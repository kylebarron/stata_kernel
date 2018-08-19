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
            self.config.set('execution_mode', 'console', permanent=True)

        # Change to this directory and set more off
        adofile = resource_filename(
            'stata_kernel', 'ado/_StataKernelCompletions.ado')
        adodir = Path(adofile).resolve().parent
        self.linesize = 80
        # set more on
        # set pagesize 10
        init_cmd = """\
            adopath + `"{0}"\'
            cd `"{1}"\'
            set linesize {2}
            clear all
            global stata_kernel_graph_counter = 0
            `finished_init_cmd'
            """.format(adodir, os.getcwd(), self.linesize).rstrip()
        self.do(dedent(init_cmd), md5='finished_init_cmd', display=False)

    def init_windows(self):
        # The WinExec step is necessary for some reason to make graphs
        # work. Stata can't be launched directly with Dispatch()
        WinExec(self.config.get('stata_path'))
        sleep(0.25)
        self.stata = win32com.client.Dispatch("stata.StataOLEApp")
        self.automate(cmd_name='UtilShowStata', value=2)
        self.config.set('execution_mode', 'automation', permanent=True)
        self.start_log_aut()

    def init_mac_automation(self):
        self.automate(cmd_name='activate')
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

        Args:
            text (str)
            magics: Not currently implemented

        Kwargs:
            md5 (str): md5 of the text.
            text_to_exclude (str): string of text to exclude from output
            kernel (ipkernel.kernelbase): Running instance of kernel. Passed to expect.
            display (bool): Whether to send results to front-end
        """

        if self.config.get('execution_mode') == 'console':
            self.child.sendline(text)
            try:
                rc, res = self.expect(text=text, child=self.child, md5=md5, **kwargs)
            except KeyboardInterrupt:
                self.child.sendcontrol('c')
                self.child.expect('--Break--')
                self.child.expect('\r\n\. ')
        else:
            self.automate('DoCommandAsync', text)
            try:
                rc, res = self.expect(text=text, child=self.log_fd, md5=md5, **kwargs)
            except KeyboardInterrupt:
                self.automate('UtilSetStataBreak')
                self.log_fd.expect('--Break--')
                self.log_fd.expect('\r?\n\. ')

        return rc, res

    def expect(self, text, child, md5, text_to_exclude=None, display=True):
        """Watch for end of command from file descriptor or TTY

        Args:
            child (pexpect.spawn or fdpexpect.spawn): TTY or log file to watch
            md5 (str): current value of md5 to watch for
        """

        # split text into lines
        if text_to_exclude is not None:
            code_lines = text_to_exclude.split('\n')
        else:
            code_lines = text.split('\n')

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
        res_list = []
        rc = 0
        while match_index != 0:
            match_index = child.expect(expect_list, timeout=5)
            res = child.before
            if match_index == 0:
                break
            if match_index == 1:
                rc = int(child.match.group(1))
                if display:
                    self.kernel.send_response(
                        self.kernel.iopub_socket, 'stream', {
                            'text': 'r({});\n'.format(child.match.group(1)),
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
                res_list.append(res)
                if display:
                    code_lines, res = self.clean_log_eol(child, code_lines, res)
                    if res:
                        self.kernel.send_response(
                            self.kernel.iopub_socket, 'stream', {
                                'text': res + '\n',
                                'name': 'stdout'})
                continue
            if match_index == 5:
                sleep(0.05)

        # Then scroll to next newline, but not including period to make it
        # easier to remove code lines later
        child.expect('\r?\n')

        return rc, '\n'.join(res_list)

    def clean_log_eol(self, child, code_lines, res):
        """Clean output when expect hit a newline

        For the first line, try to match `. {lines[0][:75]}`, i.e. the first
        75 characters of the first line. (75, or linesize - 5) is chosen so
        that it catches lines that are `  1. ` inside a program or for loop

        If it's a match, look at child.before to see how many characters were
        matched. If the line had more characters than were matched, take off
        the first 75 characters, prepend `> ` and try to match again.
        When the full line is matched, remove the first indexed object and
        repeat.

        Args:
            code_lines (List[str]): List of code lines sent to console that have not yet been matched in output
            res (str): Current line of result/output
            l_cont (bool): Whether current line is a line continuation

        Returns:
            (List[str], str, bool)
            - List of code lines not yet matched in output after this
            - Result to be displayed
        """
        if code_lines == []:
            return code_lines, res

        # If the beginning of the first code line is not in res, return
        if not ('. ' + code_lines[0][:self.linesize - 5]) in res:
            return code_lines, res

        res_match = re.search(r'^(  \d+)?\. (.+)$', res)
        if not res_match:
            return code_lines, ''
        res = res_match.group(2)

        # Remove the characters that were matched. If there's still text left,
        # it's on the next line.
        code_lines[0] = code_lines[0][len(res):]
        while code_lines[0]:
            child.expect(r'\r?\n', timeout=5)
            res = child.before
            assert child.before.startswith('> ')
            res = res[2:]
            code_lines[0] = code_lines[0][len(res):]

        return code_lines[1:], None

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
