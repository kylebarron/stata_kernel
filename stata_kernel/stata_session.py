import re
import platform
import subprocess

from time import sleep

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

class StataSession(object):
    def __init__(self, execution_mode, stata_path, cache_dir):

        self.execution_mode = execution_mode
        self.banner = 'stata_kernel: A Jupyter kernel for Stata.'
        self.cache_dir = cache_dir
        # Make sure cache_dir exists
        self.graph_counter = 0
        if platform.system() == 'Windows':
            self.execution_mode = 'automation'
            self.init_windows(stata_path)
        elif platform.system() == 'Darwin':
            if execution_mode == 'automation':
                self.init_mac_automation()
            else:
                self.init_console(stata_path)
        else:
            self.execution_mode = 'console'
            self.init_console(stata_path)

    def init_windows(self, stata_path):
        # The WinExec step is necessary for some reason to make graphs
        # work. Stata can't be launched directly with Dispatch()
        WinExec(stata_path)
        sleep(0.25)
        self.stata = win32com.client.Dispatch("stata.StataOLEApp")
        window = win32gui.GetForegroundWindow()
        win32gui.MoveWindow(window, 0, 0, 1920, 1080, True)
        self.run_automation_cmd(cmd_name='UtilShowStata', value=2)

    def init_mac_automation(self):
        self.run_automation_cmd(cmd_name='activate')
        self.run_automation_cmd(cmd_name='UtilShowStata', value=1)
        cmd = 'set bounds of front window to {1, 1, 1280, 900}'
        self.run_automation_cmd(cmd_name=cmd)

    def init_console(self, stata_path):
        """Initiate stata console

        Spawn stata console and then wait/scroll to initial dot prompt.
        It tries to find the dot prompt immediately; otherwise it assumes
        there's a `more` stopping it, and presses `q` until the more has
        gone away.

        Args:
            stata_path (str): Path to stata executable

        """
        self.child = pexpect.spawn(stata_path, encoding='utf-8')
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

    def do(self, chunks):
        """Run code in Stata

        This is a wrapper for the platform-dependent functions.

        Args:
            (List[Tuple[Token, str]]):
                Each tuple should have two elements. The first is the name of
                the Token, the second is the string to send to Stata.

        NOTE I might end up needing more metadata about the chunks, so this is subject to change format.

        NOTE I might put in here a regex that catches graph commands. I could either automatically add a command for `graph export` after each `graph` command, or I could try to keep a record of the current state of graphs and send one when I think a new one has been created.

            I think the former would actually have less false positives. When
            using `graph dir` and `graph describe`, it only shows you graph
            timestamps to the minute.

            Note, though, that there are _many_ graph commands, and it would be
            a pain to write a regex for them all. See: `help graph_other`

            graph_keywords = [
                r'gr(a|ap|aph)?', r'tw(o|ow|owa|oway)?',
                r'sc(a|at|att|atte|atter)?', r'line']
            graph_keywords = r'\b(' + '|'.join(graph_keywords) + r')\b'
            check_graphs = re.search(graph_keywords, code)

        NOTE: Also don't forget to prevent any empty lines from going to Stata
        """

        if self.execution_mode == 'console':
            log = []
            for line in chunks:
                obj = self.do_console(line)
                log.append(obj['res'])
                if obj['rc']:
                    # stop running lines, return current results
                    break
                if 'get_graph':
                    img = self.get_graph()

            return log

        # Use token names to decide which chunks can be sent through DoCommand
        # and which need to be sent through DoCommandAsync.
        log_path = self.cache_dir + '/.stata_kernel_log.log'
        rc = self.automate('DoCommand', 'log using `"{}"\', replace text'.format(log_path))
        if rc:
            # Cache location is non writable
            return

        for line in chunks:
            if line['block']:
                rc = self.do_aut_async(line)
            else:
                rc = self.do_aut_sync(line)
            if rc:
                # stop running lines, return current results
                break
            if 'get_graph':
                img = self.get_graph()
        rc = self.automate('DoCommand', 'cap log close')

        return log


    def do_console(self, line):
        """Run Stata command in console

        In the console, Stata runs one syntactic chunk at a time. Usually this
        is a line, ending with a newline. For/while loops, blocks, `program`,
        and `input`, are all multiline syntactic chunks. Stata will not show
        another dot prompt until the entire chunk has been pasted. Therefore I
        must only send complete syntactic chunks to Stata.

        The regex that I expect on is `(?<=(\r\n)|(\x1b=))\r\n\. `. The basic
        `\r\n\.` regex would have too many false-positives. Any results with a
        dot and a space could have pexpect thinking that a result is actually
        the next prompt. This would be bad and would cause following results to
        be out of order.

        Using `\r\n\r\n\. ` is better but I found that the command `shell`
        returns some ANSI escape codes between lines, and thus I needed to allow
        for an ANSI escape code.

        NOTE will need to set timeout to None once sure that running is stable.
        Otherwise running a task longer than 30s would timeout.

        Args:
            chunks (List[Tuple[Token, str]]):
                list of strings that are ready to send to Stata.
                NOTE I might end up needing more metadata about the chunks, so
                this is subject to change format.

        Returns:
            dict {
                'err': error code as a number,
                'res': unmodified output from line}
        """

        self.child.sendline(line)
        self.child.expect('(?<=(\r\n)|(\x1b=))\r\n\. ', timeout=20)
        res = self.child.before
        res = ansi_escape.sub('', res)

        # Check error
        err = re.search(r'\r\nr\((\d+)\);', res)
        if err:
            rc = int(err.group(1))
        else:
            rc = 0

        return {'err': rc, 'res': res}

    def do_aut_sync(self, line):
        """Run code in Stata Automation using DoCommand

        In general, DoCommand is desired rather than DoCommandAsync:
            1. DoCommand will stop on error (NOTE check this is always true for Windows).
            2. DoCommand returns the return code, so you don't have to check the log for errors.
            3. DoCommand is synchronous, so I don't have to keep polling for the command to have finished.

        However, the drawback of DoCommand is that there are a few commands that
        don't work. Namely `program`, `while`, `forvalues`, `foreach`, `input`,
        and `exit`. Because these are basically all multiline inputs, I run
        DoCommand for all non-multiline inputs.

        On Windows, DoCommand only allows one line of code at a time. Since I'm
        sending one line of code at a time to the console anyways, it's easy
        enough to just have all do functions run one syntactic line at a time.

        """

        return self.automate('DoCommand', line)

    def do_aut_async(self, line):
        """Run code in Stata Automation using DoCommandAsync

        When running a command with DoCommandAsync, the return code is always 0
        because the command is just put onto the queue. Stata Automation has the
        command `UtilStataErrorCode`, but that gives the value of _rc and _rc
        won't be defined unless you use `cap`. `cap` by default silences output,
        so I need to use `cap noi`.

        In Stata 15, there is no issue with using multiple of the same prefix,
        and the last prefix between `qui` and `noi` is the one that determines
        output showing. So if the user wanted to have it be quiet, it would
        still be quiet with an extra `cap noi` prefixed.
        """

        line = 'cap noi ' + line
        self.automate('DoCommandAsync', line)
        finished = 0
        while not finished:
            # NOTE What should the optimal sleep time be?
            # Should it be in the settings?
            sleep(0.25)
            finished = self.run_automation_cmd('UtilIsStataFree')

        return self.automate('UtilStataErrorCode')

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

    def export_graph(self):
        """
        NOTE: unclear whether I actually need to save all the graphs individually, or if I can just overwrite one. Since I'm just writing them to load them into Python, and the next graph shouldn't start writing until I'm done reading the previous one into Python, I can probably just overwrite the same file.
        """
        # Export graph to file
        cmd = 'qui graph export `"{0}/graph{1}.{2}"\' , as({2}) replace'.format(
            self.cache_dir, self.graph_counter, self.graph_format)
        self.do(cmd)

        # Read image
        with open('{}/graph{}.{}'.format(self.cache_dir, self.graph_counter, self.graph_format)) as f:
            img = f.read()

        self.graph_counter += 1
        return img
