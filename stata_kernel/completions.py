import os
import re
import platform

from .code_manager import CodeManager
from .pygments._mata_builtins import mata_builtins


# NOTE: Add command completion (e.g. r<tab>; mata: st_<tab>)
# NOTE: Add extended_fcn completions, `:<tab>
# NOTE: Add sub-command completions for scalars and matrices?
class CompletionsManager():
    def __init__(self, kernel, config):
        self.config = config
        self.kernel = kernel

        # Path completion
        self.path_search = re.compile(
            r'^(?P<fluff>.*")(?P<path>[^"]*)\Z').search

        # Magic completion
        self.magic_completion = re.compile(
            r'\A%(?P<magic>\S*)\Z', flags=re.DOTALL + re.MULTILINE).match

        self.set_magic_completion = re.compile(
            r'\A%set (?P<setting>\S*)\Z', flags=re.DOTALL + re.MULTILINE).match

        # NOTE(mauricio): Locals have to be listed separately because
        # inside a Stata program they would only list the locals for
        # that program. Further, we need to match the output until the
        # end of the string OR until '---+\s*end' (the latter in case
        # set trace was set to on.
        self.matchall = re.compile(
            r"\A.*?%mata%(?P<mata>.*?)"
            r"%varlist%(?P<varlist>.*?)"
            r"%globals%(?P<globals>.*?)"
            # r"%locals%(?P<locals>.*?)"
            r"%logfiles%(?P<logfiles>.*?)"
            r"%scalars%(?P<scalars>.*?)"
            r"%matrices%(?P<matrices>.*?)(\Z|---+\s*end)",
            flags=re.DOTALL + re.MULTILINE).match

        # Match output from mata mata desc
        self.matadesc = re.compile(
            r"(\A.*?---+|---+[\r\n]*\Z)", flags=re.MULTILINE + re.DOTALL)

        self.matalist = re.compile(
            r"(?:.*?)\s(\S+)\s*$", flags=re.MULTILINE + re.DOTALL)

        self.mataclean = re.compile(r"\W.*?(\b|$)")
        self.matasearch = re.compile(r"(?P<kw>\w.*?(?=\W|\b|$))").search

        self.matainline = re.compile(r"^m(ata)?\b").search

        self.matacontext = re.compile(
            r'(^|\s+)(?P<st>_?st_)'
            r'(?P<context>\S+?)\('
            r'(?P<quote>[^\)]*?")'
            r'(?P<pre>[^\)]*?)\Z', flags=re.MULTILINE + re.DOTALL).search

        # Varlist-style matching; applies to all
        self.varlist = re.compile(r"(?:\s+)(\S+)", flags=re.MULTILINE)

        # Clean line-breaks.
        self.varclean = re.compile(
            r"(?=\s*)[\r\n]{1,2}?^>\s", flags=re.MULTILINE).sub

        # Macth context; this is used to determine if the line starts
        # with matrix or scalar. It also matches constructs like
        #
        #     (`=)?scalar(

        pre = (
            r'(cap(t|tu|tur|ture)?'
            r'|qui(e|et|etl|etly)?'
            r'|n(o|oi|ois|oisi|oisil|oisily)?)')
        kwargs = {'flags': re.MULTILINE}
        self.context = {
            'function':
                re.compile(
                    r"(\s+|(?P<equals>\=))(?P<context>\S+?)"
                    r"\([^\)\s]*?\Z", **kwargs).search,
            'lfunction':
                re.compile(
                    r"\s(?P<fluff>.*?)`\=(?P<context>\S+?)"
                    r"\([^\)\s]*?\Z", **kwargs).search,
            'line':
                re.compile(
                    r"^\s*({0}\s+)*(?P<context>\S+)".format(pre), **kwargs)
                .search,
            'delimit_line':
                re.compile(
                    r"\A\s*({0}\s+)*(?P<context>\S+)".format(pre), **kwargs)
                .search}

        self.suggestions = self.get_suggestions(kernel)
        self.suggestions['magics'] = kernel.magics.available_magics
        self.suggestions['magics_set'] = kernel.conf.all_settings

    def refresh(self, kernel):
        self.suggestions = self.get_suggestions(kernel)
        self.suggestions['magics'] = kernel.magics.available_magics
        self.suggestions['magics_set'] = kernel.conf.all_settings
        self.globals = self.get_globals(kernel)

    def get_env(self, code, rdelimit, sc_delimit_mode, mata_mode):
        """Returns completions environment

        Args:
            code (str): Right-truncated to cursor position
            rdelimit (str): The two characters immediately after code.
                Will be used to accurately determine rcomp.
            sc_delimit_mode (bool): Whether #delimit ; is on.
            mata_mode (bool): Whether mata is on

        Returns:
            env (int):
                -2: %set magic, %set x*
                -1: magics, %x*
                0: varlist and/or file path
                1: locals, `x* completed with `x*'
                2: globals, $x* completed with $x*
                3: globals, ${x* completed with ${x*}
                4: scalars, scalar .* x* completed with x*
                5: scalars, scalar(x* completed with scalar(x*
                6: matrices, matrix .* x* completed with x*
                7: scalars and varlist, scalar .* = x* completed with x*
                8: matrices and varlist, matrix .* = x* completed with x*
                9: mata, inline or in mata environment
            pos (int):
                Where the completions start. This is set to the start
                of the word to be completed.
            code (str):
                Word to match.
            rcomp (str):
                How to finish the completion. Blank by default.
                    locals: '
                    globals (if start with ${): }
                    scalars: )
                    scalars (if start with `): )'
        """

        lcode = code.lstrip()
        if self.magic_completion(lcode):
            pos = code.rfind("%") + 1
            env = -1
            rcomp = ""
            return env, pos, code[pos:], rcomp
        elif self.set_magic_completion(lcode):
            pos = max(code.rfind(' '), code.rfind('"')) + 1
            env = -2
            rcomp = ""
            return env, pos, code[pos:], rcomp

        # Detect space-delimited word.
        env = 0
        env_add = 0
        search = re.search(r'(?<![`$"{/])\b\w+\Z', code, flags=re.MULTILINE)
        searchpos = -1 if search is None else search.start() - 1
        pos = max(code.rfind(' '), code.rfind('"'), searchpos)
        rcomp = ''
        if pos >= 0:
            pos += 1

            if mata_mode:
                env_add = 9
            else:
                # Figure out if current statement is a matrix or scalar
                # statement. If so, will add them to completions list.
                if sc_delimit_mode:
                    linecontext = self.context['delimit_line'](code)
                else:
                    linecontext = self.context['line'](code)

                if linecontext:
                    context = linecontext.groupdict()['context']
                    equals = (code.find('=') > 0)
                    if re.match(r'^sca(lar|la|l)?$', context.strip()):
                        env_add = 7 if equals else 4
                    elif re.match(r'^mat(rix|ri|r)?$', context.strip()):
                        env_add = 8 if equals else 6
                    elif self.matainline(context.strip()):
                        env_add = 9

                # Constructs of the form scalar(x<tab> will be filled only
                # with scalars. This can be preceded by = or `=
                if env_add == 0:
                    lfuncontext = self.context['lfunction'](code)
                    if lfuncontext:
                        lfunction = lfuncontext.groupdict()['context']
                        fluff = lfuncontext.groupdict()['fluff']
                        lfluff = 0 if not fluff else len(fluff)
                        if lfunction == 'scalar':
                            env_add = 5
                            pos += len(lfunction) + 3 + lfluff
                            if rdelimit == ")'":
                                rcomp = ""
                            elif rdelimit[0:1] == ")":
                                rcomp = ""
                            elif rdelimit[0:1] == "'":
                                rcomp = ")"
                            else:
                                rcomp = ")'"
                    else:
                        funcontext = self.context['function'](code)
                        if funcontext:
                            function = funcontext.groupdict()['context']
                            extra = 2 if funcontext.groupdict()['equals'] else 1
                            if function == 'scalar':
                                env_add = 5
                                pos += len(function) + extra
                                rcomp = "" if rdelimit[0:1] == ")" else ")"
        else:
            pos = 0
            if mata_mode:
                env_add = 9

        # Figure out if this is a local or global; env = 0 (default)
        # will suggest variables in memory.
        chunk = code[pos:]
        lfind = chunk.rfind('`')
        gfind = chunk.rfind('$')
        path_chars = any(x in chunk for x in ['/', '\\', '~'])
        chunk_quoted = chunk[lfind:].startswith('`"')

        if lfind >= 0 and (lfind > gfind) and not chunk_quoted:
            pos += lfind + 1
            env = 1
            rcomp = "" if rdelimit[0:1] == "'" else "'"
        elif gfind >= 0 and not path_chars:
            bfind = chunk.rfind('{')
            if bfind >= 0 and (bfind > gfind):
                pos += bfind + 1
                env = 3
                rcomp = "" if rdelimit[0:1] == "}" else "}"
            else:
                env = 2
                pos += gfind + 1
        elif chunk.startswith('"'):
            pos += 1
        elif chunk.startswith('`"'):
            pos += 2
        else:
            # Set to matrix or scalar environment, if applicable. Note
            # that matrices and scalars can be set to variable values,
            # so varlist is still a valid completion in a matrix or
            # scalar context.
            env += env_add

        if env == 9:
            matacontext = self.matacontext(code)
            if matacontext:
                st, context, quote, pre = matacontext.groupdict().values()
                varlist = [
                    'data', 'sdata', 'store', 'sstore', 'view', 'sview',
                    'varindex', 'varrename', 'vartype', 'isnumvar', 'isstrvar',
                    'vartype', 'varformat', 'varlabel', 'varvaluelabel',
                    'dropvar', 'keepvar']
                _globals = ['global', 'global_hcat']
                _locals = ['local']
                scalars = ['numscalar', 'strscalar', 'numscalar_hcat']
                matrices = [
                    'matrix', 'matrix_hcat', 'matrixrowstripe',
                    'matrixcolstripe', 'replacematrix']

                posextra = 0
                # if st:
                #     posextra += len(st)
                # if context:
                #     posextra += len(context)
                # if quote:
                #     posextra += len(quote) + 1

                if context in varlist:
                    env = 0
                elif context in _globals:
                    env = 2
                    rcomp = ''
                elif context in _locals:
                    env = 1
                    rcomp = ''
                elif context in scalars:
                    env = 4
                    rcomp = ''
                elif context in matrices:
                    env = 6
                    rcomp = ''
                else:
                    posextra = 0

                pos += posextra

        closing_symbol = self.config.get('autocomplete_closing_symbol', 'False')
        closing_symbol = closing_symbol.lower() == 'true'
        if not closing_symbol:
            rcomp = ''

        return env, pos, code[pos:], rcomp

    # NOTE: Simplify this
    def get(self, starts, env, rcomp):
        """Return environment-aware completions list.
        """
        if env == -2:
            return [
                var for var in self.suggestions['magics_set']
                if var.startswith(starts)]
        elif env == -1:
            return [
                var for var in self.suggestions['magics']
                if var.startswith(starts)]
        elif env == 0:
            paths = self.get_file_paths(starts)
            return paths + [
                var for var in self.suggestions['varlist']
                if var.startswith(starts)]
        elif env == 1:
            return [
                var + rcomp
                for var in self.suggestions['locals']
                if var.startswith(starts)]
        elif env == 2:
            return [
                var for var in self.suggestions['globals']
                if var.startswith(starts)]
        elif env == 3:
            return [
                var + rcomp
                for var in self.suggestions['globals']
                if var.startswith(starts)]
        elif env == 4:
            return [
                var for var in self.suggestions['scalars']
                if var.startswith(starts)]
        elif env == 5:
            return [
                var + rcomp
                for var in self.suggestions['scalars']
                if var.startswith(starts)]
        elif env == 6:
            return [
                var for var in self.suggestions['matrices']
                if var.startswith(starts)]
        elif env == 7:
            return [
                var for var in self.suggestions['scalars']
                if var.startswith(starts)] + [
                    var for var in self.suggestions['varlist']
                    if var.startswith(starts)]
        elif env == 8:
            return [
                var for var in self.suggestions['matrices']
                if var.startswith(starts)] + [
                    var for var in self.suggestions['varlist']
                    if var.startswith(starts)]
        elif env == 9:
            if len(starts) > 1:
                builtins = [
                    var for var in mata_builtins if var.startswith(starts)]
            else:
                builtins = []

            if re.search(r'[/\\]', starts):
                paths = self.get_file_paths(starts)
            else:
                paths = []

            return [
                var for var in self.suggestions['mata']
                if var.startswith(starts)] + builtins + paths

    def get_file_paths(self, chunk):
        """Get file paths based on chunk

        Args:
            chunk (str): chunk of text after last space. Doesn't include string
                punctuation characters

        Returns:
            (List[str]): folders and files at that location
        """

        # If local exists, return empty list
        if re.search(r'[`\']', chunk):
            return []

        # Define directory separator
        dir_sep = '/'
        if platform.system() == 'Windows':
            if '/' not in chunk:
                dir_sep = '\\'

        # Get directory without ending file, and without / or \
        if any(x in chunk for x in ['/', '\\']):
            ind = max(chunk.rfind('/'), chunk.rfind('\\'))
            user_folder = chunk[:ind + 1]
            user_starts = chunk[ind + 1:]

            # Replace multiple consecutive / with a single /
            user_folder = re.sub(r'/+', '/', user_folder)
            user_folder = re.sub(r'\\+', r'\\', user_folder)

        else:
            user_folder = ''
            user_starts = chunk

        # Replace globals with their values
        globals_re = r'\$\{?((?![0-9_])\w{1,32})\}?'
        try:
            folder = re.sub(
                globals_re, lambda x: self.globals[x.group(1)], user_folder)
        except KeyError:
            # If the global doesn't exist in self.globals (aka it hasn't been
            # defined in the Stata environment yet), then there are no paths to
            # check
            return []

        # Use Stata's relative path
        abspath = re.search(r'^([/~]|[a-zA-Z]:)', folder)
        if not abspath:
            folder = self.kernel.stata.cwd + '/' + folder

        try:
            top_dir, dirs, files = next(os.walk(os.path.expanduser(folder)))
            results = [x + dir_sep for x in dirs] + files
            results = [
                user_folder + x for x in results if not x.startswith('.')
                and re.match(re.escape(user_starts), x, re.I)]

        except StopIteration:
            results = []

        return sorted(results)

    def get_suggestions(self, kernel):
        match = self.matchall(self.quickdo('_StataKernelCompletions', kernel))
        if match:
            suggestions = match.groupdict()
            suggestions['mata'] = self._parse_mata_desc(suggestions['mata'])
            for k, v in suggestions.items():
                if k == 'mata':
                    continue
                suggestions[k] = self.varlist.findall(self.varclean('', v))

            all_locals = """mata : invtokens(st_dir("local", "macro", "*")')"""
            res = '\r\n'.join(
                re.split(r'[\r\n]{1,2}', self.quickdo(all_locals, kernel)))
            if res.strip():
                suggestions['locals'] = self.varlist.findall(
                    self.varclean('', res))
            else:
                suggestions['locals'] = []
        else:
            suggestions = {
                'varlist': [],
                'scalars': [],
                'matrices': [],
                'logfiles': [],
                'globals': [],
                'locals': []}

        suggestions['globals'] = [
            x for x in suggestions['globals']
            if x != 'stata_kernel_graph_counter']

        return suggestions

    def get_globals(self, kernel):
        res = self.quickdo("macro list `:all globals'", kernel)
        vals = re.split(r'^(\w+):', res, flags=re.MULTILINE)
        # TODO: Check if leading line in output
        if not vals[0].strip():
            vals = vals[1:]
        vals = [x.strip() for x in vals]
        return {x: y for x, y in zip(vals[::2], vals[1::2])}

    def quickdo(self, code, kernel):
        code = kernel.stata._mata_escape(code)
        cm = CodeManager(code)
        text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf)
        rc, res = kernel.stata.do(
            text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
        return res

    def _parse_mata_desc(self, desc):
        """Parse output from mata desc
        """
        mata_objects = self.matalist.findall(
            self.matadesc.sub('', self.varclean('', desc)))

        mata_class = ''
        mata_suggestions = []
        for x in mata_objects:
            kw = self.matasearch(x).groupdict()['kw']
            if x.startswith('::'):
                continue
                # NOTE(mauricio): Class-aware completions?
                mata_suggestions.append(mata_class + '.' + kw)
            else:
                mata_suggestions.append(kw)
                mata_class = kw

        return mata_suggestions
