import argparse
import regex


# ---------------------------------------------------------------------
# Magic argument parsers


class MagicParsers():
    def __init__(self):
        self.plot = argparse.ArgumentParser()
        self.plot.add_argument(
            'code',
            nargs    = '*',
            type     = str,
            metavar  = 'CODE',
            help     = "Code to run")
        self.plot.add_argument(
            '--scale',
            dest     = 'scale',
            type     = float,
            metavar  = 'SCALE',
            default  = 1,
            help     = "Scale default height and width",
            required = False)
        self.plot.add_argument(
            '--width',
            dest     = 'width',
            type     = int,
            metavar  = 'WIDTH',
            default  = 600,
            help     = "Plot width",
            required = False)
        self.plot.add_argument(
            '--height',
            dest     = 'height',
            type     = int,
            metavar  = 'height',
            default  = 400,
            help     = "Plot height",
            required = False)

        self.globals = argparse.ArgumentParser()
        self.globals.add_argument(
            'code',
            nargs    = '*',
            type     = str,
            metavar  = 'CODE',
            help     = "Code to run")
        self.globals.add_argument(
            '-t', '--truncate',
            dest     = 'truncate',
            action   = 'store_true',
            help     = "Truncate macro values to first line (as truncated by Stata)",
            required = False)


# ---------------------------------------------------------------------
# Hack-ish magic parser


class StataMagics():
    def __init__(self):
        self.quit_early = None
        self.last_magic = None
        self.magic_dict = {
            'name':   '',
            'status': 0,
            'kwargs': None
        }

        self.magics_match = regex.compile(
            r'\A%(?<magic>.+?)(?<code>\s+.*)?\Z',
            flags = regex.DOTALL + regex.MULTILINE
        )

        self.magics_available = {
            'plot': ['plot', 'graph'],
            'exit': ['exit', 'restart'],
            'globals': ['locals', 'globals']
            'time': ['time', 'timeit']
        }

    def magics(self, code, kernel)
        quit_early = {'execution_count': count}
        quit_early['status'] = 'ok'
        quit_early['payload'] = []
        quit_early['user_expressions'] = {}
        magic = self.magic_dict

        if code.strip().startswith("%"):
            match = magic_regex.match(code.strip())
            if match:
                _magic = match.groupdict()['magic']
                code   = match.groupdict()['code']
                code   = '' if not code else code.strip()

                if _magic in stata_magics['plot_magics']:
                    magic['name'] = _magic
                    try:
                        args = vars(plot_parser.parse_args(code.split(' ')))
                        code = ' '.join(args['code'])
                        args.pop('code', None)
                        args['width']   = args['scale'] * args['width']
                        args['height']  = args['scale'] * args['height']
                        args.pop('scale', None)
                        magic['kwargs'] = args
                    except:
                        magic['name']   = ''
                        magic['status'] = -1

                elif _magic in stata_magics['global_magics']:
                    magic['status'] = -1
                    magic['name']   = _magic
                    magic['locals'] = (_magic == 'locals')
                    magic['sregex'] = regex.compile(r"^ {16,16}", flags = regex.MULTILINE)
                    try:
                        args = vars(globals_parser.parse_args(code.split(' ')))
                        code = ' '.join(args['code'])
                        magic['gregex'] = regex.compile(code.strip())
                        if args['truncate']:
                            magic['regex']  = regex.compile(
                                r"^(?<macro>_?[\w\d]*?):(?<cr>[\r\n]{0,2} {1,16})(?<contents>.*?$)",
                                flags = regex.DOTALL + regex.MULTILINE
                            )
                        else:
                            magic['regex']  = regex.compile(
                                r"^(?<macro>_?[\w\d]*?):(?<cr>[\r\n]{0,2} {1,16})(?<contents>.*?$(?:[\r\n]{0,2} {16,16}.*?$)*)",
                                flags = regex.DOTALL + regex.MULTILINE
                            )
                    except:
                        magic['name']   = ''

                # elif _magic in stata_magics['exit_magics']:
                #     magic['name']    = _magic
                #     magic['restart'] = (_magic == 'restart')
                #     if code.strip() != '':
                #         magic['name']   = ''
                #         magic['status'] = -1
                #         print("Magic %{0} must be called by itself.".format(_magic))

                else:
                    print("Uknown magic %{0}.".format(_magic))

        elif code.strip().startswith("?"):
            code = "help " + code.strip()

        if code.strip() == '':
            magic['status'] = -1

        if (magic['status'] == -1) and :
            self.quit_early = quit_early
        else:
            self.quit_early = None

        return code

    def magic_plot(self):
        pass

    def magic_globals(self):
        pass

    def magic_locals(self):
        pass

    def magic_time(self):
        pass

    def magic_timeit(self):
        pass
