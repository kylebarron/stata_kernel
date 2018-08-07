import os
import re
import platform
import subprocess

from time import sleep
from subprocess import run
from dateutil.parser import parse
from configparser import ConfigParser
from ipykernel.kernelbase import Kernel

if platform.system() == 'Windows':
    import win32com.client
    import win32gui
    from win32api import WinExec
else:
    import pexpect

# Regex from: https://stackoverflow.com/a/45448194
ansi_regex = r'\x1b(' \
             r'(\[\??\d+[hl])|' \
             r'([=<>a-kzNM78])|' \
             r'([\(\)][a-b0-2])|' \
             r'(\[\d{0,2}[ma-dgkjqi])|' \
             r'(\[\d+;\d+[hfy]?)|' \
             r'(\[;?[hf])|' \
             r'(#[3-68])|' \
             r'([01356]n)|' \
             r'(O[mlnp-z]?)|' \
             r'(/Z)|' \
             r'(\d+)|' \
             r'(\[\?\d;\d0c)|' \
             r'(\d;\dR))'
ansi_escape = re.compile(ansi_regex, flags=re.IGNORECASE)


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
        self.execution_mode = config['stata_kernel']['execution_mode']
        self.stata_path = config['stata_kernel']['stata_path']

        if self.execution_mode.lower() == 'automation':
            if platform.system() == 'Windows':
                # The WinExec step is necessary for some reason to make graphs
                # work. Stata can't be launched directly with Dispatch()
                WinExec(self.stata_path)
                sleep(0.25)
                self.stata = win32com.client.Dispatch("stata.StataOLEApp")
                window = win32gui.GetForegroundWindow()
                win32gui.MoveWindow(window, 0, 0, 1920, 1080, True)
                self.run_automation_cmd(cmd_name='UtilShowStata', value=2)
            else:
                self.run_automation_cmd(cmd_name='activate')
                self.run_automation_cmd(cmd_name='UtilShowStata', value=1)
                cmd = 'set bounds of front window to {1, 1, 1280, 900}'
                self.run_automation_cmd(cmd_name=cmd)

            # TODO: Change directory to that of running code
            self.run_automation_cmd(cmd_name='DoCommand', value='set more off')
            self.banner = 'Jupyter kernel for Stata'

        else:
            # Spawn stata console and then wait/scroll to initial dot prompt.
            # It tries to find the dot prompt immediately; otherwise it assumes
            # there's a `more` stopping it, and presses `q` until the more has
            # gone away.
            self.child = pexpect.spawn(self.stata_path, encoding='utf-8')
            banner = []
            try:
                self.child.expect('\r\n\.', timeout=0.2)
                banner.append(self.child.before)
            except pexpect.TIMEOUT:
                try:
                    while True:
                        self.child.expect('more', timeout=0.1)
                        banner.append(self.child.before)
                        self.child.send('q')
                except pexpect.TIMEOUT:
                    self.child.expect('\r\n\.')
                    banner.append(self.child.before)

            # Set banner to Stata's shell header
            banner = '\n'.join(banner)
            banner = ansi_escape.sub('', banner)

            # Remove extra characters before first \r\n
            self.banner = re.sub(r'^.*\r\n', '', banner)

            # Set more off
            self.run_shell('set more off')

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

        code = self.remove_comments(code)
        graph_keywords = [
            r'gr(a|ap|aph)?', r'tw(o|ow|owa|oway)?',
            r'sc(a|at|att|atte|atter)?', r'line']
        graph_keywords = r'\b(' + '|'.join(graph_keywords) + r')\b'
        check_graphs = re.search(graph_keywords, code)

        obj = self.do(code)
        res = obj.get('res').rstrip()
        stream_content = {'text': res}

        # The base class increments the execution count
        return_obj = {'execution_count': self.execution_count}
        if obj.get('err'):
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
        code = code.strip()
        if code.endswith('///'):
            return {'status': 'incomplete', 'indent': '    '}

        lines = [x.strip() for x in code.split('\n')]
        n_open = len([x for x in lines if x.endswith('{')])
        n_closed = len([x for x in lines if x.startswith('}')])
        if n_open > n_closed:
            return {'status': 'incomplete', 'indent': '    '}

        open_pr = r'^\s*(pr(ogram|ogra|ogr|og|o)?)\s+(de(fine|fin|fi|f)?\s+)?'
        closed_pr = r'^\s*end\s*'
        n_open = len([x for x in lines if re.search(open_pr, x)])
        n_closed = len([x for x in lines if re.search(closed_pr, x)])
        if n_open > n_closed:
            return {'status': 'incomplete', 'indent': '    '}

        open_input = r'^\s*inp(u|ut)?'
        closed_input = r'^\s*end\s*'
        n_open = len([x for x in lines if re.search(open_input, x)])
        n_closed = len([x for x in lines if re.search(closed_input, x)])
        if n_open > n_closed:
            return {'status': 'incomplete', 'indent': '    '}

        return {'status': 'complete'}

    def do(self, code):
        """A wrapper for the platform-dependent run functions"""
        if self.execution_mode == 'console':
            obj = self.run_shell(code)
        else:
            obj = self.do_automation(code)

        # Remove ANSI escape sequences. These are weird pieces of text added by
        # some shells
        obj['res'] = ansi_escape.sub('', obj['res'])
        return obj

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

        keywords = [
            r'pr(o|og|ogr|ogra|ogram)?', r'while',
            r'forv(a|al|alu|alue|alues)?', r'foreach', r'inp(u|ut)?',
            r'e(x|xi|xit)?']
        keywords = r'\b(' + '|'.join(keywords) + r')\b'
        has_blocks = re.search(keywords, code)

        # Split user code into lines
        code = re.sub(r'\r\n', r'\n', code)
        lines = code.split('\n')

        # Remove leading and trailing whitespace from lines. This shouldn't
        # matter because Stata doesn't give a semantic meaning to whitespace.
        lines = [x.strip() for x in lines]

        # Make sure no empty lines. If empty line, there's no blank line in the
        # stata window between the dot prompts, so the current expect regex
        # fails.
        lines = [x for x in lines if x != '']
        results = []
        for line in lines:
            self.child.sendline(line)
            if has_blocks:
                try:
                    self.child.expect('\r\n  \d\. ', timeout=0.1)
                    continue
                except pexpect.TIMEOUT:
                    pass

            self.child.expect('(?<=(\r\n)|(\x1b=))\r\n\. ', timeout=3)
            res = self.child.before

            # Remove input command, up to first \r\n
            res = re.sub(r'^.+\r\n', '', res)

            # Check error
            err = re.search(r'\r\nr\((\d+)\);', res)
            if err:
                return {'err': err.group(1), 'res': res}

            results.append(res)

        return {'err': '', 'res': '\n'.join(results)}

    def do_automation(self, code):
        """Run Stata command in GUI window using Stata Automation

        If the command doesn't use `program`, `while`, `forvalues`, `foreach`,
        `input`, or `exit`, I run it using DoCommand. This means that I don't
        have to poll for when the command has completed.
        """

        # Save output to log file
        log_path = os.getcwd() + '/.stata_kernel_log.log'
        code = 'log using `"{}"\', replace text{}{}'.format(
            log_path, os.linesep, code)
        code = code.rstrip() + os.linesep + 'cap log close'

        keywords = [
            r'pr(o|og|ogr|ogra|ogram)?', r'while',
            r'forv(a|al|alu|alue|alues)?', r'foreach', r'inp(u|ut)?',
            r'e(x|xi|xit)?']
        keywords = r'\b(' + '|'.join(keywords) + r')\b'
        if re.search(keywords, code):
            is_async = True
            rc = self.do_automation_async(code)
        else:
            is_async = False
            # On Windows, I need to run one line of code at a time through
            # DoCommand. For some reason, code with embedded newlines only works
            # with DoCommandAsync. For that I can use either `\r` or `\n`. It
            # actually seems that using `\r\n`  gives an extra empty line in the
            # output.
            if platform.system() == 'Darwin':
                rc = self.run_automation_cmd(
                    cmd_name='DoCommand', value=code, stopOnError=True)
                if rc == 1:
                    self.run_automation_cmd(
                        cmd_name='DoCommand', value='cap log close')
            else:
                lines = code.split(os.linesep)
                for l in lines:
                    rc = self.run_automation_cmd(cmd_name='DoCommand', value=l)
                    if rc != 0:
                        # If error, still close log file
                        rc = self.run_automation_cmd(
                            cmd_name='DoCommand', value=lines[-1])
                        break

        obj = self.get_log(code, log_path, is_async)
        res = obj.get('res')
        if is_async:
            rc = obj.get('err')
        return {'err': rc, 'res': res}

    def do_automation_async(self, code):
        """Run Stata command in GUI window using DoCommandAsync
        """
        self.run_automation_cmd(cmd_name='DoCommandAsync', value=code)
        finished = 0
        while not finished:
            sleep(0.25)
            finished = self.run_automation_cmd('UtilIsStataFree')
        return ''

    def run_automation_cmd(self, cmd_name, value=None, **kwargs):
        """Execute `cmd_name` in a cross-platform manner

        - There are a few commands that take no arguments. For these, leave `value` as None and pass nothing for `kwargs`.
        - Most commands take one argument. For these, pass a `value`.
        - A couple commands take extra arguments. For these, use `kwargs`.
        """

        if platform.system() == 'Windows':
            if value is None:
                return getattr(self.stata, cmd_name)()
            return getattr(self.stata, cmd_name)(value, **kwargs)

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

        res = run(['osascript', '-e', cmd],
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE)
        if res.stderr:
            stderr = res.stderr.decode('utf-8')
            if 'the command resulted in non-zero return code' in stderr:
                return 1
            else:
                raise OSError(res.stderr.decode('utf-8') + '\nInput: ' + cmd)
        stdout = res.stdout.strip()

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

    def check_graphs(self):
        cur_names = self.do('graph dir')['res']
        cur_names = cur_names.strip().split(' ')
        cur_names = [x.strip() for x in cur_names]
        graphs_to_get = []
        for name in cur_names:
            if not self.graphs.get(name):
                graphs_to_get.append(name)
                continue

            stamp = self.get_graph_timestamp(name)
            if stamp > self.graphs.get(name):
                graphs_to_get.append(name)

        return graphs_to_get

    def get_graph_timestamp(self, name):
        # Get timestamp of graph and save to dict
        res = self.do('graph describe ' + name)['res']
        lines = res.split('\n')
        stamp = [x for x in lines if 'created' in x]
        # I.e. non-English Stata
        if not stamp:
            stamp = lines[5][13:].strip()
        else:
            stamp = stamp[0][13:].strip()

        return parse(stamp)

    def get_graph(self, name):
        cwd = os.getcwd()
        # Export graph to file
        self.do('cap mkdir `"{}/.stata_kernel_images"\''.format(cwd))
        cmd = 'graph export `"{}/.stata_kernel_images/{}.svg"\' , '.format(
            cwd, name)
        cmd += 'name({}) as(svg) replace'.format(name)
        self.do(cmd)

        # Read image
        with open(cwd + '/.stata_kernel_images/' + name + '.svg') as f:
            img = f.read()

        self.graphs[name] = self.get_graph_timestamp(name)

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
