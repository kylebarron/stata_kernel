import sys
import re
import pandas as pd
from argparse import ArgumentParser
from .code_manager import CodeManager


# NOTE(mauricio): Figure  out if passing the kernel around is a problem...
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
            'code', nargs='*', type=str, metavar='CODE', help="Code to run")
        self.globals.add_argument(
            '-t', '--truncate', dest='truncate', action='store_true',
            help="Truncate macro values to first line printed by Stata",
            required=False)

        self.locals = StataParser(prog='%locals', kernel=kernel)
        self.locals.add_argument(
            'code', nargs='*', type=str, metavar='CODE', help="Code to run")
        self.locals.add_argument(
            '-t', '--truncate', dest='truncate', action='store_true',
            help="Truncate macro values to first line printed by Stata",
            required=False)

        self.browse = StataParser(prog='%browse', kernel=kernel)
        self.browse.add_argument(
            'varlist', nargs='*', type=str, metavar='VARLIST', help='Varlist to browse')
        self.browse.add_argument(
            '--if', dest='if', type=str,
            help="if clause passed to browse", required=False)
        self.browse.add_argument(
            '--in', dest='in', type=str,
            help="if clause passed to browse", required=False)

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


class StataMagics():
    img_metadata = {'width': 600, 'height': 400}

    magic_regex = re.compile(
        r'\A%(?P<magic>.+?)(?P<code>\s+.*)?\Z', flags=re.DOTALL + re.MULTILINE)

    available_magics = [
        'browse',
        # 'exit',
        # 'restart',
        'locals',
        'globals',
        'delimit',
        'time',
        'timeit']

    def __init__(self):
        self.quit_early = None
        self.status = 0
        self.any = False
        self.name = ''
        self.graphs = 1
        self.timeit = 0
        self.time_profile = None
        self.img_set = False

    def magic(self, code, kernel):
        self.__init__()
        self.parse = MagicParsers(kernel)

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
        args = vars(self.parse.browse.parse_args(code.split(' ')))
        if not args['in']:
            args['in'] = '1/200'

        cmd = """\
        _StataKernelExportDelim {} {} {} using `"{}/data.csv"', replace datafmt
        """.format(args['varlist'], args['if'], args['in'], kernel.conf.get('cache_dir'))
        cm = CodeManager(cmd)
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        df = pd.read_csv(kernel.conf.get('cache_dir') / 'data.csv')
        html = df.to_html(na_rep = '.', notebook=True)
        content = {'data': {'text/html': html}, 'metadata': {},}
        kernel.send_response(kernel.iopub_socket, 'display_data', content)
        self.status = -1
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
            if args['truncate']:
                gregex['main'] = re.compile(
                    r"^(?P<macro>_?[\w\d]*?):"
                    r"(?P<cr>[\r\n]{0,2} {1,16})"
                    r"(?P<contents>.*?$)", flags=re.DOTALL + re.MULTILINE)
            else:
                gregex['main'] = re.compile(
                    r"^(?P<macro>_?[\w\d]*?):"
                    r"(?P<cr>[\r\n]{0,2} {1,16})"
                    r"(?P<contents>.*?$(?:[\r\n]{0,2} {16,16}.*?$)*)",
                    flags=re.DOTALL + re.MULTILINE)
        except:
            self.status = -1

        if self.status == -1:
            return code

        cm = CodeManager("macro dir")
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        if rc:
            self.status = -1
            return code

        stata_globals = gregex['main'].findall(res)
        lens = 0
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

def print_kernel(msg, kernel):
    msg = re.sub(r'$', r'\r\n', msg, flags=re.MULTILINE)
    msg = re.sub(r'[\r\n]{1,2}[\r\n]{1,2}', r'\r\n', msg, flags=re.MULTILINE)
    stream_content = {'text': msg, 'name': 'stdout'}
    kernel.send_response(kernel.iopub_socket, 'stream', stream_content)
