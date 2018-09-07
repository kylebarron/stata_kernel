import os
import re
import sys
import json
import argparse
import platform

from shutil import which
from pathlib import Path
from textwrap import dedent
from IPython.utils.tempdir import TemporaryDirectory
from jupyter_client.kernelspec import KernelSpecManager

kernel_json = {
    "argv": [sys.executable, "-m", "stata_kernel", "-f", "{connection_file}"],
    "display_name": "Stata",
    "language": "stata", }


def install_my_kernel_spec(user=True, prefix=None):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755)  # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)

        print('Installing Jupyter kernel spec')
        KernelSpecManager().install_kernel_spec(
            td, 'stata', user=user, replace=True, prefix=prefix)


def install_conf():
    if platform.system() == 'Windows':
        execution_mode = 'automation'
        stata_path = win_find_path()
    else:
        execution_mode = 'console'
        for i in ['stata-mp', 'StataMP', 'stata-se', 'StataSE', 'stata',
                  'Stata']:
            stata_path = which('StataMP')
            if stata_path:
                break

        if (not stata_path) and (platform.system() == 'Darwin'):
            stata_path = mac_find_path()

    if not stata_path:
        msg = """\
            WARNING: Could not find Stata path.
            Refer to the documentation to see how to set it manually:

            https://kylebarron.github.io/stata_kernel/getting_started/#configuration

            """
        print(dedent(msg))

    conf_default = dedent(
        """\
    [stata_kernel]

    # Path to stata executable. If you type this in your terminal, it should
    # start the Stata console
    stata_path = {}

    # **macOS only**
    # The manner in which the kernel connects to Stata. Either 'console' or
    # 'automation'. 'console' is the default because it allows multiple
    # independent sessions of Stata at the same time.
    execution_mode = {}

    # Directory to hold temporary images and log files
    cache_directory = ~/.stata_kernel_cache

    # Whether autocompletion suggestions should include the closing symbol
    # (i.e. ``'`` for a local macro or `}` if the global starts with `${`)
    autocomplete_closing_symbol = False

    # Extension and format for images
    graph_format = svg

    # Scaling factor for graphs
    graph_scale = 1
    """.format(stata_path, execution_mode))

    with open(Path('~/.stata_kernel.conf').expanduser(), 'w') as f:
        f.write(conf_default)


def win_find_path():
    import winreg
    reg = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
    subkeys = [
        r'Stata15Do\shell\do\command', r'Stata14Do\shell\do\command',
        r'Stata13Do\shell\do\command', r'Stata12Do\shell\do\command']

    fpath = ''
    for subkey in subkeys:
        try:
            key = winreg.OpenKey(reg, subkey)
            fpath = winreg.QueryValue(key, None).split('"')[1]
        except FileNotFoundError:
            pass
        if fpath:
            break

    return fpath


def mac_find_path():
    """Attempt to find Stata path on macOS when not on user's PATH

    Returns:
        (str): Path to Stata. Empty string if not found.
    """
    path = Path('/Applications/Stata')
    if not path.exists():
        return ''

    dirs = [
        x for x in path.iterdir() if re.search(r'Stata(SE|MP)?\.app', x.name)]
    if not dirs:
        return ''

    if len(dirs) > 1:
        for ext in ['MP.app', 'SE.app', '.app']:
            name = [x for x in dirs if x.name.endswith(ext)]
            if name:
                dirs = name
                break

    path = dirs[0] / 'Contents' / 'MacOS'
    if not path.exists():
        return ''

    binaries = [x for x in path.iterdir()]
    for pref in ['stata-mp', 'stata-se', 'stata']:
        name = [x for x in binaries if x.name == pref]
        if name:
            binaries = name
            break

    return str(binaries[0])


def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False  # assume not an admin on non-Unix platforms


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--user', action='store_true',
        help="Install to the per-user kernels registry. Default if not root.")
    ap.add_argument(
        '--sys-prefix', action='store_true',
        help="Install to sys.prefix (e.g. a virtualenv or conda env)")
    ap.add_argument(
        '--prefix', help="Install to the given prefix. "
        "Kernelspec will be installed in {PREFIX}/share/jupyter/kernels/")
    args = ap.parse_args(argv)

    if args.sys_prefix:
        args.prefix = sys.prefix
    if not args.prefix and not _is_root():
        args.user = True

    install_my_kernel_spec(user=args.user, prefix=args.prefix)
    install_conf()


if __name__ == '__main__':
    main()
