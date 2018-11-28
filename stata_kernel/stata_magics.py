import sys
import re
import urllib
import pandas as pd
from textwrap import dedent
from argparse import ArgumentParser, SUPPRESS

from bs4 import BeautifulSoup as bs
from .code_manager import CodeManager
from pkg_resources import resource_filename


class StataParser(ArgumentParser):
    def __init__(self, *args, kernel=None, **kwargs):
        super(StataParser, self).__init__(*args, **kwargs)
        self.kernel = kernel

    def print_help(self, **kwargs):
        print_kernel(self.format_help(), self.kernel)
        sys.exit(1)

    def error(self, msg):
        print_kernel('error: %s\n' % msg, self.kernel)
        print_kernel(self.format_usage(), self.kernel)
        sys.exit(2)


class MagicParsers():
    def __init__(self, kernel):
        self.globals = StataParser(prog='%globals', kernel=kernel)
        self.globals.add_argument(
            'code', nargs='*', type=str, metavar='REGEX', help="regex to match")
        self.globals.add_argument(
            '-v', '--verbose', dest='verbose', action='store_true',
            help="Verbose output (print full contents of matched globals).",
            required=False)

        self.locals = StataParser(prog='%locals', kernel=kernel)
        self.locals.add_argument(
            'code', nargs='*', type=str, metavar='REGEX', help="regex to match")
        self.locals.add_argument(
            '-v', '--verbose', dest='verbose', action='store_true',
            help="Verbose output (print full contents of matched locals).",
            required=False)

        self.browse = StataParser(prog='%browse', kernel=kernel)
        self.browse = StataParser(
            prog='%browse', kernel=kernel,
            usage='%(prog)s [-h] [N] [varlist] [if]',
            description="Display the first N rows of the dataset in memory.")
        self.browse.add_argument('code', nargs='*', type=str, help=SUPPRESS)

        self.time = StataParser(prog='%time', kernel=kernel)
        self.time.add_argument(
            'code', nargs='*', type=str, metavar='CODE', help="Code to run")
        self.time.add_argument(
            '--profile', dest='profile', action='store_true',
            help="Profile each line of code", required=False)

        self.timeit = StataParser(prog='%timeit', kernel=kernel)
        self.timeit.add_argument(
            'code', nargs='*', type=str, metavar='CODE', help="Code to run")
        self.timeit.add_argument(
            '-r', dest='r', type=int, metavar='R', default=3,
            help="Choose best time of R loops.", required=False)
        self.timeit.add_argument(
            '-n', dest='n', type=int, metavar='N', default=None,
            help="Execute statement N times per loop.", required=False)

        self.help = StataParser(
            prog='%help', kernel=kernel, description="Display HTML help.",
            usage='%(prog)s [-h] command_or_topic_name')
        self.help.add_argument(
            'command_or_topic_name', nargs='*', type=str, help=SUPPRESS)

        info = (
            kernel.implementation, kernel.implementation_version,
            kernel.language.title(), kernel.language_version)
        self.help._msg_html = dedent(
            """
        <p style="font-family:Monospace;">
        {0} {1} for {2} {3}. Type<br><br>

            <span style='margin-left:1em;font-weight:bold;'>
            %help kernel</span><br><br>

        for help on using the kernel and<br><br>

            <span style='margin-left:1em;font-weight:bold;'>
            %help magics</span><br><br>

        for info on magics. To see the help menu for a Stata command type<br><br>

            <span style='margin-left:1em;font-weight:bold;'>
            %help command_or_topic</span>
        </p>
        """.format(*info))
        self.help._msg_plain = dedent(
            """\
        {0} {1} for {2} {3}.

        Note: This front end cannot display rich HTML help. See the online
        documentation at

                https://kylebarron.github.io/stata_kernel/

        For kernel help in plain text, type

            %help kernel

        for help on using the kernel and

            %help magics

        for info on magics.
        """.format(*info))

        self.head = StataParser(
            prog='%head', kernel=kernel,
            usage='%(prog)s [-h] [N] [varlist] [if]',
            description="Display the first N rows of the dataset in memory.")
        self.head.add_argument('code', nargs='*', type=str, help=SUPPRESS)

        self.tail = StataParser(
            prog='%tail', kernel=kernel,
            usage='%(prog)s [-h] [N] [varlist] [if]',
            description="Display the last N rows of the dataset in memory.")
        self.tail.add_argument('code', nargs='*', type=str, help=SUPPRESS)

        #######################################################################
        #                                                                     #
        #                             %set magic                              #
        #                                                                     #
        #######################################################################

        self.set = StataParser(
            prog='%set', kernel=kernel, description='Set configuration value.')
        self.set.add_argument('key', type=str, help='Configuration key name.')
        self.set.add_argument('value', type=str, help='Value to set.')
        self.set.add_argument(
            '--permanently', dest='perm', action='store_true',
            help="Store settings permanently", required=False)
        self.set.add_argument(
            '--reset', dest='reset', action='store_true',
            help="Restore default settings.", required=False)

        self.show_gui = StataParser(
            prog='%show_gui', kernel=kernel,
            description="Show Stata GUI. Only works on Windows (and Mac if using automation execution mode)")
        self.show_gui.add_argument('code', nargs='*', type=str, help=SUPPRESS)

        self.hide_gui = StataParser(
            prog='%hide_gui', kernel=kernel,
            description="Hide Stata GUI. Only works on Windows (and Mac if using automation execution mode)")
        self.hide_gui.add_argument('code', nargs='*', type=str, help=SUPPRESS)


