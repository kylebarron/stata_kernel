import os

from ipykernel.kernelbase import Kernel

from .completions import CompletionsManager
from .code_manager import CodeManager
from .stata_session import StataSession


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '0.1'
    language = 'stata'
    language_version = '0.1'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'file_extension': '.do'}

    def __init__(self, *args, **kwargs):
        super(StataKernel, self).__init__(*args, **kwargs)

        self.graphs = {}

        self.stata = StataSession()
        self.banner = self.stata.banner

        # Change to this directory and set more off
        text = [('Token.Text', 'cd `"{}"\''.format(os.getcwd())),
                ('Token.Text', 'set more off')]
        self.stata.do(text)

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
        if not self.is_complete(code):
            return {'status': 'error', 'execution_count': self.execution_count}

        cm = CodeManager(code)
        rc, res = self.stata.do(cm.get_chunks())
        stream_content = {'text': res}

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
            return return_obj

        # if check_graphs:
        #     graphs_to_get = self.check_graphs()
        #     graphs_to_get = list(set(graphs_to_get))
        #     all_graphs = []
        #     for graph in graphs_to_get:
        #         g = self.get_graph(graph)
        #         all_graphs.append(g)
        #
        #     for graph in all_graphs:
        #         content = {
        #             # This dict may contain different MIME representations
        #             # of the output.
        #             'data': {
        #                 'text/plain': 'text',
        #                 'image/svg+xml': graph},
        #
        #             # We can specify the image size in the metadata field.
        #             'metadata': {
        #                 'width': 600,
        #                 'height': 400}}
        #
        #         # We send the display_data message with the contents.
        #         self.send_response(self.iopub_socket, 'display_data', content)

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

    def do_complete(self, code):
        env = self.stata.env
        suggestions = CompletionsManager(env)
        return {}

    def is_complete(self, code):
        cm = CodeManager(code)
        if str(cm.tokens[-1][0]) == 'Token.MatchingBracket.Other':
            return False
        return True
