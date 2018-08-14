from ipykernel.kernelbase import Kernel
from timeit import default_timer

from .completions import CompletionsManager
from .code_manager import CodeManager
from .stata_session import StataSession
from .stata_magics import StataMagics


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '1.3.1'
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
        self.timer_dict = {}

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

        self._timer()

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

        # If %timer is on, always profile
        if self.magics.timer:
            if self.magics.timer_profile:
                self.magics.timeit = 2
            else:
                self.timeit = 1

        self._timer('StataMagics')

        # Tokenize code and return code chunks
        cm = CodeManager(code, self.sc_delimit_mode, self.stata.mata_mode)
        # print('debugz', self.stata.mata_mode)

        # Enter mata if applicable
        self.stata.mata_mode = cm.has_mata_mode and not cm.ends_mata
        # print('debugw', self.stata.mata_mode)
        if self.stata.mata_mode:
            # print('debugx', 'mata')
            self.stata.prompt = self.stata.mata_prompt
            self.stata.prompt_regex = self.stata.mata_prompt_regex
            # Turn off plot magic in mata
            # if (self.magics.graphs != 2):
            self.magics.graphs = 0
        else:
            # print('debugx', 'stata')
            self.stata.prompt = self.stata.stata_prompt
            self.stata.prompt_regex = self.stata.stata_prompt_regex

        self._timer('CodeManager')

        # Execute code chunk
        rc, imgs, res = self.stata.do(cm.get_chunks(), self.magics)
        self._timer('StataSession')

        # If mata error, restart
        if self.stata.mata_mode and (rc == 3000):
            self.stata.prompt = self.stata.stata_prompt
            self.stata.prompt_regex = self.stata.stata_prompt_regex
            mata_restart = [('Token.Text', 'end')]
            _rc, _imgs, _res = self.stata.do(mata_restart, self.magics)
            self.stata.prompt = self.stata.mata_prompt
            self.stata.prompt_regex = self.stata.mata_prompt_regex
            _rc, _imgs, _res = self.stata.do([('Token.Text', 'mata')], self.magics)
            res = "Incomplete or invalid input; restarting mata...\n"
            res += _res
        elif self.stata.mata_mode and (rc == 0):
            res = self.stata.mata_trim.sub('', res)

        self._timer('MataRefresh')
        stream_content = {'text': res}

        # Post magic results, if applicable
        self.magics.post(self)
        self._timer('StataMagicsPost')

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
            self._timer('CompletionsManager', True)
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
        self._timer('CompletionsManager', True)
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
        # Environment-aware suggestion for the current space-delimited
        # variable, local, etc.
        env, pos, chunk, rcomp = self.completions.get_env(
            code[:cursor_pos], code[cursor_pos:(cursor_pos + 2)],
            self.sc_delimit_mode, self.stata.mata_mode)

        return {
            'status': 'ok',
            'cursor_start': pos,
            'cursor_end': cursor_pos,
            'matches': self.completions.get(chunk, env, rcomp)}

    def is_complete(self, code):
        c = CodeManager(
            code, self.sc_delimit_mode, self.stata.mata_mode).is_complete
        return c

    def _timer(self, step = None, end = False):
        if self.magics.timer:
            if self.magics.timer_profile:
                self.magics.timeit = 2
            else:
                self.magics.timeit = 1

        if step:
            self.timer_dict[step] = default_timer() - self.timer_dict['timer']
            self.timer_dict['timer'] = default_timer()
        else:
            self.timer_dict = {}
            self.timer_dict['all'] = default_timer()
            self.timer_dict['timer'] = default_timer()

        if end:
            self.timer_dict['all'] = default_timer() - self.timer_dict['all']

            if self.magics.timer:
                lens = 0
                sens = 0
                tprint = []
                sprint = []

                for k, t in self.timer_dict.items():
                    if k == 'all':
                        tall = t
                        continue
                    elif k == 'timer':
                        continue

                    tfmt = "{0:.2f}".format(t)
                    tprint += [(tfmt, k)]
                    lens = max(lens, len(tfmt))

                for k, t in self.stata.timer_dict.items():
                    if k == 'all':
                        continue
                    elif k == 'timer':
                        continue

                    sfmt = "{0:.2f}".format(t)
                    sprint += [(sfmt, k)]
                    sens = max(sens, len(sfmt))

                self._print("Wall time (total): {0:.2f}\n".format(tall))
                fmt = "\t{{0:{0}}} {{1}}\n".format(lens)
                smt = "\t\t{{0:{0}}} {{1}}\n".format(sens)
                for t, k in tprint:
                    self._print(fmt.format(t, k))
                    if k == 'StataSession':
                        for _t, _k in sprint:
                            self._print(smt.format(_t, _k))

    def _print(self, msg):
        stream_content = {'text': msg}
        stream_content['name'] = 'stdout'
        self.send_response(self.iopub_socket, 'stream', stream_content)
