import argparse
import json
import os
import sys
import platform

from jupyter_client.kernelspec import KernelSpecManager
from IPython.utils.tempdir import TemporaryDirectory

kernel_json = {
    "argv": [sys.executable, "-m", "stata_kernel", "-f", "{connection_file}"],
    "display_name": "Stata",
    "language": "stata",
}

if platform.system() == 'Windows':
    execution_mode = 'automation'
else:
    execution_mode = 'console'

conf_default = """\
[stata_kernel]

# Path to stata executable. If you type this in your terminal, it should start
# the Stata console
stata_path = stata

# The manner in which the kernel connects to Stata. The default is 'console',
# which monitors the Stata console. In the future another mode, 'automation',
# may be added to connect with the Stata GUI on Windows and macOS computers
execution_mode = {}
""".format(execution_mode)

def install_my_kernel_spec(user=True, prefix=None):
    with TemporaryDirectory() as td:
        os.chmod(td, 0o755) # Starts off as 700, not user readable
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)
        # TODO: Copy any resources

        print('Installing Jupyter kernel spec')
        KernelSpecManager().install_kernel_spec(td, 'stata', user=user, replace=True, prefix=prefix)

def install_conf():
    with open(os.path.expanduser('~/.stata_kernel.conf'), 'w') as f:
        f.write(conf_default)

def _is_root():
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False # assume not an admin on non-Unix platforms

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', action='store_true',
        help="Install to the per-user kernels registry. Default if not root.")
    ap.add_argument('--sys-prefix', action='store_true',
        help="Install to sys.prefix (e.g. a virtualenv or conda env)")
    ap.add_argument('--prefix',
        help="Install to the given prefix. "
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
