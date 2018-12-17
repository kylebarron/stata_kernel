import os
import re
import base64
import shutil
import platform
import html

from PIL import Image
from pathlib import Path
from textwrap import dedent
from datetime import datetime
from xml.etree import ElementTree as ET
from pkg_resources import resource_filename
from ipykernel.kernelbase import Kernel

from .config import Config
from .completions import CompletionsManager
from .code_manager import CodeManager
from .stata_session import StataSession
from .stata_magics import StataMagics


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '1.8.1'
    language = 'stata'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'codemirror_mode': 'stata',
        'file_extension': '.do',
        'version': '15.1'}
    help_links = [
        {'text': 'stata_kernel Help', 'url': 'https://kylebarron.github.io/stata_kernel/'},
        {'text': 'Stata Help', 'url': 'https://www.stata.com/features/documentation/'}
    ]  # yapf: disable

    def __init__(self, *args, **kwargs):
        # Copy syntax highlighting files
        from_paths = [
            Path(resource_filename('stata_kernel', 'pygments/stata.py')),
            Path(resource_filename('stata_kernel', 'codemirror/stata.js'))]
        to_paths = [
            Path(resource_filename('pygments', 'lexers/stata.py')),
            Path(
                resource_filename(
                    'notebook',
                    'static/components/codemirror/mode/stata/stata.js'))]

        for from_path, to_path in zip(from_paths, to_paths):
            copy = False
            if to_path.is_file():
                to_path_dt = datetime.fromtimestamp(to_path.stat().st_mtime)
                from_path_dt = datetime.fromtimestamp(from_path.stat().st_mtime)
                if from_path_dt > to_path_dt:
                    copy = True
            else:
                copy = True

            if copy:
                try:
                    to_path.parents[0].mkdir(parents=True, exist_ok=True)
                    shutil.copy(str(from_path), str(to_path))
                except OSError:
                    pass

        super(StataKernel, self).__init__(*args, **kwargs)

        # Can't name this `self.config`. Conflicts with a Jupyter attribute
        self.conf = Config()
        self.graph_formats = ['svg', 'png', 'pdf']
        self.sc_delimit_mode = False
        self.stata = StataSession(self, self.conf)
        self.banner = self.stata.banner
        self.language_version = self.stata.stata_version
        self.magics = StataMagics(self)
        self.completions = CompletionsManager(self, self.conf)

    def do_execute(
            self, code, silent, store_history=True, user_expressions=None,
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

            return {
                'status': 'error',
                'ename': 'error_exception_name',
                'evalue': 'exception_value',
                'traceback': [''],
                'execution_count': self.execution_count}

        # Search for magics in the code
        code = self.magics.magic(code, self)

        # If the magic executed, bail out early
        if self.magics.quit_early:
            return self.magics.quit_early

        # Tokenize code and return code chunks
        cm = CodeManager(code, self.sc_delimit_mode, self.stata.mata_mode)
        self.stata._mata_refresh(cm)
        text_to_run, md5, text_to_exclude = cm.get_text(self.conf, self.stata)

        # Execute code chunk
        rc, res = self.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude)
        res = self.stata._mata_restart(rc, res)

        # Post magic results, if applicable
        self.magics.post(self)
        self.post_do_hook()

        # Alert if delimiter changed. NOTE: This compares the delimiter at the
        # end of the code block with that at the end of the previous code block.
        if (not silent) and (cm.ends_sc != self.sc_delimit_mode):
            delim = ';' if cm.ends_sc else 'cr'
            self.send_response(
                self.iopub_socket, 'stream', {
                    'text': 'delimiter now {}'.format(delim),
                    'name': 'stdout'})
        self.sc_delimit_mode = cm.ends_sc

        # The base class increments the execution count
        return_obj = {'execution_count': self.execution_count}
        if rc:
            return_obj['status'] = 'error'
            return_obj['ename'] = 'error_exception_name'
            return_obj['evalue'] = 'exception_value'
            return_obj['traceback'] = ['']
        else:
            return_obj['status'] = 'ok'
            return_obj['payload'] = []
            return_obj['user_expressions'] = {}
        return return_obj

    def post_do_hook(self):
        """Things to do after running commands in Stata
        """

        _rc, _res = self.cleanLogs("off")

        self.stata.linesize = int(self.quickdo("di `c(linesize)'"))
        self.stata.cwd = self.quickdo("pwd")
        self.completions.refresh(self)

        _rc, _res = self.cleanLogs("on")

    def quickdo(self, code):
        code = self.stata._mata_escape(code)
        cm = CodeManager(code)
        text_to_run, md5, text_to_exclude = cm.get_text(self.conf)
        rc, res = self.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)

        if not rc:
            # Remove rmsg lines when rmsg is on
            rmsg_regex = r'r(\(\d+\))?;\s+t=\d*\.\d*\s*\d*:\d*:\d*'
            res = [
                x for x in res.split('\n')
                if not re.search(rmsg_regex, x.strip())]
            res = '\n'.join(res).strip()
            if self.stata.mata_open:
                res = re.sub(
                    r'^([:\>])  ??(\{\})?$', '', res,
                    flags=re.MULTILINE).strip()

            return res

    def cleanLogs(self, what):
        code = self.stata._mata_escape("_StataKernelLog {0}".format(what))
        cm = CodeManager(code)
        text_to_run, md5, text_to_exclude = cm.get_text(self.conf)
        rc, res = self.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)

        if what == 'off':
            code = self.stata._mata_escape('_StataKernelLog {0}'.format(what))
            self.cleanTail(code, self.stata.prompt_dot)
        return rc, res

    def send_image(self, graph_paths):
        """Load graph and send to frontend

        This supports SVG, PNG, and PDF formats. While PDF display isn't
        supported in Atom or Jupyter, the data can be stored within the Jupyter
        Notebook file and makes exporting images to PDF through LaTeX easier.

        Args:
            graph_paths (List[str]): path to exported graph
        """

        no_display_msg = 'This front-end cannot display the desired image type.'
        content = {'data': {'text/plain': no_display_msg}, 'metadata': {}}
        warn = False
        for graph_path in graph_paths:
            file_size = Path(graph_path).stat().st_size
            if (file_size > 2 * (1024 ** 3)) & (len(graph_paths) >= 2):
                warn = True

            if graph_path.endswith('.svg'):
                with Path(graph_path).open('r', encoding='utf-8') as f:
                    img = f.read()
                e = ET.ElementTree(ET.fromstring(img))
                root = e.getroot()

                width = int(root.attrib['width'][:-2])
                height = int(root.attrib['height'][:-2])
                # Wrap SVG in iframe. See #234.
                iframe = """\
                <iframe frameborder="0" scrolling="no" height="{0}" width="{1}"\
                srcdoc="<html><body>{2}</body></html>"></iframe>
                """.format(height, width, html.escape(img))
                content['data']['text/html'] = dedent(iframe)
                content['metadata']['text/html'] = {
                    'width': width,
                    'height': height}

                content['data']['image/svg+xml'] = img
                content['metadata']['image/svg+xml'] = {
                    'width': int(root.attrib['width'][:-2]),
                    'height': int(root.attrib['height'][:-2])}

            elif graph_path.endswith('.png'):
                im = Image.open(graph_path)
                width = im.size[0]
                height = im.size[1]

                # On my Mac, the width is double what I told Stata to export.
                # This is not true on my Windows test VM
                if platform.system() == 'Darwin':
                    width /= 2
                    height /= 2
                with Path(graph_path).open('rb') as f:
                    img = base64.b64encode(f.read()).decode('utf-8')

                content['data']['image/png'] = img
                content['metadata']['image/png'] = {
                    'width': width,
                    'height': height}

            elif graph_path.endswith('.pdf'):
                with Path(graph_path).open('rb') as f:
                    pdf = base64.b64encode(f.read()).decode('utf-8')
                content['data']['application/pdf'] = pdf

        msg = """\
        **`stata_kernel` Warning**: One of your image files is larger than 2MB
        and you have Graph Redundancy on. If you don't plan to export the
        Jupyter Notebook file to PDF, you can save space by running:

        ```
        %set graph_svg_redundancy false [--permanently]
        %set graph_png_redundancy false [--permanently]
        ```

        To turn off this warning, run:

        ```
        %set graph_redundancy_warning false [--permanently]
        ```

        For more information, see:
        <https://kylebarron.github.io/stata_kernel/using_stata_kernel/intro/#graph-redundancy>
        """
        msg = dedent(msg)
        warn_setting = self.config.get('graph_redundancy_warning', 'True')
        if warn and (warn_setting.lower() == 'true'):
            self.send_response(
                self.iopub_socket, 'display_data', {
                    'data': {
                        'text/plain': msg,
                        'text/markdown': msg},
                    'metadata': {}})
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
            self.sc_delimit_mode, self.stata.mata_mode)

        return {
            'status': 'ok',
            'cursor_start': pos,
            'cursor_end': cursor_pos,
            'matches': self.completions.get(chunk, env, rcomp)}

    def is_complete(self, code):
        return CodeManager(
            code, self.sc_delimit_mode, self.stata.mata_mode).is_complete

    def cleanTail(self, tail, rprompt):
        """
        Search from the end of all open log files for a kernel marker
        specified by tail, typically

            . `md5 hash'

        rprompt is a regex for the prompt, typically a dot but it could
        be a `>` or a `:` (e.g. in mata). We only search up to 10 chars
        past the length of the marker for log files (unless it is a smcl
        file, in which case we search up to 100 chars back).
        """
        ltail = len(tail)
        rtail = re.escape(tail[::-1]) + ' {0,2}'
        for logfile in self.completions.suggestions['logfiles']:
            lcmp = ''
            fname, fext = os.path.splitext(logfile)
            with open(logfile, 'r+', encoding='utf-8') as fh:
                fh.seek(0, os.SEEK_END)
                pos = fh.tell() - 1
                # Note the search is inverted because we read from the end
                if fext == '.smcl':
                    maxread = pos - ltail - 100
                    rfind = rtail + '({0}|}}moc{{|[\\r\\n])'.format(rprompt)
                else:
                    rfind = rtail + rprompt
                    maxread = pos - ltail - 10
                while (pos > maxread) and (re.search(rfind, lcmp) is None):
                    lcmp += fh.read(1)
                    pos -= 1
                    fh.seek(pos, os.SEEK_SET)

                if pos > maxread:
                    fh.seek(pos + 1, os.SEEK_SET)
                    fh.truncate()
