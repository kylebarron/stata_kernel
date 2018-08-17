import os
import re
import base64
import pexpect
import pexpect.fdpexpect
import platform
import subprocess
from pkg_resources import resource_filename

from time import sleep
from timeit import default_timer
from pathlib import Path
from textwrap import dedent

if platform.system() == 'Windows':
    import win32gui
    import win32com.client
    from win32api import WinExec

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


class StataSession():
    def __init__(self, kernel, config):
        """
        Args:
            config (ConfigParser): config class
        """

        self.config = config
        self.kernel = kernel

        graph_export_size = {
            'pdf': None,
            'svg': ' width({0}px) height({1}px)',
            'tif': ' width({0}) height({1})',
            'png': ' width({0}) height({1})'}

        self.graph_size = graph_export_size[self.config.get('graph_format')]
        self.graph_cmd = 'qui graph export `"{0}/graph.{1}"\' , as({1}) replace'
        self.img_metadata = {'width': 600, 'height': 400}
        self.banner = 'stata_kernel: A Jupyter kernel for Stata.'

        if platform.system() == 'Windows':
            self.init_windows()
        elif platform.system() == 'Darwin':
            if self.config.get('execution_mode') == 'automation':
                self.init_mac_automation()
            else:
                self.init_console()
        else:
            self.init_console()

        # Change to this directory and set more off
        adofile = resource_filename(
            'stata_kernel', 'ado/_StataKernelCompletions.ado')
        adodir = Path(adofile).resolve().parent
        init_cmd = """\
            adopath + `"{0}"\'
            cd `"{1}"\'
            set more on
            set pagesize 10
            clear all
            global stata_kernel_graph_counter = 0
            `finished_init_cmd'
            """.format(adodir, os.getcwd())
        self.do(dedent(init_cmd), md5='finished_init_cmd', display=False)

    def init_windows(self):
        # The WinExec step is necessary for some reason to make graphs
        # work. Stata can't be launched directly with Dispatch()
        WinExec(self.config.get('stata_path'))
        sleep(0.25)
        self.stata = win32com.client.Dispatch("stata.StataOLEApp")
        window = win32gui.GetForegroundWindow()
        win32gui.MoveWindow(window, 0, 0, 1920, 1080, True)
        self.automate(cmd_name='UtilShowStata', value=2)
        self.start_log_aut()

    def init_mac_automation(self):
        self.automate(cmd_name='activate')
        cmd = 'set bounds of front window to {1, 1, 1280, 900}'
        self.automate(cmd_name=cmd)
        self.automate(cmd_name='UtilShowStata', value=1)
        self.start_log_aut()

    def init_console(self):
        """Initiate stata console

        Spawn stata console and then wait/scroll to initial dot prompt.
        It tries to find the dot prompt immediately; otherwise it assumes
        there's a `more` stopping it, and presses `q` until the more has
        gone away.
        """
        self.child = pexpect.spawn(
            self.config.get('stata_path'), encoding='utf-8')
        self.child.logfile = open(
            self.config.get('cache_dir') / 'console_debug.log', 'w')
        banner = []
        try:
            self.child.expect('\r\n\. ', timeout=0.2)
            banner.append(self.child.before)
        except pexpect.TIMEOUT:
            try:
                while True:
                    self.child.expect('more', timeout=0.1)
                    banner.append(self.child.before)
                    self.child.send('q')
            except pexpect.TIMEOUT:
                self.child.expect('\r\n\. ')
                banner.append(self.child.before)

        # Set banner to Stata's shell header
        self.banner = ansi_escape.sub('', '\n'.join(banner))

    def start_log_aut(self):
        """Start log and watch file

        This is only on Automation. On console I watch the TTY directly.
        """

        self.automate('DoCommand', 'cap log close _all')
        log_path = self.config.get('cache_dir') / 'log.log'
        cmd = 'log using `"{}"\', replace text'.format(log_path)
        rc = self.automate('DoCommand', cmd)
        if rc:
            return rc

        self.fd = open(log_path)
        if platform.system() == 'Windows':
            self.log_fd = pexpect.fdpexpect.fdspawn(self.fd, encoding='utf-8')
        else:
            self.log_fd = pexpect.fdpexpect.fdspawn(
                self.fd, encoding='utf-8', maxread=1)
        return 0

    def do(self, text, md5, magics=None, **kwargs):
        """Main wrapper for sequence of running user-given code

        Probably don't use this for internal code run by kernel

        Args:
            text (str)
            magics: Not currently implemented

        Kwargs:
            md5 (str): md5 of the text.
            kernel (ipkernel.kernelbase): Running instance of kernel. Passed to expect.
            display (bool): Whether to send results to front-end
        """

        if self.config.get('execution_mode') == 'console':
            self.child.sendline(text)
            try:
                self.expect(child=self.child, md5=md5, **kwargs)
            except KeyboardInterrupt:
                self.child.sendcontrol('c')
                self.child.expect('--Break--')
                self.child.expect('\r\n\. ')
        else:
            self.automate('DoCommandAsync', text)
            try:
                self.expect(child=self.log_fd, md5=md5, **kwargs)
            except KeyboardInterrupt:
                self.automate('UtilSetStataBreak')
                self.log_fd.expect('--Break--')
                self.log_fd.expect('\r?\n\. ')

        return

    def expect(self, child, md5, display=True):
        """Watch for end of command from file descriptor or TTY

        Args:
            child (pexpect.spawn or fdpexpect.spawn): TTY or log file to watch
            md5 (str): current value of md5 to watch for
        """

        md5 = '`' + md5 + "'"
        error_re = r'^r\((\d+)\);'
        cache_dir_str = str(self.config.get('cache_dir'))
        if platform.system() == 'Windows':
            cache_dir_str = re.sub(r'\\', '/', cache_dir_str)

        g_exp = r'\(file {}'.format(cache_dir_str)
        g_exp += r'/graph(\d+)\.(svg|pdf|tif|png) written in '
        g_exp += r'(?i:(svg|pdf|tif|png)) format\)'

        more = r'^--more--'
        eol = r'\r?\n'
        expect_list = [md5, error_re, g_exp, more, eol, pexpect.EOF]

        match_index = -1
        while match_index != 0:
            match_index = child.expect(expect_list, timeout=5)
            line = child.before
            if match_index == 0:
                break
            if match_index == 1:
                # print('error:', 'r({});'.format(child.match.group(1)))
                if display:
                    self.kernel.send_response(
                        self.kernel.iopub_socket, 'stream', {
                            'text': line,
                            'name': 'stderr'})
                continue
            if match_index == 2:
                img = self.load_graph(child.match.group(1))
                if display:
                    self.kernel.send_image(img)
            if match_index == 3:
                child.sendline('q')
                break
            if match_index == 4:
                # print('result:', line)
                if display:
                    self.kernel.send_response(
                        self.kernel.iopub_socket, 'stream', {
                            'text': line + '\n',
                            'name': 'stdout'})
                continue
            if match_index == 5:
                sleep(0.05)

        # Then scroll to next newline, but not including period to make it easier to remove code lines later
        child.expect('\r?\n')

    def automate(self, cmd_name, value=None, **kwargs):
        """Execute `cmd_name` through Automation in a cross-platform manner

        - There are a few commands that take no arguments. For these, leave `value` as None and pass nothing for `kwargs`.
        - Most commands take one argument. For these, pass a `value`.
        - A couple commands take extra arguments. For these, use `kwargs`.
        """

        if platform.system() == 'Windows':
            if value is None:
                return getattr(self.stata, cmd_name)()
            return getattr(self.stata, cmd_name)(value, **kwargs)

        app_name = Path(self.config.get('stata_path')).name
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

        res = subprocess.run(['osascript', '-e', cmd],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        if res.stderr:
            raise OSError(res.stderr.decode('utf-8') + '\nInput: ' + cmd)
        return self.resolve_return_type(cmd_name, res.stdout.decode('utf-8'))

    def resolve_return_type(self, cmd_name, stdout):
        """Resolve return type from osascript to Python object

        This must match the output type return by Windows Automation for the
        same command
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

    def clean_log_console(self, log, syn_chunks):
        """Clean output from console

        Args:
            log (List[str]):
                Text returned from each syntactic chunk of Stata code.
            syn_chunks (List[Tuple[Token, str]]):
                Input chunks. `len(syn_chunks) >= len(log)` because there
                could have been an error in the middle.

        Returns:
            str: Text to return to user.
        """

        # Don't keep chunks that weren't executed
        syn_chunks = syn_chunks[:len(log)]

        # Take out line continuations for both input and results
        log = [re.sub(r'\r\n> ', '', x) for x in log]

        log_all = []
        for (Token, code_line), log_line in zip(syn_chunks, log):
            if str(Token) != 'Token.TextBlock':
                # Since I'm sending one line at a time, and since it's not a
                # block, the first line should equal the text sent
                # The assert is just a sanity check for now.
                log_line = log_line.split('\r\n')
                assert log_line[0] == code_line
                log_all.extend(log_line[1:])
                log_all.append('')
            else:
                # Split input and output
                code_lines = code_line.split('\n')
                log_lines = log_line.split('\r\n')
                log_all.extend([
                    x for x in log_lines if not any(y in x
                                                    for y in code_lines)])
                log_all.append('')

        return '\n'.join(log_all)

    def clean_log_aut(self, log, syn_chunks):
        """Do initial Automation-specific log cleaning

        I know that code is run in order. So I'll search the log lines for the
        first line of syn_chunks. Once I find it, I'll search for the next, etc.

        First I'll turn syn_chunks into a list of strings that the code lines in
        the output should start with. Then I'll use those lines to search the
        log in order.

        Args:
            log (str): Contents of log file
            syn_chunks (List[Tuple[Token, str]]):
                Input chunks. `len(syn_chunks) >= len(log)` because there
                could have been an error in the middle.
        """

        # Remove line continuations
        log = re.sub(r'\n> ', '', log)
        log = log.split('\n')

        log = log[5:]
        # Note: I know this leaves `cap log close`.
        log = log[:-1]

        # Add `cap noi ` to the beginning of code lines that were sent with
        # DoCommandAsync
        syn_chunks_new = []
        for (Token, code_lines) in syn_chunks:
            if str(Token) == 'Token.TextBlock':
                syn_chunks_new.append((Token, 'cap noi ' + code_lines))
            else:
                syn_chunks_new.append((Token, code_lines))
        syn_chunks = syn_chunks_new

        # Now turn syn_chunks into a list of code lines
        all_code_lines = []
        # Since I run `log using` with DoCommand
        # It's weird, but sometimes there's a single leading whitespace. Usually
        # there isn't, but it seems that when I run two loop blocks in a row
        # (ish?), then there's a leading whitespace on the second one. So after
        # this for loop, I set the first line to `inexact` matching.
        last_whitespace = ''
        for (Token, code_lines) in syn_chunks:
            if str(Token) != 'Token.TextBlock':
                # Means I sent it with DoCommand; there should be no leading
                # spaces. Also means it should be a single line
                all_code_lines.append(['exact', last_whitespace + code_lines])
                last_whitespace = ''
                continue

            # So it's a block
            lines = code_lines.split('\n')

            # Blocks where the inner lines are indented and numbered
            keywords = [
                r'pr(o|og|ogr|ogra|ogram)?', r'while',
                r'forv(a|al|alu|alue|alues)?', r'foreach']
            keywords = r'\b(' + '|'.join(keywords) + r')\b'
            if re.search(keywords, lines[0][8:]):
                block_counter = 1
                for line in lines:
                    all_code_lines.append(['exact', last_whitespace + line])
                    block_counter += 1
                    last_whitespace = '  {}. '.format(block_counter)

                last_whitespace = '. '
                continue

            # If/else/else if blocks
            # These lead following lines with .
            if any(lines[0][8:].startswith(x)
                   for x in ['if', 'else', 'else if']):
                for line in lines:
                    all_code_lines.append(['exact', last_whitespace + line])
                    last_whitespace = '. '
                continue

            cap_reg = re.compile(r'\bcap(t|tu|tur|ture)?\b').search
            qui_reg = re.compile(r'\bqui(e|et|etl|etly)?\b').search
            noi_reg = re.compile(r'\bn(o|oi|ois|oisi|oisil|oisily)?\b').search
            # If `cap` or both `qui` and `cap` show up after my cap noi, no
            # following code lines will be printed.
            if cap_reg(lines[0][8:]) and not noi_reg(lines[0][8:]):
                all_code_lines.append(['exact', last_whitespace + lines[0]])
                last_whitespace = '. '
                continue

            if noi_reg(lines[0][8:]) or qui_reg(lines[0][8:]):
                for line in lines:
                    all_code_lines.append(['exact', last_whitespace + line])
                    last_whitespace = '. '
                continue

            # Otherwise, I don't know what it is
            for line in lines:
                all_code_lines.append(['inexact', line])
                last_whitespace = '. '

        all_code_lines[0][0] = 'inexact'

        code_line_idxs = [len(log) - 1]
        log_line_counter = 0
        for (match_type, code_line) in all_code_lines:
            if match_type == 'exact':
                idx = log.index(code_line, log_line_counter)
            else:
                idx = [
                    ind for ind, x in enumerate(log[log_line_counter:])
                    if code_line in x][0]
            log_line_counter = idx + 1
            code_line_idxs.append(idx)

        # If I just want to remove code lines
        # [x for ind, x in enumerate(log) if ind not in code_line_idxs]

        start_idxs = [
            ind for ind, x in enumerate(log)
            if (ind not in code_line_idxs) and (ind - 1 in code_line_idxs)]
        end_idxs = [
            ind + 1
            for ind, x in enumerate(log)
            if (ind not in code_line_idxs) and (ind + 1 in code_line_idxs)]

        all_log_chunks = []
        for start_idx, end_idx in zip(start_idxs, end_idxs):
            all_log_chunks.append('\n'.join(log[start_idx:end_idx]))

        return '\n'.join(all_log_chunks)

    def load_graph(self, graph_counter):
        """Load graph

        Args:
            graph_counter (str): graph counter of current graph

        Returns:
            image (str if svg; else bytes (or base64 string?))
        """

        if self.config.get('graph_format') == 'svg':
            read_format = 'r'
        else:
            read_format = 'rb'
        with open(self.config.get('cache_dir') / 'graph{}.{}'.format(
                graph_counter, self.config.get('graph_format')),
                  read_format) as f:
            img = f.read()

        if read_format == 'rb':
            img = base64.b64encode(img).decode('utf-8')

        return img

    def shutdown(self):
        if self.config.get('execution_mode') == 'automation':
            self.automate('DoCommandAsync', 'exit, clear')
        else:
            self.child.close(force=True)
        return
