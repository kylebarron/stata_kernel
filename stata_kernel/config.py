import os
import re
import platform

from pathlib import Path
from textwrap import dedent
from tempfile import TemporaryDirectory
from configparser import ConfigParser, NoSectionError

from .utils import find_path

GLOBAL_PATH = '/etc/stata_kernel.conf'
USER_PATH = '~/.stata_kernel.conf'

GLOBAL_PATH_ENVVAR_NAME = 'STATA_KERNEL_GLOBAL_CONFIG_PATH'
USER_PATH_ENVVAR_NAME = 'STATA_KERNEL_USER_CONFIG_PATH'


class Config():
    all_settings = [
        'autocomplete_closing_symbol',
        'cache_directory',
        'execution_mode',
        'graph_format',
        'graph_height',
        'graph_png_redundancy',
        'graph_redundancy_warning',
        'graph_scale',
        'graph_svg_redundancy',
        'graph_width',
        'stata_path',
        'user_graph_keywords', ]  # yapf: ignore

    def __init__(self):
        """
        Load config both from a potential system-wide config file or from a
        user-defined one if present.

        We first load from the system-wide location if the file is present and
        then we load the user-defined location, updating entries. Thus the
        user-location takes precedence, but either file can be missing.

        The user-defined path defaults to `~/.stata_kernel.conf` or can be read
        from the environmental variable `STATA_KERNEL_USER_CONFIG_PATH`.

        The system-wide config file was added to facilitate deployments on
        systems like Jupyter Hub; it defaults to `/etc/stata_kernel.conf` or
        read from the environmental variable `STATA_KERNEL_GLOBAL_CONFIG_PATH`,
        and we do not otherwise keep a reference to it because it is likely
        non-writable. Setting any config option should go to the user-config.

        Example config file::

            [stata_kernel]
            stata_path = "C:/Program Files/Stata16/StataMP-64.exe"
            execution_mode = automation
            cache_directory = ~/.stata_kernel_cache
            autocomplete_closing_symbol = False
            graph_format = svg
            graph_scale = 1
            user_graph_keywords = coefplot,vioplot
        """
        _global_path = os.environ.get(GLOBAL_PATH_ENVVAR_NAME, GLOBAL_PATH)
        _user_path = os.environ.get(USER_PATH_ENVVAR_NAME, USER_PATH)

        global_config = ConfigParser()
        global_config.read(_global_path)

        self.config_path = Path(_user_path).expanduser()
        self.config = ConfigParser()
        self.config.read(str(self.config_path))

        self.env = {}

        for c in (global_config, self.config):
            try:
                self.env.update(dict(c.items('stata_kernel')))
            except NoSectionError:
                pass

        cache_par_dir = Path(self.get('cache_directory',
                                      '~/.stata_kernel_cache')).expanduser()
        cache_par_dir.mkdir(parents=True, exist_ok=True)
        self._cache_temp_dir = TemporaryDirectory(dir=str(cache_par_dir))
        cache_dir = Path(self._cache_temp_dir.name)

        stata_path = self.get('stata_path', find_path())
        if not stata_path:
            self.raise_config_error('stata_path')

        if platform.system() == 'Darwin':
            stata_path = self.get_mac_stata_path_variant(stata_path)
            execution_mode = self.get('execution_mode', 'console')
            if execution_mode not in ['console', 'automation']:
                self.raise_config_error('execution_mode')
        elif platform.system() == 'Windows':
            execution_mode = 'automation'
        else:
            execution_mode = 'console'
            stata_path = self.get_linux_stata_path_variant(stata_path)

        self.set('cache_dir', cache_dir)
        self.set('stata_path', stata_path)
        self.set('execution_mode', execution_mode)
        if not self.get('stata_path'):
            self.raise_config_error('stata_path')

    def get(self, key, backup=None):
        return self.env.get(key, backup)

    def set(self, key, val, permanent=False):
        if key.startswith('cache_dir'):
            val = Path(val).expanduser()
            val.mkdir(parents=True, exist_ok=True)

        self.env[key] = val

        if permanent:
            if key.startswith('cache_dir'):
                key = 'cache_directory'
                val = str(val)

            if key.startswith('graph_'):
                val = str(val)

            try:
                self.config['stata_kernel']
            except KeyError:
                self.config['stata_kernel'] = {}

            self.config.set('stata_kernel', key, val)
            with self.config_path.open('w') as f:
                self.config.write(f)

    def get_mac_stata_path_variant(self, stata_path):
        path = Path(stata_path)
        if self.get('execution_mode') == 'automation':
            d = {'stata': 'Stata', 'stata-se': 'StataSE', 'stata-mp': 'StataMP'}
        else:
            d = {'Stata': 'stata', 'StataSE': 'stata-se', 'StataMP': 'stata-mp'}

        bin_name = d.get(path.name, path.name)
        return str(path.parent / bin_name)

    def get_linux_stata_path_variant(self, stata_path):
        d = {
            'xstata': 'stata',
            'xstata-se': 'stata-se',
            'xstata-mp': 'stata-mp'}
        for xname, name in d.items():
            if stata_path.endswith(xname):
                stata_path = re.sub(r'{}$'.format(xname), name, stata_path)
                break

        return stata_path

    def raise_config_error(self, option):
        msg = """\
        {} option in configuration file is missing or invalid
        Refer to the documentation to see how to set it manually:

        https://kylebarron.dev/stata_kernel/using_stata_kernel/configuration/
        """.format(option)
        raise ValueError(dedent(msg))

    def _remove_unsafe(self, key, permanent=False):
        self.env.pop(key, None)
        if permanent:
            self.config.remove_option(option=key, section='stata_kernel')
            with self.config_path.open('w') as f:
                self.config.write(f)


config = Config()
