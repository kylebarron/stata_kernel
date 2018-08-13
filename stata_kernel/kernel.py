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
        self.completions = CompletionsManager(self)
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

        # Enter mata if applicable
        self.stata.mata_mode = cm.has_mata_mode and not cm.ends_mata
        if self.stata.mata_mode:
            # print('\tdebug1', 'mata')
            self.stata.prompt = self.stata.mata_prompt
            self.stata.prompt_regex = self.stata.mata_prompt_regex
            # Turn off plot magic in mata
            # if (self.magics.graphs != 2):
            self.magics.graphs = 0
        else:
            # print('\tdebug1', 'stata')
            self.stata.prompt = self.stata.stata_prompt
            self.stata.prompt_regex = self.stata.stata_prompt_regex

        # Execute code chunk
        # print('\tdebug2', cm.get_chunks())
        rc, imgs, res = self.stata.do(cm.get_chunks(), self.magics)

        # If mata error, restart
        # print("debug0", self.stata.mata_mode)
        if self.stata.mata_mode and (rc == 3000):
            self.stata.prompt = self.stata.stata_prompt
            self.stata.prompt_regex = self.stata.stata_prompt_regex
            mata_restart = [('Token.Text', 'end')]
            _rc, _imgs, _res = self.stata.do(mata_restart, self.magics)
            # print("debuge", res)
            self.stata.prompt = self.stata.mata_prompt
            self.stata.prompt_regex = self.stata.mata_prompt_regex
            _rc, _imgs, _res = self.stata.do([('Token.Text', 'mata')], self.magics)
            # print("debugf", _res)
            res = "Incomplete or invalid input; restarting...\n"
            res += _res
        elif self.stata.mata_mode and (rc == 0):
            # print('debug', self.stata.mata_trim.search(res))
            res = self.stata.mata_trim.sub('', res)

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
            # Refresh completions
            self.completions.refresh(self)
            return return_obj

        if res.strip():
            self.send_response(self.iopub_socket, 'stream', stream_content)

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

        # Send message if delimiter changed. NOTE: This uses the delimiter at
        # the _end_ of the code block. It prints only if the delimiter at the
        # end is different than the one before the chunk.
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
        # print("debugic")
        if self.is_complete(code):
            # print("debugic1")
            return {'status': 'complete'}

        # print("debugic2")
        return {'status': 'incomplete', 'indent': '    '}

    def do_complete(self, code, cursor_pos):
        # Environment-aware suggestion for the current space-delimited
        # variable, local, etc.
        env, pos, chunk, rcomp = self.completions.get_env(
            code[:cursor_pos], code[cursor_pos:(cursor_pos + 2)],
            self.sc_delimit_mode, self.stata.mata_mode)

        return {
            'status': 'ok',
            'cursor_start': pos,
            'cursor_end': cursor_pos,
            'matches': self.completions.get(chunk, env, rcomp)
        }

    def is_complete(self, code):
        c = CodeManager(
            code, self.sc_delimit_mode, self.stata.mata_mode).is_complete
        # print("debugc", c)
        return c
