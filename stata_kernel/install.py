import os
import sys
import json
import argparse
import platform

from shutil import copyfile
from pathlib import Path
from textwrap import dedent
from importlib.resources import files
from IPython.utils.tempdir import TemporaryDirectory
from jupyter_client.kernelspec import KernelSpecManager


kernel_json = {
    "argv": [sys.executable, "-m", "stata_kernel", "-f", "{connection_file}"],
    "display_name": "Stata",
    "language": "stata", }

if sys.version_info[0] < 3:
    raise ImportError('Python < 3 is unsupported.')

if sys.version_info[1] < 5:
    raise ImportError('Python < 3.5 is unsupported.')


def install_my_kernel_spec(user=True, prefix=None):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755)  # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)

        # Copy logo to tempdir to be installed with kernelspec
        logo_path = files('stata_kernel').joinpath('docs/logo-64x64.png')
        copyfile(logo_path, os.path.join(td, 'logo-64x64.png'))

        print('Installing Jupyter kernel spec')
        KernelSpecManager().install_kernel_spec(
            td, 'stata', user=user, prefix=prefix)


def install_conf(conf_file):
    if platform.system() == 'Windows':
        execution_mode = 'automation'
    else:
        execution_mode = 'console'

    # By avoiding an import of .utils until we need it, we can
    # complete the installation process in virtual environments
    # without needing this submodule nor its downstream imports.
    from .utils import find_path
    stata_path = find_path()
    if not stata_path:
        msg = """\
            WARNING: Could not find Stata path.
            Refer to the documentation to see how to set it manually:

            https://kylebarron.dev/stata_kernel/using_stata_kernel/configuration

            """
        print(dedent(msg))
    elif 'IC.app' in stata_path:
        execution_mode = 'automation'

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
    # (i.e. ``'`` for a local macro or `}}` if the global starts with `${{`)
    autocomplete_closing_symbol = False

    # Extension and format for images
    graph_format = svg

    # Scaling factor for graphs
    graph_scale = 1

    # List of user-created keywords that produce graphs.
    # Should be comma-delimited.
    user_graph_keywords = coefplot,vioplot
    """.format(stata_path, execution_mode))

    with conf_file.open('w') as f:
        f.write(conf_default)


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
    ap.add_argument(
        '--no-conf-file', action='store_true',
        help="Skip the creation of a default user configuration file.")
    args = ap.parse_args(argv)

    if args.sys_prefix:
        args.prefix = sys.prefix
    if not args.prefix and not _is_root():
        args.user = True

    install_my_kernel_spec(user=args.user, prefix=args.prefix)
    if not args.no_conf_file:
        conf_file = Path('~/.stata_kernel.conf').expanduser()
        if not conf_file.is_file():
            install_conf(conf_file)


if __name__ == '__main__':
    main()
