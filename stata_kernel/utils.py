import os
import re
import requests
import platform

from shutil import which
from pathlib import Path
from textwrap import dedent
from packaging import version


def check_stata_kernel_updated_version(stata_kernel_version):
    try:
        r = requests.get('https://pypi.org/pypi/stata-kernel/json')
        pypi_v = r.json()['info']['version']
        if version.parse(pypi_v) > version.parse(stata_kernel_version):
            msg = """\
                NOTE: A newer version of stata_kernel exists. Run

                \tpip install stata_kernel --upgrade

                to install the latest version.
                """
            return dedent(msg)
    except requests.exceptions.RequestException:
        return


def find_path():
    if os.getenv('CONTINUOUS_INTEGRATION'):
        print('WARNING: Running as CI; Stata path not set correctly')
        return 'stata'
    if platform.system() == 'Windows':
        return win_find_path()
    elif platform.system() == 'Darwin':
        return mac_find_path()
    else:
        for i in ['stata-mp', 'stata-se', 'stata']:
            stata_path = which(i)
            if stata_path:
                break

        return stata_path


def win_find_path():
    import winreg
    reg = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
    subkeys = [
        r'Stata16Do\shell\do\command', r'Stata15Do\shell\do\command',
        r'Stata14Do\shell\do\command', r'Stata13Do\shell\do\command',
        r'Stata12Do\shell\do\command']

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
        for ext in ['MP.app', 'SE.app', 'IC.app', '.app']:
            name = [x for x in dirs if x.name.endswith(ext)]
            if name:
                dirs = name
                break

    path = dirs[0] / 'Contents' / 'MacOS'
    if not path.exists():
        return ''

    binaries = [x for x in path.iterdir()]
    for pref in ['stata-mp', 'stata-se', 'stata', 'StataIC']:
        name = [x for x in binaries if x.name == pref]
        if name:
            binaries = name
            break

    return str(binaries[0])
