import os
import base64
import platform

from PIL import Image
from textwrap import dedent
from xml.etree import ElementTree as ET
from ipykernel.kernelbase import Kernel

from .config import Config
from .completions import CompletionsManager
from .code_manager import CodeManager
from .stata_session import StataSession
from .stata_magics import StataMagics


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '1.4.7'
    language = 'stata'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'file_extension': '.do'}
    help_links = [
        {'text': 'stata_kernel Help', 'url': 'https://kylebarron.github.io/stata_kernel/'},
        {'text': 'Stata Help', 'url': 'https://www.stata.com/features/documentation/'}
    ] # yapf: disable

    def __init__(self, *args, **kwargs):
        super(StataKernel, self).__init__(*args, **kwargs)

        # Can't name this `self.config`. Conflicts with a Jupyter attribute
        self.conf = Config()
        self.graph_formats = ["svg", "png"]
        self.sc_delimit_mode = False
        self.stata = StataSession(self, self.conf)
        self.banner = self.stata.banner
        self.language_version = self.stata.stata_version
        self.magics = StataMagics(self)
        self.completions = CompletionsManager(self, self.conf)

    def do_execute(
            self,
            code,
            silent,
            store_history=True,
            user_expressions=None,
            allow_stdin=False):
        """Execute user code.

        This is the function that Jupyter calls to run code. Must return a
        dictionary as described here:
        https://jupyter-client.readthedocs.io/en/stable/messaging.html#execution-results
        """
        invalid_input_msg = """\
        stata_kernel error: code entered was incomplete.

        This usually means that a loop or program was not correctly terminated.
        This can also happen if you are in `#delimit ;` mode and did not end the
        command with `;`. Use `%delimit` to see the current delimiter mode.
        """
        if not self.is_complete(code):
            self.send_response(
                self.iopub_socket, 'stream', {
                    'text': dedent(invalid_input_msg),
                    'name': 'stderr'})

            return {'status': 'error', 'execution_count': self.execution_count}

        # Write line of code to history file
        if code:
            r = repr(code)
            with open(self.conf.get('cache_dir') / 'history.txt', 'a') as f:
                f.write(r + os.linesep)

        # Search for magics in the code
        code = self.magics.magic(code, self)

        # If the magic executed, bail out early
        if self.magics.quit_early:
            return self.magics.quit_early

        # Tokenize code and return code chunks
        cm = CodeManager(code, self.sc_delimit_mode)
        text_to_run, md5, text_to_exclude = cm.get_text(self.conf)
        rc, res = self.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude)

        # Post magic results, if applicable
        self.magics.post(self)

        # The base class increments the execution count
        return_obj = {'execution_count': self.execution_count}
        if rc:
            return_obj['status'] = 'error'
        else:
            return_obj['status'] = 'ok'
            return_obj['payload'] = []
            return_obj['user_expressions'] = {}

        if silent:
            # Refresh completions
            self.completions.refresh(self)
            return return_obj

        # Send message if delimiter changed.
        # NOTE: This uses the delimiter at the _end_ of the code block. It
        # prints only if the delimiter at the end is different than the one
        # before the chunk.
        if cm.ends_sc != self.sc_delimit_mode:
            delim = ';' if cm.ends_sc else 'cr'
            self.send_response(
                self.iopub_socket, 'stream', {
                    'text': 'delimiter now {}'.format(delim),
                    'name': 'stdout'})
        self.sc_delimit_mode = cm.ends_sc

        # Refresh completions
        self.completions.refresh(self)
        return return_obj

    def send_image(self, graph_path):
        """Load graph and send to frontend

        In `code_manager.get_text`, I send to Stata only the `width` argument.
        This way, the graphs are always scaled in accordance with their aspect
        ratio. However this means that I don't know their aspect ratio. For this
        reason, I load the SVG or PNG image into memory so that I can get the
        image dimensions to relay to the frontend.

        As of now, this only supports SVG and PNG formats. I see no real need to
        change this. PDF isn't supported in Atom or in Jupyter. TIFF is 1-2
        orders of magnitude larger than SVG and PNG images without a real
        benefit over SVG.

        Args:
            graph_path (str): path to exported graph
        """

        no_display_msg = 'This front-end cannot display the desired image type.'
        if graph_path.endswith('.svg'):
            with open(graph_path, 'r', encoding='utf-8') as f:
                img = f.read()
            e = ET.ElementTree(ET.fromstring(img))
            root = e.getroot()

            content = {
                'data': {
                    'text/plain': no_display_msg,
                    'image/svg+xml': img},
                'metadata': {
                    'image/svg+xml': {
                        'width': int(root.attrib['width'][:-2]),
                        'height': int(root.attrib['height'][:-2])}}}
            self.send_response(self.iopub_socket, 'display_data', content)
        elif graph_path.endswith('.png'):
            im = Image.open(graph_path)
            width = im.size[0]
            height = im.size[1]

            # On my Mac, the width is double what I told Stata to export. This
            # is not true on my Windows test VM
            if platform.system() == 'Darwin':
                width /= 2
                height /= 2
            with open(graph_path, 'rb') as f:
                img = base64.b64encode(f.read()).decode('utf-8')

            content = {
                'data': {
                    'text/plain': no_display_msg,
                    'image/png': img},
                'metadata': {
                    'image/png': {
                        'width': width,
                        'height': height}}}
            self.send_response(self.iopub_socket, 'display_data', content)

    def do_shutdown(self, restart):
        """Shutdown the Stata session

        Shutdown the kernel. You only need to handle your own clean up - the
        kernel machinery will take care of cleaning up its own things before
        stopping.
        """
        self.stata.shutdown()
        return {'restart': restart}

    def do_is_complete(self, code):
        """Decide if command has completed"""
        if self.is_complete(code):
            return {'status': 'complete'}

        return {'status': 'incomplete', 'indent': '    '}

    def do_complete(self, code, cursor_pos):
        """Provide context-aware suggestions
        """
        env, pos, chunk, rcomp = self.completions.get_env(
            code[:cursor_pos], code[cursor_pos:(cursor_pos + 2)],
            self.sc_delimit_mode)

        return {
            'status': 'ok',
            'cursor_start': pos,
            'cursor_end': cursor_pos,
            'matches': self.completions.get(chunk, env, rcomp)}

    def is_complete(self, code):
        return CodeManager(code, self.sc_delimit_mode).is_complete

    def do_history(hist_access_type, output, raw, session=None, start=None,
        stop=None, n=None, pattern=None, unique=False):

        pass

