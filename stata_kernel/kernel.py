import os
import re
import pexpect
import string
import platform
from dateutil.parser import parse
from configparser import ConfigParser
from ipykernel.kernelbase import Kernel


class StataKernel(Kernel):
    implementation = 'stata_kernel'
    implementation_version = '0.1'
    language = 'stata'
    language_version = '0.1'
    language_info = {
        'name': 'stata',
        'mimetype': 'text/x-stata',
        'file_extension': '.do',
    }

    def __init__(self, *args, **kwargs):
        super(StataKernel, self).__init__(*args, **kwargs)

        self.graphs = {}

        config = ConfigParser()
        config.read(os.path.expanduser('~/.stata_kernel.conf'))
        if platform.system() == 'Windows':
            self.child = pexpect.popen_spawn.PopenSpawn(
                config['stata_kernel']['stata_path'])
        else:
            self.child = pexpect.spawn(config['stata_kernel']['stata_path'])
        # Wait/scroll to initial dot prompt
        self.child.expect('\r\n\.')

        # Set banner to Stata's shell header
        banner = self.child.before.decode('utf-8')
        banner = ''.join([x for x in banner if x in string.printable])

        # Remove extra characters before first \r\n
        self.banner = re.sub(r'^.*\r\n', '', banner)

        # Set more off
        self.run_shell('set more off')

    def do_execute(self,
                   code,
                   silent,
                   store_history=True,
                   user_expressions=None,
                   allow_stdin=False):

        code = self.remove_comments(code)
        obj = self.run_shell(code)
        rc = obj.get('err')
        res = obj.get('res')
        stream_content = {'text': '\n'.join(res)}
        if rc:
            stream_content['name'] = 'stderr'
        else:
            stream_content['name'] = 'stdout'

        if not silent:
            self.send_response(self.iopub_socket, 'stream', stream_content)

            if obj.get('check_graphs'):
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
                            'image/svg+xml': graph
                        },

                        # We can specify the image size in the metadata field.
                        'metadata': {
                            'width': 600,
                            'height': 400
                        }
                    }

                    # We send the display_data message with the contents.
                    self.send_response(self.iopub_socket, 'display_data',
                                       content)
        if rc:
            return {'status': 'error', 'execution_count': self.execution_count}

        return {
            'status': 'ok',
            # The base class increments the execution count
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def do_shutdown(self, restart):
        """Shutdown the Stata session

        Shutdown the kernel. You only need to handle your own clean up - the
        kernel machinery will take care of cleaning up its own things before
        stopping.
        """
        self.child.sendline('exit, clear')
        return {'restart': restart}

    def do_is_complete(self, code):
        """Decide if command has completed

        I permit users to use /// line continuations. Otherwise, the only
        incomplete text should be unmatched braces. I use the fact that braces
        cannot be followed by text when opened or preceded or followed by text
        when closed.

        """
        code = code.strip()
        if code.endswith('///'):
            return {'status': 'incomplete', 'indent': '    '}

        lines = re.sub(r'\r\n', r'\n', code).split('\n')
        lines = [x.strip() for x in lines]
        open_br = len([x for x in lines if x.endswith('{')])
        closed_br = len([x for x in lines if x.startswith('}')])
        if open_br > closed_br:
            return {'status': 'incomplete', 'indent': '    '}

        return {'status': 'complete'}

    def run_shell(self, code):
        """Run Stata command in shell

        I split the code into lines because that makes it easier to work with
        pexpect.expect. Even if you paste several lines in, Stata's shell still
        shows the prompt, i.e. `\r\n.` several times. So if I expect for that
        prompt, I'll only scroll to the first line continuation by default. It's
        impossible to get all the continuation prompts without knowing how many
        separate commands there are, because some commands in Stata take a long
        time. Therefore it's imperative to split the code into lines.

        However splitting the code into lines makes it harder to support for
        loops. This is because if I split on \n and send the first line, I don't
        get the line continuation prompt back. I fix this by assuming that the
        Stata executable will provide the loop continuation prompt very quickly,
        since all it needs to do is parse if the command has ended. So if there
        exists a block in the code, then I check for 0.1 s after every line to
        see if there is a loop continuation line.

        The regex that I expect on is '(?<=\r\n)\r\n\.'. This is necessary
        instead of '\r\n.' because the latter would have issues after `di "."`.
        Since the kernel always shows two end of lines before a dot prompt, this
        is fine.

        NOTE will need to set timeout to None once sure that running is stable.
        Otherwise running a task longer than 30s would timeout.

        Args:
            code (str): code to run in Stata

        Returns:
            results from Stata shell
        """

        has_blocks = re.search(r'\{[^\}]+?\}', code)

        # Split user code into lines
        code = re.sub(r'\r\n', r'\n', code)
        lines = code.split('\n')
        results = []
        for line in lines:
            self.child.sendline(line)
            if has_blocks:
                try:
                    self.child.expect('\r\n  \d\. ', timeout=0.1)
                    continue
                except pexpect.TIMEOUT:
                    pass

            self.child.expect('(?<=\r\n)\r\n\. ')
            res = self.child.before.decode('utf-8')

            # Remove input command, up to first \r\n
            res = re.sub(r'^.+\r\n', '', res)

            # Check error
            err = re.search(r'\r\nr\((\d+)\);', res)
            if err:
                return {'err': err.group(1), 'res': [res]}

            results.append(res)

        obj = {'err': '', 'res': results}

        graph_keywords = [
            r'gr(a|ap|aph)?', r'tw(o|ow|owa|oway)?',
            r'sc(a|at|att|atte|atter)?', r'line'
        ]
        graph_keywords = r'\b(' + '|'.join(graph_keywords) + r')\b'
        if re.search(graph_keywords, code):
            obj['check_graphs'] = True

        return obj

    def check_graphs(self):
        cur_names = self.run_shell('graph dir')['res'][0]
        cur_names = cur_names.strip().split(' ')
        cur_names = [x.strip() for x in cur_names]
        graphs_to_get = []
        for name in cur_names:
            if not self.graphs.get(name):
                graphs_to_get.append(name)
                continue

            self.run_shell('cap graph describe ' + name)
            stamp = self.run_shell('di r(command_date) " " r(command_time)')[
                'res'][0].strip()
            stamp = parse(stamp)
            if stamp > self.graphs.get(name):
                graphs_to_get.append(name)

        return graphs_to_get

    def get_graph(self, name):
        # Export graph to file
        self.run_shell('cap mkdir .stata_kernel_images')
        cmd = 'graph export .stata_kernel_images/' + name + '.svg , '
        cmd += 'name(' + name + ') as(svg)'
        self.run_shell(cmd)

        # Get file location
        cwd = self.run_shell('pwd')['res'][0].strip()

        # Read image
        with open(cwd + '/.stata_kernel_images/' + name + '.svg') as f:
            img = f.read()

        # Get timestamp of graph and save to dict
        self.run_shell('cap graph describe ' + name)
        stamp = self.run_shell('di r(command_date) " " r(command_time)')[
            'res'][0].strip()
        self.graphs[name] = parse(stamp)

        return img
    def remove_comments(self, code):
        """Remove block and end-of-line comments from code

        From:
        https://stackoverflow.com/questions/24518020/comprehensive-regexp-to-remove-javascript-comments
        Using the "Final Boss Fight" at the bottom.
        Otherwise it fails on `di 5 / 5 // hello`
        """
        return re.sub(
            r'((["\'])(?:\\[\s\S]|.)*?\2|(?:[^\w\s]|^)\s*\/(?![*\/])(?:\\.|\[(?:\\.|.)\]|.)*?\/(?=[gmiy]{0,4}\s*(?![*\/])(?:\W|$)))|\/\/\/.*?\r?\n\s*|\/\/.*?$|\/\*[\s\S]*?\*\/',
            '\\1', code)
