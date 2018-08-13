import re
import regex
# NOTE: Using regex for (?r) flag


class CompletionsManager(object):
    def __init__(self, kernel):

        # NOTE(mauricio): Locals have to be listed sepparately because
        # inside a Stata program they would only list the locals for
        # that program. Further, we need to match the output until the
        # end of the string OR until '---+\s*end' (the latter in case
        # set trace was set to on.
        self.matchall = re.compile(
            r"\A.*?%mata%(?P<mata>.*?)"
            r"%varlist%(?P<varlist>.*?)"
            r"%globals%(?P<globals>.*?)"
            # r"%locals%(?P<locals>.*?)"
            r"%scalars%(?P<scalars>.*?)"
            r"%matrices%(?P<matrices>.*?)(\Z|---+\s*end)",
            flags = re.DOTALL + re.MULTILINE).match

        # Match output from mata mata desc
        self.matadesc = regex.compile(
            r"(\A.*?---+|---+[\r\n]*\Z)", flags=regex.MULTILINE + regex.DOTALL)

        self.matalist = re.compile(
            r"(?:.*?)\s(\S+)\s*$", flags=re.MULTILINE + re.DOTALL)

        self.mataclean = regex.compile(r"\W")

        self.matainline = regex.compile(r"^m(ata)?\b").search

        self.matacontext = regex.compile(
            r'(?r)(^|\s+)(?<st>_?st_)'
            r'(?<context>\S+?)\('
            r'(?<quote>[^\)]*?")'
            r'(?<pre>[^\)]*?)\Z', flags=regex.MULTILINE + regex.DOTALL).search

        # Varlist-style matching; applies to all
        self.varlist = re.compile(
            r"(?:\s+)(\S+)", flags=re.MULTILINE)

        # Clean line-breaks.
        self.varclean = re.compile(
            r"(?=\s*)[\s\S]{1,2}?^>\s", flags=re.MULTILINE).sub

        # Macth context; this is used to determine if the line starts
        # with matrix or scalar. It also matches constructs like
        #
        #     (`=)?scalar(

        pre = r"(cap(t(u(re?)?)?)?|n(o(i(s(i(ly?)?)?)?)?)?|qui(e(t(ly?)?)?)?)?"
        kwargs = {'flags': regex.MULTILINE}
        self.context = {
            'function':
                regex.compile(
                    r"(?r)(\s+|(?<equals>\=))(?<context>\S+?)"
                    r"\([^\)\s]*?\Z", **kwargs).search,
            'lfunction':
                regex.compile(
                    r"(?r)\s(?<fluff>.*?)`\=(?<context>\S+?)"
                    r"\([^\)\s]*?\Z", **kwargs).search,
            'line':
                regex.compile(
                    r"(?r)^(\s*{0})*(?<context>\S+)".format(pre), **kwargs)
                .search,
            'delimit_line':
                regex.compile(
                    r"\A(\s*{0})*(?<context>\S+)".format(pre), **kwargs).search}

        self.suggestions = self.get_suggestions(kernel)

    def refresh(self, kernel):
        self.suggestions = self.get_suggestions(kernel)

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
                0: varlist
                1: locals, `x* completed with `x*'
                2: globals, $x* completed with $x*
                3: globals, ${x* completed with ${x*}
                4: scalars, scalar .* x* completed with x*
                5: scalars, scalar(x* completed with scalar(x*
                6: matrices, matrix .* x* completed with x*
                7: scalars and varlist, scalar .* = x* completed with x*
                8: matrices and varlsit, matrix .* = x* completed with x*
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

        # Detect space-delimited word.
        env = 0
        env_add = 0
        pos = code.rfind(' ')
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
                    if context.strip() == 'scalar':
                        env_add = 7 if equals else 4
                    elif context.strip() == 'matrix':
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
        if chunk.find('`') >= 0:
            pos += chunk.find('`') + 1
            env = 1
            rcomp = "" if rdelimit[0:1] == "'" else "'"
        elif chunk.find('$') >= 0:
            if chunk.find('{') >= 0:
                pos += chunk.find('{') + 1
                env = 3
                rcomp = "" if rdelimit[0:1] == "}" else "}"
            else:
                env = 2
                pos += chunk.find('$') + 1
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
                    'data',
                    'sdata',
                    'store',
                    'sstore',
                    'view',
                    'sview',
                    'varindex',
                    'varrename',
                    'vartype',
                    'isnumvar',
                    'isstrvar',
                    'vartype',
                    'varformat',
                    'varlabel',
                    'varvaluelabel',
                    'dropvar',
                    'keepvar'
                ]
                _globals = ['global', 'global_hcat']
                _locals = ['local']
                scalars = ['numscalar', 'strnumscalar', 'strnumscalar_hcat']
                matrices = [
                    'matrix',
                    'matrix_hcat',
                    'matrixrowstripe',
                    'matrixcolstripe',
                    'replacematrix'
                ]

                posextra = 0
                if st:
                    posextra += len(st)
                if context:
                    posextra += len(context)
                if quote:
                    posextra += len(quote) + 1

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

        return env, pos, code[pos:], rcomp

    def get(self, starts, env, rcomp):
        """Return environment-aware completions list.
        """
        if env == 0:
            return [
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
            return [
                var for var in self.suggestions['mata']
                if var.startswith(starts)]

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
                self.quickdo(all_locals, kernel).split('\r\n')[1:])
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
                'globals': [],
                'locals': []
            }

        return suggestions

    def quickdo(self, code, kernel):
        """Runs a single line in the Stata console or session
        """
        if kernel.stata.execution_mode == 'console':
            res, timer = kernel.stata.do_console(
                kernel.stata._mata_escape(code))
        else:
            log_path = kernel.stata.cache_dir / '.stata_kernel_completions.log'
            log_cmd = 'log using `"{}"\', replace text'.format(log_path)
            rc = kernel.stata.automate(
                'DoCommand', kernel.stata._mata_escape(log_cmd))
            if not rc:
                fh = open(log_path, 'r')
                fh.read()
                rc, timer = kernel.stata.do_aut_sync(
                    kernel.stata._mata_escape(code))
                res = fh.read()
                kernel.stata.automate(
                    'DoCommand', kernel.stata._mata_escape('cap log close'))
                fh.close()

        return res

    def _parse_mata_desc(self, desc):
        """Parse output from mata desc
        """
        mata_objects = self.matalist.findall(
            self.matadesc.sub('', self.varclean('', desc)))

        mata_suggestions = []
        for x in mata_objects:
            if x.startswith('::'):
                # TODO: Class-aware method suggestions
                continue
                mata_suggestions.append('.' + self.mataclean.sub('', x))
            else:
                mata_suggestions.append(self.mataclean.sub('', x))

        return mata_suggestions
