import os
import re

from configparser import ConfigParser
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

        config = ConfigParser()
        config.read(os.path.expanduser('~/.stata_kernel.conf'))
        self.stata = StataSession(
            execution_mode=config['stata_kernel']['execution_mode'],
            stata_path=config['stata_kernel']['stata_path'],
            cache_dir=os.path.expanduser(
                config['stata_kernel']['cache_directory']))
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

        if check_graphs:
            graphs_to_get = self.check_graphs()
            graphs_to_get = list(set(graphs_to_get))
            all_graphs = []
            for graph in graphs_to_get:
                g = self.get_graph(graph)
                all_graphs.append(g)

            for graph in all_graphs:
                content = {
                    # This dict may contain different MIME representations
                    # of the output.
                    'data': {
                        'text/plain': 'text',
                        'image/svg+xml': graph},

                    # We can specify the image size in the metadata field.
                    'metadata': {
                        'width': 600,
                        'height': 400}}

                # We send the display_data message with the contents.
                self.send_response(self.iopub_socket, 'display_data', content)

        return return_obj

    def do_shutdown(self, restart):
        """Shutdown the Stata session

        Shutdown the kernel. You only need to handle your own clean up - the
        kernel machinery will take care of cleaning up its own things before
        stopping.
        """
        if self.execution_mode == 'automation':
            self.run_automation_cmd('DoCommandAsync', 'exit, clear')
        else:
            self.child.close(force=True)
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

    def get_log(self, code, log_path, is_async):
        """Get results from log file
        """

        code_l = code.split('\n')
        # Remove '\r' from the right side of strings
        code_l = [x.rstrip('\r') for x in code_l]
        # The `log using` line doesn't show up in the output
        code_l = code_l[1:]

        with open(log_path) as f:
            lines = f.readlines()

        # Remove log header. I assume it's always 5 lines.
        lines = lines[5:]

        # If necessary check log for errors
        rc = None
        if is_async:
            rc_regex = re.compile(r'^r\(\d+\);$').search
            err = [x for x in lines if rc_regex(x)]
            if err:
                rc = rc_regex(err[0]).group(0)

        # Take off newline character
        lines = [l[:-1] for l in lines]

        # Add `. ` to code lines so they can be matched and removed
        if is_async:
            code_l = ['. ' + x for x in code_l]

        # Find indices of code lines
        inds = [ind for ind, x in enumerate(lines) if x in code_l]
        begin_inds = [x + 1 for x in inds][:-1]
        end_inds = inds[1:]

        # Make a list of lists, where each inner list comprises a block of lines
        # from a single command
        res = [lines[begin_inds[x]:end_inds[x]] for x in range(len(begin_inds))]

        # For the async execution, remove any lines that are `. ` or `  \d.    `
        for i, block in enumerate(res):
            block_new = [
                l for l in block if not re.search(r'^((\. )|(  \d+\.    ))', l)]
            res[i] = block_new

        # First join on a single EOL the lines within each code block. Then join
        # on a double EOL between each code block.
        res_joined = (os.linesep + os.linesep).join([
            os.linesep.join(x) for x in res])

        # Fix output when the Stata window is too narrow.
        # For all lines beginning with `> `, move to the end of previous line
        if (os.linesep + '> ') not in res_joined:
            return {'err': rc, 'res': res_joined}

        lines = res_joined.split(os.linesep)
        inds = [ind for ind, x in enumerate(lines) if x.startswith('> ')]
        # Reverse list to accommodate when there are two `> ` lines in a row
        for ind in inds[::-1]:
            if re.search(r'^> \s+', lines[ind]):
                lines[ind - 1] += re.sub(r'^>\s+', ' ', lines[ind])
            else:
                lines[ind - 1] += lines[ind][2:]

        return {
            'err':
                rc,
            'res':
                os.linesep.join([
                    x for ind, x in enumerate(lines) if ind not in inds])}
