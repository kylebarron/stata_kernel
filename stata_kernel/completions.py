import re
# from time import time


# TODO: Add scalars and matrices?
# TODO: Speed up completions refresh
class CompletionsManager(object):
    def __init__(self, kernel):
        self.varlist = re.compile(
            r"(?:\s+)(\S*)", flags=re.MULTILINE)

        self.varclean = re.compile(
            r"[\s\S?]^>\s", flags=re.MULTILINE).sub

        self.globals = re.compile(
            r"^(?P<macro>_?[\w\d]*?):"
            r"(?P<cr>[\r\n]{0,2} {1,16})"
            r"(?P<contents>.*?$)", flags=re.DOTALL + re.MULTILINE)

        self.suggestions = {}
        self.suggestions.update(self.get_globals_locals(kernel))
        self.suggestions.update(self.get_varlist(kernel))

    def refresh(self, kernel):
        # debugz = time()
        self.suggestions = {}
        self.suggestions.update(self.get_globals_locals(kernel))
        # print("\tdebug\trefresh globals", time() - debugz)
        # debugz = time()
        self.suggestions.update(self.get_varlist(kernel))
        # print("\tdebug\trefresh vars", time() - debugz)

    def get(self, starts, env):
        if env == 0:
            return [
                var for var in self.suggestions['varlist']
                if var.startswith(starts)]
        elif env == 1:
            return [
                var + "'" for var in self.suggestions['locals']
                if var.startswith(starts)]
        elif env == 2:
            return [
                var for var in self.suggestions['globals']
                if var.startswith(starts)]
        elif env == 3:
            return [
                var + "}" for var in self.suggestions['globals']
                if var.startswith(starts)]

    def get_varlist(self, kernel):
        res = self.quickdo('_StataKernel_ds', kernel)
        return {'varlist': self.varlist.findall(self.varclean('', res))}

    def get_globals_locals(self, kernel):
        macros = {'globals': [], 'locals': []}
        res = self.quickdo('macro dir', kernel)
        stata_globals = self.globals.findall(res)
        if len(stata_globals) > 0:
            for macro, cr, contents in stata_globals:
                if macro.startswith('_'):
                    macro = macro[1:]
                    macros['locals'] += [macro]
                else:
                    macros['globals'] += [macro]

        return macros

    def quickdo(self, code, kernel):
        if kernel.stata.execution_mode == 'console':
            res, timer = kernel.stata.do_console(code)
        else:
            log_path = kernel.stata.cache_dir / '.stata_kernel_ds.log'
            log_cmd = 'log using `"{}"\', replace text'.format(log_path)
            rc = kernel.stata.automate('DoCommand', log_cmd)
            if not rc:
                fh = open(log_path, 'r')
                fh.read()
                rc, timer = kernel.stata.do_aut_sync(code)
                res = fh.read()
                kernel.stata.automate('DoCommand', 'cap log close')
                fh.close()

        return res
