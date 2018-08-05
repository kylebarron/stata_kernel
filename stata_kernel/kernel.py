import os
import re
import string
import pexpect
import platform
import subprocess

from subprocess import run
from dateutil.parser import parse
from configparser import ConfigParser
from ipykernel.kernelbase import Kernel

if platform.system() == 'Windows':
    import win32com.client


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
        self.execution_mode = config['stata_kernel']['execution_mode']
        self.stata_path = config['stata_kernel']['stata_path']
        if platform.system == 'Windows':
            self.eol = '\r\n'
        else:
            self.eol = '\n'
        # self.batch = config['stata_kernel']['batch']

        if self.execution_mode.lower() == 'automation':
            # Activate Stata
            if platform.system() == 'Windows':
                self.stata = win32com.client.Dispatch("stata.StataOLEApp")
            else:
                self.run_automation_cmd(cmd_name='activate')

            # TODO: Change directory to that of running code
            # Hide Stata Window
            self.run_automation_cmd(cmd_name='UtilShowStata', value=1)
            self.run_automation_cmd(cmd_name='DoCommand', value='set more off')
            self.banner = 'Jupyter kernel for Stata'

        else:
            self.child = pexpect.spawn(self.stata_path)
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
        """Execute user code.

        This is the function that Jupyter calls to run code. Must return a
        dictionary as described here:
        https://jupyter-client.readthedocs.io/en/stable/messaging.html#execution-results

        """

        code = self.remove_comments(code)
        if self.execution_mode == 'automation':
            obj = self.do_automation(code)
        else:
            obj = self.run_shell(code)
        res_text = obj.get('res')
        # Only return printable characters
        res_text = ''.join([x for x in res_text if x in string.printable])
        stream_content = {'text': res_text.rstrip()}
        if obj.get('err'):
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
        if obj.get('err'):
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
        if self.execution_mode == 'automation':
            self.run_automation_cmd('DoCommandAsync', 'exit, clear')
        else:
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
                return {'err': err.group(1), 'res': res}

            results.append(res)

        obj = {'err': '', 'res': '\n'.join(results)}

        graph_keywords = [
            r'gr(a|ap|aph)?', r'tw(o|ow|owa|oway)?',
            r'sc(a|at|att|atte|atter)?', r'line'
        ]
        graph_keywords = r'\b(' + '|'.join(graph_keywords) + r')\b'
        if re.search(graph_keywords, code):
            obj['check_graphs'] = True

        return obj

    def do_automation(self, code):
        """Run Stata command in GUI window using Stata Automation

        If the command doesn't use `program`, `while`, `forvalues`, `foreach`,
        `input`, or `exit`, I run it using DoCommand. This means that I don't
        have to poll for when the command has completed.
        """

        # Save output to log file
        log_path = os.getcwd() + '/.stata_kernel_log.log'
        code = 'log using `"{}"\', replace text nomsg{}{}'.format(log_path, self.eol, code)
        code = code.rstrip() + self.eol + 'cap log close'

        keywords = [
            r'pr(o|og|ogr|ogra|ogram)?', r'while',
            r'forv(a|al|alu|alue|alues)?', r'foreach', r'inp(u|ut)?',
            r'e(x|xi|xit)?'
        ]
        keywords = r'\b(' + '|'.join(keywords) + r')\b'
        if re.search(keywords, code):
            is_async = True
            rc = self.do_automation_async(code)
        else:
            is_async = False
            rc = self.run_automation_cmd(cmd_name='DoCommand', value=code)

        res = self.get_log(code, log_path, is_async)
        return {'err': rc, 'res': res}

    def do_automation_async(self, code):
        """Run Stata command in GUI window using DoCommandAsync
        """
        return ''

    def run_automation_cmd(self, cmd_name, value=None, **kwargs):
        """Execute `cmd_name` in a cross-platform manner

        - There are a few commands that take no arguments. For these, leave `value` as None and pass nothing for `kwargs`.
        - Most commands take one argument. For these, pass a `value`.
        - A couple commands take extra arguments. For these, use `kwargs`.
        """

        if platform.system() == 'Windows':
            return getattr(self.stata, 'cmd_name')(value, **kwargs)

        app_name = re.search(r'/?([\w-]+)$', self.stata_path).group(1)
        app_dict = {
            'stata-mp': 'StataMP',
            'stata-se': 'StataSE',
            'stata-ic': 'StataIC'}
        app_name = app_dict.get(app_name, app_name)

        cmd = 'tell application "{}" to {}'.format(app_name, cmd_name)
        if value is not None:
            value = str(value).replace('\n', '\\n').replace('\r', '\\r')
            cmd += ' "{}"'.format(re.sub(r'"', r'\\"', value))
        if kwargs:
            for key, val in kwargs.items():
                if isinstance(val, bool):
                    if val:
                        cmd += ' with {}'.format(key)
                    else:
                        cmd += ' without {}'.format(key)
                elif isinstance(val, int):
                    cmd += ' {} {}'.format(key, val)

        res = run(['osascript', '-e', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.stderr.decode('utf-8'):
            raise OSError(res.stderr.decode('utf-8') + '\nInput: ' + cmd)
        stdout = res.stdout.decode('utf-8').strip()

        # Coerce types
        return self.resolve_return_type(cmd_name, stdout)

    def resolve_return_type(self, cmd_name, stdout):
        """Resolve return type from osascript to Python object
        """
        # Try to coerce stdout into Python type
        if stdout == 'true':
            return True
        if stdout == 'false':
            return False
        try:
            return int(stdout)
        except ValueError:
            pass

        return stdout

    def get_log(self, code, log_path, is_async):
        """Get results from log file
        """

        code_l = code.split(self.eol)
        # The `log using` line doesn't show up in the output
        code_l = code_l[1:]
        # But the `cap log close` does
        code_l.append('cap log close')

        with open(log_path) as f:
            lines = f.readlines()

        # Take off newline character
        lines = [l[:-1] for l in lines]

        # Remove code lines
        if is_async:
            # Add `. ` to code lines
            code_l = ['. ' + x for x in code_l]

        # Find indicies of code lines
        inds = [ind for ind, x in enumerate(lines) if x in code_l]
        begin_inds = [x + 1 for x in inds][:-1]

        if is_async:
            # The empty lines immediately prior to code lines are added and
            # aren't result lines.
            empty_inds = [x - 1 for x in inds]
            for x in empty_inds:
                assert lines[x] == ''

            end_inds = empty_inds[1:]
        else:
            end_inds = inds[1:]

        res = [lines[begin_inds[x]:end_inds[x]] for x in range(len(begin_inds))]
        # First join on a single EOL the lines within each code block. Then join
        # on a double EOL between each code block.
        return (self.eol + self.eol).join([self.eol.join(x) for x in res])

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
