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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stata_path = stata_path
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
        self.automate(cmd_name='UtilShowStata', value=2)

    def init_mac_automation(self):
        self.automate(cmd_name='activate')
        self.automate(cmd_name='UtilShowStata', value=1)
        cmd = 'set bounds of front window to {1, 1, 1280, 900}'
        self.automate(cmd_name=cmd)

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

    def do(self, syn_chunks):
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
            rc = 0
            err_regex = re.compile(r'\r\nr\((\d+)\);\r\n').search
            for line in syn_chunks:
                res = self.do_console(line[1])
                log.append(res)
                err = err_regex(res)
                if err:
                    rc = int(err.group(1))
                    break
                # if 'get_graph':
                #     img = self.get_graph()

            return rc, self.clean_log_console(log, syn_chunks)
        else:
            # Blocks will be sent through DoCommandAsync while everything else
            # will be sent through docommand
            log_path = self.cache_dir + '/.stata_kernel_log.log'
            rc = self.automate(
                'DoCommand', 'log using `"{}"\', replace text'.format(log_path))
            if rc:
                return rc, ''

            # Keep track of how many chunks have been executed
            syn_chunk_counter = 0
            for line in syn_chunks:
                syn_chunk_counter += 1
                if str(line[0]) == 'Token.MatchingBracket.Other':
                    rc = self.do_aut_async(line[1])
                else:
                    rc = self.do_aut_sync(line[1])
                if rc:
                    break
                # if 'get_graph':
                #     img = self.get_graph()
            self.automate('DoCommand', 'cap log close')
            with open(log_path, 'r') as f:
                log = f.read()

            # Don't keep chunks that weren't executed
            syn_chunks = syn_chunks[:syn_chunk_counter]

            return rc, self.clean_log_aut(log, syn_chunks)

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
            line (str): literal string ready to send to Stata
        Returns:
            (str): unmodified output from line
        """

        self.child.sendline(line)
        regex = r'\r\n(\x1b\[\?1h\x1b=)?\r\n\. '
        self.child.expect(regex, timeout=20)
        return ansi_escape.sub('', self.child.before)

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

        Args:
            line (str): literal string ready to send to Stata
        Returns:
            (int): return code from Stata
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
            finished = self.automate('UtilIsStataFree')

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
            if str(Token) != 'Token.MatchingBracket.Other':
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
        log = log[:-1]

        # Add `cap noi ` to the beginning of code lines that were sent with
        # DoCommandAsync
        syn_chunks_new = []
        for (Token, code_lines) in syn_chunks:
            if str(Token) == 'Token.MatchingBracket.Other':
                syn_chunks_new.append((Token, 'cap noi ' + code_lines))
            else:
                syn_chunks_new.append((Token, code_lines))
        syn_chunks = syn_chunks_new

        # Now turn syn_chunks into a list of code lines
        all_code_lines = []
        # Since I run `log using` with DoCommand
        last_whitespace = ''
        for (Token, code_lines) in syn_chunks:
            if str(Token) != 'Token.MatchingBracket.Other':
                # Means I sent it with DoCommand; there should be no leading
                # spaces. Also means it should be a single line
                all_code_lines.append(('exact', last_whitespace + code_lines))
                last_whitespace = ''
                continue

            # So it's a block
            lines = code_lines.split('\n')

            # Blocks where the inner lines are indented and numbered
            keywords = [r'pr(o|og|ogr|ogra|ogram)?', r'while',
                r'forv(a|al|alu|alue|alues)?', r'foreach']
            keywords = r'\b(' + '|'.join(keywords) + r')\b'
            if re.search(keywords, lines[0][8:]):
                block_counter = 1
                for line in lines:
                    all_code_lines.append(('exact', last_whitespace + line))
                    block_counter += 1
                    last_whitespace = '  {}. '.format(block_counter)

                last_whitespace = '. '
                continue

            # If/else/else if blocks
            # These lead following lines with .
            if any(lines[0][8:].startswith(x) for x in ['if', 'else', 'else if']):
                for line in lines:
                    all_code_lines.append(('exact', last_whitespace + line))
                    last_whitespace = '. '

            cap_reg = re.compile(r'\bcap(t|tu|tur|ture)?\b').search
            qui_reg = re.compile(r'\bqui(e|et|etl|etly)?\b').search
            noi_reg = re.compile(r'\bn(o|oi|ois|oisi|oisil|oisily)?\b').search
            # If `cap` or both `qui` and `cap` show up after my cap noi, no
            # following code lines will be printed.
            if cap_reg(lines[0][8:]) and not noi_reg(lines[0][8:]):
                all_code_lines.append(('exact', last_whitespace + lines[0]))
                last_whitespace = '. '
                continue

            if noi_reg(lines[0][8:]) or qui_reg(lines[0][8:]):
                for line in lines:
                    all_code_lines.append(('exact', last_whitespace + line))
                    last_whitespace = '. '
                continue

            # Otherwise, I don't know what it is
            for line in lines:
                all_code_lines.append(('inexact', line))
                last_whitespace = '. '

        code_line_idxs = [len(log)]
        log_line_counter = 0
        for (match_type, code_line) in all_code_lines:
            if match_type == 'exact':
                idx = log.index(code_line, log_line_counter)
            else:
                idx = [ind for ind, x in enumerate(log[log_line_counter:]) if code_line in x][0]
            log_line_counter = idx + 1
            code_line_idxs.append(idx)

        # If I just want to remove code lines
        # [x for ind, x in enumerate(log) if ind not in code_line_idxs]

        start_idxs = [ind for ind, x in enumerate(log) if
            (ind not in code_line_idxs) and
            (ind - 1 in code_line_idxs)]
        end_idxs = [ind for ind, x in enumerate(log) if
            (ind not in code_line_idxs) and
            (ind + 1 in code_line_idxs)]

        all_log_chunks = []
        for start_idx, end_idx in zip(start_idxs, end_idxs):
            all_log_chunks.append('\n'.join(log[start_idx:end_idx]))

        return '\n'.join(all_log_chunks)

    def export_graph(self):
        """
        NOTE: unclear whether I actually need to save all the graphs individually, or if I can just overwrite one. Since I'm just writing them to load them into Python, and the next graph shouldn't start writing until I'm done reading the previous one into Python, I can probably just overwrite the same file.
        """
        # Export graph to file
        cmd = 'qui graph export `"{0}/graph{1}.{2}"\' , as({2}) replace'.format(
            self.cache_dir, self.graph_counter, self.graph_format)
        self.do(cmd)

        # Read image
        with open('{}/graph{}.{}'.format(self.cache_dir, self.graph_counter,
                                         self.graph_format)) as f:
            img = f.read()

        return img
