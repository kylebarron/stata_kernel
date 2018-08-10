import argparse
import regex

magic_regex = regex.compile(
    r'\A%(?<magic>.+?)(?<code>\s+.*)?\Z',
    flags = regex.DOTALL + regex.MULTILINE
)
stata_magics = {
    'plot_magics': ['plot', 'graph'],
    'exit_magics': ['exit', 'restart'],
    'global_magics': ['locals', 'globals']
}

# ---------------------------------------------------------------------
# Plot and graph magic

plot_parser = argparse.ArgumentParser()
plot_parser.add_argument(
    'code',
    nargs    = '*',
    type     = str,
    metavar  = 'CODE',
    help     = "Code to run")
plot_parser.add_argument(
    '--scale',
    dest     = 'scale',
    type     = float,
    metavar  = 'SCALE',
    default  = 1,
    help     = "Scale default height and width",
    required = False)
plot_parser.add_argument(
    '--width',
    dest     = 'width',
    type     = int,
    metavar  = 'WIDTH',
    default  = 600,
    help     = "Plot width",
    required = False)
plot_parser.add_argument(
    '--height',
    dest     = 'height',
    type     = int,
    metavar  = 'height',
    default  = 400,
    help     = "Plot height",
    required = False)

globals_parser = argparse.ArgumentParser()
globals_parser.add_argument(
    'code',
    nargs    = '*',
    type     = str,
    metavar  = 'CODE',
    help     = "Code to run")
globals_parser.add_argument(
    '-t', '--truncate',
    dest     = 'truncate',
    action   = 'store_true',
    help     = "Truncate macro values to first line (as truncated by Stata)",
    required = False)


# ---------------------------------------------------------------------
# Hack-ish magic parser

def poor_mans_magic(code):
    magic = {'name': '', 'status': 0}

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
        code = "help " + code

    if code.strip() == '':
        magic['status'] = -1

    return magic, code