class StataMagics():
    html_base = "https://www.stata.com"
    html_help = urllib.parse.urljoin(html_base, "help.cgi?{}")

    magic_regex = re.compile(
        r'\A%(?P<magic>.+?)(?P<code>\s+.*)?\Z', flags=re.DOTALL + re.MULTILINE)

    available_magics = [
        'browse',
        'delimit',
        # 'exit',
        'globals',
        'head',
        'help',
        'hide_gui',
        'locals',
        # 'restart',
        'set',
        'show_gui',
        'status',
        'tail']
        # 'time',
        # 'timeit'

    csshelp_default = resource_filename(
        'stata_kernel', 'css/_StataKernelHelpDefault.css')
    help_kernel_html = resource_filename('stata_kernel', 'docs/index.html')
    help_kernel_plain = resource_filename('stata_kernel', 'docs/index.txt')
    help_magics_html = resource_filename(
        'stata_kernel', 'docs/using_stata_kernel/magics.html')
    help_magics_plain = resource_filename(
        'stata_kernel', 'docs/using_stata_kernel/magics.txt')

    def __init__(self, kernel):
        self.quit_early = None
        self.status = 0
        self.any = False
        self.name = ''
        self.graphs = 1
        self.timeit = 0
        self.time_profile = None
        self.img_set = False
        self.parse = MagicParsers(kernel)

    def magic(self, code, kernel):
        self.__init__(kernel)

        if code.strip().startswith("%"):
            match = self.magic_regex.match(code.strip())
            if match:
                name, code = match.groupdict().values()
                code = '' if code is None else code.strip()
                if name in self.available_magics:
                    code = getattr(self, "magic_" + name)(code, kernel)
                    self.name = name
                    self.any = True
                    if code.strip() == '':
                        self.status = -1
                else:
                    print_kernel("Unknown magic %{0}.".format(name), kernel)
                    self.status = -1

                if (self.status == -1):
                    self.quit_early = {
                        'execution_count': kernel.execution_count,
                        'status': 'ok',
                        'payload': [],
                        'user_expressions': {}}

        elif code.strip().startswith("?"):
            code = "help " + code.strip()

        return code

    def post(self, kernel):
        if self.timeit in [1, 2]:
            total, _ = self.time_profile.pop()
            print_kernel("Wall time (seconds): {0:.2f}".format(total), kernel)

            if (len(self.time_profile) > 0) and (self.timeit == 2):
                lens = 0
                tprint = []
                for t, l in self.time_profile:
                    tfmt = "{0:.2f}".format(t)
                    tprint += [(tfmt, l)]
                    lens = max(lens, len(tfmt))

                fmt = "\t{{0:{0}}} {{1}}".format(lens)
                for t, l in tprint:
                    print_kernel(fmt.format(t, l), kernel)

    def magic_browse(self, code, kernel):
        self.status = -1
        try:
            self.parse.browse.parse_args(code.split(' '))
        except:
            return ''
        res = self.show_data_head(code, kernel, N=200)
        if res:
            try:
                self.parse.browse.error(res)
            except:
                pass
        return ''

    def magic_head(self, code, kernel, N=None):
        self.status = -1
        try:
            self.parse.head.parse_args(code.split(' '))
        except:
            return ''
        res = self.show_data_head(code, kernel, N=10)
        if res:
            try:
                self.parse.head.error(res)
            except:
                pass
        return ''

    def show_data_head(self, code, kernel, N=10):
        hasif = re.search(r"\bif\b", code) is not None
        using = kernel.conf.get('cache_dir') / 'data_head.csv'
        cmd = '_StataKernelHead ' + code.strip() + ' using ' + str(using)
        cmd += ' , n_default({})'.format(N)
        cm = CodeManager(cmd)
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        if rc:
            return res
        else:
            if hasif:
                df = pd.read_csv(using, index_col=0, dtype=str)
                df.index.name = None
            else:
                df = pd.read_csv(using, dtype=str)
                df.index += 1

            html = df.to_html(na_rep='.', notebook=True)
            content = {
                'data': {
                    'text/plain': res,
                    'text/html': html},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', content)

        return ''

    def magic_tail(self, code, kernel):
        self.status = -1
        try:
            self.parse.tail.parse_args(code.split(' '))
        except:
            return ''

        hasif = re.search(r"\bif\b", code) is not None
        using = kernel.conf.get('cache_dir') / 'data_tail.csv'
        cmd = '_StataKernelTail ' + code.strip() + ' using ' + str(using)
        cm = CodeManager(cmd)
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        if rc:
            try:
                self.parse.tail.error(res)
            except:
                return ''
        else:
            if hasif:
                df = pd.read_csv(using, index_col=0, dtype=str)
                df.index.name = None
            else:
                res = res.rstrip()
                lastn = res.rfind('\n')
                nobs = int(res[lastn:].strip())
                res = res[:lastn]
                df = pd.read_csv(using, dtype=str)
                nread = df.shape[0]
                df.index = list(range(nobs - nread + 1, nobs + 1))

            html = df.to_html(na_rep='.', notebook=True)
            content = {
                'data': {
                    'text/plain': res,
                    'text/html': html},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', content)

        return ''

    def magic_globals(self, code, kernel, local=False):
        gregex = {}
        gregex['blank'] = re.compile(r"^ {16,16}", flags=re.MULTILINE)
        try:
            if local:
                args = vars(self.parse.locals.parse_args(code.split(' ')))
            else:
                args = vars(self.parse.globals.parse_args(code.split(' ')))

            code = ' '.join(args['code'])
            gregex['match'] = re.compile(code.strip())
            if args['verbose']:
                gregex['main'] = re.compile(
                    r"^(?P<macro>_?[\w\d]*?):"
                    r"(?P<cr>[\r\n]{0,2} {1,16})"
                    r"(?P<contents>.*?$(?:[\r\n]{0,2} {16,16}.*?$)*)",
                    flags=re.DOTALL + re.MULTILINE)
            else:
                gregex['main'] = re.compile(
                    r"^(?P<macro>_?[\w\d]*?):"
                    r"(?P<cr>[\r\n]{0,2} {1,16})"
                    r"(?P<contents>.*?$)", flags=re.DOTALL + re.MULTILINE)
        except:
            self.status = -1

        if self.status == -1:
            return code

        cm = CodeManager(kernel.stata._mata_escape("macro dir"))
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        if rc:
            self.status = -1
            return code

        stata_globals = gregex['main'].findall(res)
        lens = 0
        note = False
        find_name = gregex['match'] != ''
        print_globals = []
        if len(stata_globals) > 0:
            for macro, cr, contents in stata_globals:
                if local and not macro.startswith('_'):
                    continue
                elif not local and macro.startswith('_'):
                    continue

                if macro.startswith('_'):
                    macro = macro[1:]
                    extra = 1
                else:
                    extra = 0

                if find_name:
                    if not gregex['match'].search(macro):
                        continue

                macro += ':'
                lmacro = len(macro)
                lspaces = len(cr.strip('\r\n'))
                lens = max(lens, lmacro)
                if len(macro) <= 15:
                    if (lspaces + lmacro + extra) > 16:
                        print_globals += [(macro, ' ' + contents)]
                    else:
                        print_globals += [(macro, contents)]
                else:
                    print_globals += [(macro, contents.lstrip('\r\n'))]

                if len(contents) > 24:
                    note = True

        if len(print_globals) > 0:
            if not args['verbose'] and note:
                if local:
                    wmacro = 'local'
                else:
                    wmacro = 'global'

                msg = "(note: showing first line of " + wmacro
                msg += " values; run with --verbose)\n"
                print_kernel(msg, kernel)

        fmt = "{{0:{0}}} {{1}}".format(lens)
        for macro, contents in print_globals:
            print_kernel(
                fmt.format(
                    macro, gregex['blank'].sub((lens + 1) * ' ', contents)),
                kernel)

        self.status = -1
        return ''

    def magic_locals(self, code, kernel):
        return self.magic_globals(code, kernel, True)

    def magic_delimit(self, code, kernel):
        delim = ';' if kernel.sc_delimit_mode else 'cr'
        print_kernel('The delimiter is currently: {}'.format(delim), kernel)
        return ''

    def magic_set(self, code, kernel):
        try:
            settings = code.strip().split(' ')
            args = vars(self.parse.set.parse_args(settings))
            key = args['key']
            value = args['value']
            perm = args['perm']
            reset = args['reset']

            if reset:
                if value is not None:
                    msg = 'Cannot set values with --reset.'
                    self.parse.set.error(msg)

                # reset graph settings
                kernel.conf.set('graph_format', 'svg', permanent=perm)
                kernel.conf.set('graph_scale', '1', permanent=perm)
                kernel.conf._remove_unsafe('graph_width', permanent=perm)
                kernel.conf._remove_unsafe('graph_height', permanent=perm)
            else:
                kernel.conf.set(key, value, permanent=perm)

        except:
            pass

        self.status = -1
        return ''

    def magic_time(self, code, kernel):
        try:
            args = vars(self.parse.time.parse_args(code.split(' ')))
            _code = ' '.join(args['code'])
            if args['profile']:
                self.timeit = 2
            else:
                self.timeit = 1

            self.graphs = 0
            return _code
        except:
            self.status = -1
            return code

    def magic_timeit(self, code, kernel):
        self.status = -1
        self.graphs = 0
        print_kernel("Magic timeit has not been implemented.", kernel)
        return code

    def magic_help(self, code, kernel):
        self.status = -1
        self.graphs = 0
        scode = code.strip()
        try:
            self.parse.help.parse_args(scode.split(' '))
        except:
            return ''

        if not scode:
            resp = {
                'data': {
                    'text/html': self.parse.help._msg_html,
                    'text/plain': self.parse.help._msg_plain},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', resp)
            return ''

        if scode == 'kernel':
            with open(self.help_kernel_html, 'r') as f:
                help_html = f.read()

            with open(self.help_kernel_plain, 'r') as f:
                help_plain = f.read()

            resp = {
                'data': {
                    'text/html': help_html,
                    'text/plain': help_plain},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', resp)
            return ''
        elif scode == 'magics':
            with open(self.help_magics_html, 'r') as f:
                help_html = f.read()

            with open(self.help_magics_plain, 'r') as f:
                help_plain = f.read()

            resp = {
                'data': {
                    'text/html': help_html,
                    'text/plain': help_plain},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', resp)
            return ''

        cmd = scode.replace(" ", "_")
        try:
            reply = urllib.request.urlopen(self.html_help.format(cmd))
            html = reply.read().decode("utf-8")
            soup = bs(html, 'html.parser')

            # Set root for links to https://ww.stata.com
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                relative = href.find(cmd + '#')
                if relative >= 0:
                    hrelative = href.find('#')
                    a['href'] = href[hrelative:]
                elif not href.startswith('http'):
                    a['href'] = urllib.parse.urljoin(self.html_base, href)
                    a['target'] = '_blank'

            # Remove header 'Stata 15 help for ...'
            soup.find('h2').decompose()

            # Remove Stata help menu
            soup.find('div', id='menu').decompose()

            # Remove Copyright notice
            soup.find('a', text='Copyright').find_parent("table").decompose()

            # Remove last hrule
            soup.find_all('hr')[-1].decompose()

            # Set all the backgrounds to transparent
            for color in ['#ffffff', '#FFFFFF']:
                for bg in ['bgcolor', 'background', 'background-color']:
                    for tag in soup.find_all(attrs={bg: color}):
                        if tag.get(bg):
                            tag[bg] = 'transparent'

            # Set html
            css = soup.find('style', {'type': 'text/css'})
            with open(self.csshelp_default, 'r') as default:
                css.string = default.read()

            fallback = 'This front-end cannot display HTML help.'
            resp = {
                'data': {
                    'text/html': str(soup),
                    'text/plain': fallback},
                'metadata': {}}
            kernel.send_response(kernel.iopub_socket, 'display_data', resp)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            msg = "Failed to fetch HTML help.\r\n{0}"
            print_kernel(msg.format(e), kernel)

        return ''

    def magic_exit(self, code, kernel):
        self.status = -1
        self.graphs = 0
        print_kernel("Magic exit has not been implemented.", kernel)
        return code

    def magic_restart(self, code, kernel):
        # magic['name']    = 'restart'
        # magic['restart'] = True
        # if code.strip() != '':
        #     magic['name']   = ''
        #     magic['status'] = -1
        #     print("Magic restart must be called by itself.")
        self.status = -1
        print_kernel("Magic restart has not been implemented.", kernel)
        return code

    def magic_status(self, code, kernel):
        self.status = -1
        delim = ';' if kernel.sc_delimit_mode else 'cr'
        env = 'mata' if kernel.stata.mata_mode else 'stata'
        info = (
            kernel.implementation, kernel.implementation_version,
            kernel.language, kernel.language_version)
        print_kernel('{0} {1} for {2} {3}'.format(*info), kernel)
        print_kernel('\tDelimiter:   {}'.format(delim), kernel)
        print_kernel('\tEnvironment: {}'.format(env), kernel)
        return ''

    def magic_show_gui(self, code, kernel):
        try:
            self.parse.show_gui.parse_args(code.split(' '))
        except:
            return ''
        kernel.stata.show_gui()
        return ''

    def magic_hide_gui(self, code, kernel):
        try:
            self.parse.hide_gui.parse_args(code.split(' '))
        except:
            return ''
        kernel.stata.hide_gui()
        return ''


def print_kernel(msg, kernel):
    msg = re.sub(r'$', r'\r\n', msg, flags=re.MULTILINE)
    msg = re.sub(r'[\r\n]{1,2}[\r\n]{1,2}', r'\r\n', msg, flags=re.MULTILINE)
    stream_content = {'text': msg, 'name': 'stdout'}
    kernel.send_response(kernel.iopub_socket, 'stream', stream_content)
