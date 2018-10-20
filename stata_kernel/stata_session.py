import os
import re
import pexpect
import pexpect.fdpexpect
import platform
import requests
import subprocess

from time import sleep
# from timeit import default_timer
from pathlib import Path
from textwrap import dedent
from packaging import version
from pkg_resources import resource_filename

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
        """Initialize Session
        Args:
            kernel (ipykernel.kernelbase): Running instance of kernel
            config (ConfigParser): config class
        """

        self.config = config
        self.kernel = kernel
        self.banner = 'stata_kernel {}\n'.format(kernel.implementation_version)

        try:
            r = requests.get('https://pypi.org/pypi/stata-kernel/json')
            pypi_v = r.json()['info']['version']
            if version.parse(pypi_v) > version.parse(
                    kernel.implementation_version):
                msg = '\nNOTE: A newer version of stata_kernel exists. Run\n'
                msg += '    pip install stata_kernel --upgrade\n'
                msg += 'to install the latest version.\n'
                self.banner += msg
        except requests.exceptions.RequestException:
            pass

        # See https://github.com/kylebarron/stata_kernel/issues/177
        self.linesize = 255
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

        adofile = resource_filename(
            'stata_kernel', 'ado/_StataKernelCompletions.ado')
        adodir = Path(adofile).resolve().parent
        init_cmd = """\
            adopath + `"{0}"\'
            cd `"{1}"\'
            set more on
            set pagesize 100
            set linesize {2}
            clear all
            global stata_kernel_graph_counter = 0

            di "$S_DATE, $S_TIME"
            di "Stata version: `c(version)'"
            di "OS: $S_OS"
            `finished_init_cmd'
            """.format(adodir, os.getcwd(), self.linesize).rstrip()
        self.do(dedent(init_cmd), md5='finished_init_cmd', display=False)
        rc, res = self.do(
            'di "`c(stata_version)\'"\n`done\'', md5='done', display=False)
        self.stata_version = res
        if (platform.system() == 'Windows') and (int(self.stata_version[:2]) <
                                                 15):
            self.config.set('graph_format', 'png', permanent=True)

    def init_windows(self):
        """Start Stata on Windows

        The WinExec step is necessary for some reason to make graphs work. Stata
        can't be launched directly with `win32com.client.Dispatch()`.
        """
        WinExec(self.config.get('stata_path'))
        sleep(0.25)
        self.stata = win32com.client.Dispatch("stata.StataOLEApp")
        self.automate(cmd_name='UtilShowStata', value=1)
        self.config.set('execution_mode', 'automation', permanent=True)
        self.start_log_aut()

    def init_mac_automation(self):
        """Start Stata on macOS"""
        self.automate(cmd_name='activate')
        self.automate(cmd_name='UtilShowStata', value=1)
        self.start_log_aut()

    def init_console(self):
        """Start Stata in console mode

        Spawn stata console and then wait/scroll to initial dot prompt.
        It tries to find the dot prompt immediately; otherwise it assumes
        there's a `more` stopping it, and presses `q` until the more has
        gone away.
        """
        self.child = pexpect.spawn(
            self.config.get('stata_path'), encoding='utf-8',
            codec_errors='replace')
        self.child.setwinsize(100, 255)
        self.child.delaybeforesend = None
        self.child.logfile = (
            self.config.get('cache_dir') / 'console_debug.log').open(
                'w', encoding='utf-8')
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
        self.banner += ansi_escape.sub('', '\n'.join(banner))

    def start_log_aut(self):
        """Start log and watch file

        This is used only when execution_mode is set to Automation. In the
        console mode I watch the pty directly.
        """

        self.automate('DoCommand', 'cap log close stata_kernel_log')

        # There can be several different Stata GUIs open at once, and you can't
        # overwrite an existing log file, since it's still open.
        log_counter = 0
        rc = 1
        while (rc) and (log_counter < 15):
            log_path = self.config.get('cache_dir') / 'log{}.log'.format(
                log_counter)
            cmd = 'log using `"{}"\', replace text name(stata_kernel_log)'.format(
                log_path)
            rc = self.automate('DoCommand', cmd)
            log_counter += 1
            sleep(0.1)

        if rc:
            return rc

        self.fd = Path(log_path).open()
        if platform.system() == 'Windows':
            self.log_fd = pexpect.fdpexpect.fdspawn(
                self.fd, encoding='utf-8', codec_errors='replace')
        else:
            self.log_fd = pexpect.fdpexpect.fdspawn(
                self.fd, encoding='utf-8', maxread=1, codec_errors='replace')

        self.log_fd.logfile = (
            self.config.get('cache_dir') / 'console_debug.log').open(
                'w', encoding='utf-8')

        return 0

    def do(self, text, md5, **kwargs):
        """Main wrapper for sequence of running user-given code

        Args:
            text (str)
            md5 (str): md5 of the text. This is passed to `expect` and is the
                string that declares the end of the text sent to Stata.

        Kwargs:
            text_to_exclude (str): string of text to exclude from output. It is
                expected that this string include many lines. It will be split
                on \\n in `expect`.
            display (bool): Whether to send results to front-end
        """

        self.cache_dir_str = str(self.config.get('cache_dir'))
        if platform.system() == 'Windows':
            self.cache_dir_str = re.sub(r'\\', '/', self.cache_dir_str)

        if self.config.get('execution_mode') == 'console':
            self.child.sendline(text)
            child = self.child
        else:
            self.automate('DoCommandAsync', text)
            child = self.log_fd

        try:
            rc, res = self.expect(text=text, child=child, md5=md5, **kwargs)
        except KeyboardInterrupt:
            self.send_break(child=child, md5="`{}'".format(md5))
            rc, res = 1, ''

        return rc, res

    def expect(self, text, child, md5, text_to_exclude=None, display=True):
        """Watch for end of command from file descriptor or pty

        Args:
            text (str): Text sent to Stata.
            child (pexpect.spawn or fdpexpect.spawn): pty or log file to watch
            md5 (str): current value of md5 to watch for
            text_to_exclude (str): string of text to exclude from output. It is
                expected that this string include many lines. It will be split
                on \\n in `expect`.
        """

        # split text into lines
        if text_to_exclude is not None:
            code_lines = text_to_exclude.split('\n')
        else:
            code_lines = text.split('\n')

        md5 = ". `{}'".format(md5)
        error_re = r'^r\((\d+)\);'

        g_exp = r'\(file ({}'.format(self.cache_dir_str)
        g_fmts = '|'.join(self.kernel.graph_formats)
        g_exp += r'/graph\d+\.({0})) written in ({0}) format\)'.format(g_fmts)
        # Ignore case for SVG/PDF/PNG
        # This is not a `(?i:)` flag to support Python 3.5
        g_exp = re.compile(g_exp, re.IGNORECASE)

        more = r'^--more--'
        eol = r'\r?\n'
        expect_list = [md5, error_re, g_exp, more, eol, pexpect.EOF]

        match_index = -1
        res_list = []
        res_disp = ''
        any_disp = False
        rc = 0
        while match_index != 0:
            match_index = child.expect(expect_list, timeout=None)
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
                g_path = [child.match.group(1)]
                g_fmt = child.match.group(2).lower()
                if g_fmt == 'svg':
                    pdf_dup = self.config.get('graph_svg_redundancy', 'True')
                elif g_fmt == 'png':
                    pdf_dup = self.config.get('graph_png_redundancy', 'False')
                pdf_dup = pdf_dup.lower() == 'true'

                if pdf_dup:
                    while True:
                        ind = child.expect([g_exp, pexpect.EOF], timeout=None)
                        if ind == 0:
                            break
                        sleep(0.1)

                    code_lines = code_lines[1:]
                    g_path.append(child.match.group(1))
                if display:
                    self.kernel.send_image(g_path)
            if match_index == 3:
                self.send_break(child=child, md5=md5[2:])
                child.expect_exact(md5, timeout=None)
                break
            if match_index == 4:
                code_lines, res = self.clean_log_eol(child, code_lines, res)
                if res is None:
                    continue
                res += '\n'
                res = ansi_escape.sub('', res)
                res_disp += res
                res_list.append(res)
                if not ''.join(res_list).strip():
                    continue
                if not res_disp.strip():
                    continue
                else:
                    any_disp = True
                if display:
                    self.kernel.send_response(
                        self.kernel.iopub_socket, 'stream', {
                            'text': res_disp,
                            'name': 'stdout'})
                    res_disp = ''
                continue
            if match_index == 5:
                sleep(0.05)

        res_disp = re.sub(r'\n\Z', '', res_disp, re.M)
        if display and res_disp and any_disp:
            self.kernel.send_response(
                self.kernel.iopub_socket, 'stream', {
                    'text': res_disp,
                    'name': 'stdout'})
            res_disp = ''

        # Then scroll to next newline, but not including period to make it
        # easier to remove code lines later
        child.expect('\r?\n')

        # Remove line continuation markers in output returned internally
        res = ''.join(res_list)
        res = res.replace('\n> ', '')

        return rc, res

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
        regex = r'^\(note: file {}/graph\d+\.({}) not found\)'.format(
            self.cache_dir_str, self.kernel.graph_formats)
        if re.search(regex, res):
            return code_lines, None

        if code_lines == []:
            return code_lines, res

        # On Windows, sometimes there are two spaces between the dot prompt and
        # my code, and sometimes there's only one. This might be a fault of
        # somewhere else in the package, but for now, I let there be either one
        # or two such spaces.
        # If the beginning of the first code line is not in res, return
        if not code_lines[0][:self.linesize - 5].lstrip() in res[1:].lstrip():
            return code_lines, res

        res_match = re.search(r'^(\s*\d+)?\.  ??(.+)$', res)
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

    def send_break(self, child, md5):
        """Send break to Stata

        Tell Stata to stop current execution. This is used when `expect` hits
        more and for a KeyboardInterrupt. I've found that ctrl-C, ctrl-D is the
        most consistent way for the console version to stop execution.

        Often, the first characters after sending ctrl-C, ctrl-D get removed.
        Thus, I send the md5 an extra time so that the full md5 can be matched
        without issues.

        Args:
            child (pexpect.spawn): pexpect instance to send break to
            md5 (str): The md5 to send a second time
        """
        if self.config.get('execution_mode') == 'console':
            child.sendcontrol('c')
            child.sendcontrol('d')
            self.child.sendline(md5)
        else:
            self.automate('UtilSetStataBreak')
            self.automate('DoCommandAsync', md5)

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

        res = subprocess.run(['osascript', '-e', cmd], stdout=subprocess.PIPE,
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

    def shutdown(self):
        if self.config.get('execution_mode') == 'automation':
            self.automate('DoCommandAsync', 'exit, clear')
        else:
            self.child.close(force=True)
        return