# someDictionary = {
#     helloworld
# }
#
# %%markdown
# ## Emphasis
#
# **This is bold text**
#
# __This is bold text__
#
# *This is italic text*
#
# _This is italic text_
#
#
#
# ## Test
#
# from pathlib import Path
# path = Path('~/.stata_kernel_cache/history.txt').expanduser()
#
# y = reverse_readline(path)
# [x for x in y]
#
# def reverse_readline(filename, buf_size=8192):
#     """a generator that returns the lines of a file in reverse order"""
#     with open(filename) as fh:
#         segment = None
#         offset = 0
#         fh.seek(0, os.SEEK_END)
#         file_size = remaining_size = fh.tell()
#         while remaining_size > 0:
#             offset = min(file_size, offset + buf_size)
#             fh.seek(file_size - offset)
#             buffer = fh.read(min(remaining_size, buf_size))
#             remaining_size -= buf_size
#             lines = buffer.split('\n')
#             # the first line of the buffer is probably not a complete line so
#             # we'll save it and append it to the last line of the next buffer
#             # we read
#             if segment is not None:
#                 # if the previous chunk starts right from the beginning of line
#                 # do not concact the segment to the last line of new chunk
#                 # instead, yield the segment first
#                 if buffer[-1] is not '\n':
#                     lines[-1] += segment
#                 else:
#                     yield segment
#             segment = lines[0]
#             for index in range(len(lines) - 1, 0, -1):
#                 if len(lines[index]):
#                     yield lines[index]
#         # Don't yield None if the file was empty
#         if segment is not None:
#             yield segment
