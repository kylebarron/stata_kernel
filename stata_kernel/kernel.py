from ipykernel.kernelbase import Kernel

from .completions import CompletionsManager
from .code_manager import CodeManager
from .stata_session import StataSession
from .stata_magics import StataMagics


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '1.2.0'
    language = 'stata'
    language_version = '15.1'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'file_extension': '.do'}

    def __init__(self, *args, **kwargs):
        super(StataKernel, self).__init__(*args, **kwargs)

        self.graphs = {}
        self.magics = StataMagics()

        self.sc_delimit_mode = False
        self.stata = StataSession()
        self.banner = self.stata.banner

    def do_execute(
            self, code, silent, store_history=True, user_expressions=None,
            allow_stdin=False):
        """Execute user code.

        This is the function that Jupyter calls to run code. Must return a
        dictionary as described here:
        https://jupyter-client.readthedocs.io/en/stable/messaging.html#execution-results

        """
        if not self.is_complete(code):
            return {'status': 'error', 'execution_count': self.execution_count}

        # Search for magics in the code
        code = self.magics.magic(code, self)

        # If requested, permanently set inline image display size
        if self.magics.img_set:
            self.stata.img_metadata = self.magics.img_metadata

        # The image width and height is always from magics.img_metadata;
        # set it to the default if not using %plot magic.
        if (self.magics.graphs != 2):
            self.magics.img_metadata = self.stata.img_metadata

        # If the magic executed, bail out early
        if self.magics.quit_early:
            return self.magics.quit_early

        # Tokenize code and return code chunks
        cm = CodeManager(code, self.sc_delimit_mode, self.stata.mata_mode)

        # Enter #delimit ; or mata mode
        self.sc_delimit_mode = cm.ends_sc
        self.stata.mata_mode = cm.has_mata_mode and not cm.ends_mata
        if self.stata.mata_mode:
            self.stata.prompt = self.stata.mata_prompt
            self.stata.prompt_regex = self.stata.mata_prompt_regex
            if (self.magics.graphs != 2):
                self.magics.graphs = 0
        else:
            self.stata.prompt = self.stata.stata_prompt
            self.stata.prompt_regex = self.stata.stata_prompt_regex

        # Execute code chunk
        rc, imgs, res = self.stata.do(cm.get_chunks(), self.magics)
        stream_content = {'text': res}

        # Post magic results, if applicable
        self.magics.post(self)

        # The base class increments the execution count
        return_obj = {'execution_count': self.execution_count}
        if rc:
            return_obj['status'] = 'error'
            stream_content['name'] = 'stderr'
        else:
            return_obj['status'] = 'ok'
            return_obj['payload'] = []
            return_obj['user_expressions'] = {}
            stream_content['name'] = 'stdout'

        if silent:
            return return_obj

        # At the moment, can only send either an image _or_ text to support
        # Hydrogen
        # Only send a response if there's text
        if res.strip():
            self.send_response(self.iopub_socket, 'stream', stream_content)
            if (self.magics.graphs != 2):
                return return_obj

        if imgs or (self.magics.graphs == 2):
            img_mimetypes = {
                'pdf': 'application/pdf',
                'svg': 'image/svg+xml',
                'tif': 'image/tiff',
                'png': 'image/png'}
            for (img, graph_format) in imgs:

                content = {
                    # This dict may contain different MIME representations
                    # of the output.
                    'data': {
                        'text/plain': 'text',
                        img_mimetypes[graph_format]: img},

                    # We can specify the image size in the metadata field.
                    'metadata': self.magics.img_metadata}

                # We send the display_data message with the contents.
                self.send_response(self.iopub_socket, 'display_data', content)

        return return_obj

    def do_shutdown(self, restart):
        """Shutdown the Stata session

        Shutdown the kernel. You only need to handle your own clean up - the
        kernel machinery will take care of cleaning up its own things before
        stopping.
        """
        self.stata.shutdown()
        return {'restart': restart}

    def do_is_complete(self, code):
        """Decide if command has completed

        I permit users to use /// line continuations. Otherwise, the only
        incomplete text should be unmatched braces. I use the fact that braces
        cannot be followed by text when opened or preceded or followed by text
        when closed.

        """
        if self.is_complete(code):
            return {'status': 'complete'}

        return {'status': 'incomplete', 'indent': '    '}

    def do_complete(self, code, cursor_pos):
        env = self.stata.env
        suggestions = CompletionsManager(env)
        return {}

    def is_complete(self, code):
        return CodeManager(
            code, self.sc_delimit_mode, self.stata.mata_mode).is_complete
