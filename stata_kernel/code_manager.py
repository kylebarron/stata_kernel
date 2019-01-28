import re
import platform
import hashlib

from pygments import lex
from textwrap import dedent

from .stata_lexer import StataLexer
from .stata_lexer import CommentAndDelimitLexer

base_graph_keywords = [
    r'gr(a|ap|aph)?' + r'(?!\s+' + r'(save|replay|print|export|dir|set|' +
    r'des(c|cr|cri|crib|cribe)?|rename|copy|drop|close|q(u|ue|uer|uery)?))',
    r'tw(o|ow|owa|oway)?', r'sc(atter)?', r'line',
    r'hist(o|og|ogr|ogra|ogram)?', r'kdensity', r'lowess', r'lpoly',
    r'tsr?line', r'symplot', r'quantile', r'qnorm', r'pnorm', r'qchi', r'pchi',
    r'qqplot', r'gladder', r'qladder', r'rvfplot', r'avplot', r'avplots',
    r'cprplot', r'acprplot', r'rvpplot', r'lvr2plot', r'ac', r'pac', r'pergram',
    r'cumsp', r'xcorr', r'wntestb', r'estat\s+acplot', r'estat\s+aroots',
    r'estat\s+sbcusum', r'fcast\s+graph', r'varstable', r'vecstable',
    r'irf\s+graph', r'irf\s+ograph', r'irf\s+cgraph', r'xtline'
    r'sts\s+graph', r'strate', r'ltable', r'stci', r'stphplot', r'stcoxkm',
    r'estat phtest', r'stcurve', r'roctab', r'rocplot', r'roccomp',
    r'rocregplot', r'lroc', r'lsens', r'biplot', r'irtgraph\s+icc',
    r'irtgraph\s+tcc', r'irtgraph\s+iif', r'irtgraph\s+tif', r'biplot',
    r'cluster dendrogram', r'screeplot', r'scoreplot', r'loadingplot',
    r'procoverlay', r'cabiplot', r'caprojection', r'mcaplot', r'mcaprojection',
    r'mdsconfig', r'mdsshepard', r'cusum', r'cchart', r'pchart', r'rchart',
    r'xchart', r'shewhart', r'serrbar', r'marginsplot', r'bayesgraph',
    r'tabodds', r'teffects\s+overlap', r'npgraph', r'grmap', r'pkexamine']


class CodeManager():
    """Class to deal with text before sending to Stata
    """

    def __init__(self, code, semicolon_delimit=False, mata_mode=False):
        code = re.sub(r'\r\n', r'\n', code)
        # Hard tabs in input are not shown in output and mess up removing lines
        code = re.sub(r'\t', ' ', code)
        self.input = code
        if semicolon_delimit:
            if mata_mode:
                code = 'mata;\n' + code

            code = '#delimit ;\n' + code
        elif mata_mode:
            code = 'mata\n' + code

        # First use the Comment and Delimiting lexer
        self.tokens_fp_all = self.tokenize_first_pass(code)
        self.tokens_fp_no_comments = self.remove_comments(self.tokens_fp_all)

        if not self.tokens_fp_no_comments:
            self.tokens_fp_no_comments = [('Token.Text', '')]

        self.ends_sc = str(self.tokens_fp_no_comments[-1][0]) in [
            'Token.TextInSemicolonBlock', 'Token.SemicolonDelimiter']

        tokens_nl_delim = self.convert_delimiter(self.tokens_fp_no_comments)
        text = ''.join([x[1] for x in tokens_nl_delim])
        self.tokens_final = self.tokenize_second_pass(text)

        # NOTE: Consider wrapping mata call for include in mata and
        # end. Do not include end in the include file if the result of
        # this loop is.  False Instead, send end before the include file
        # is done.

        self.mata_mode = False
        self.mata_open = False
        self.mata_error = False
        if mata_mode:
            self.mata_open = True
            self.mata_mode = True
            self.tokens_final = self.tokens_final[1:]

        self.mata_closed = False
        for token, chunk in self.tokens_final:
            if str(token) == 'Token.Mata.Close':
                self.mata_closed = True
                self.mata_mode = False
            elif str(token).startswith('Token.Mata.Open'):
                self.mata_closed = False
                self.mata_mode = True
                if str(token) == 'Token.Mata.OpenError':
                    self.mata_error = True

        self.is_complete = self._is_complete()

    def tokenize_first_pass(self, code):
        """Tokenize input code for Comments and Delimit blocks

        Args:
            code (str):
                Input string. Should use `\\n` for end of lines.

        Return:
            (List[Tuple[Token, str]]):
                List of token tuples. The only token types currently used in the
                lexer are:
                - Text (plain text)
                - Comment.Single (// and *)
                - Comment.Special (///)
                - Comment.Multiline (/* */)
                - Keyword.Namespace (code inside #delimit ; block)
                - Keyword.Reserved (; delimiter)
        """
        comment_lexer = CommentAndDelimitLexer(stripall=False, stripnl=False)
        return [x for x in lex(code, comment_lexer)]

    def remove_comments(self, tokens):
        """Remove comments from tokens

        Return:
            (List[Tuple[Token, str]]):
                list of non-comment tokens
        """
        return [x for x in tokens if not str(x[0]).startswith('Token.Comment')]

    def convert_delimiter(self, tokens):
        """If parts of tokens are `;`-delimited, convert to `\\n`-delimited

        - If there are no ;-delimiters, return
        - Else, replace newlines with spaces, see https://github.com/kylebarron/stata_kernel/pull/70#issuecomment-412399978
        - Then change the ; delimiters to newlines
        """

        # If all tokens are newline-delimited, return
        if 'Token.TextInSemicolonBlock' not in [str(x[0]) for x in tokens]:
            return tokens

        # Replace newlines in `;`-delimited blocks with spaces
        tokens = [('Space instead of newline', ' ')
                  if (str(x[0]) == 'Token.TextInSemicolonBlock')
                  and x[1] == '\n' else x for x in tokens[:-1]]

        # Change the ; delimiters to \n
        tokens = [('Newline delimiter', '\n')
                  if (str(x[0]) == 'Token.SemicolonDelimiter') and x[1] == ';'
                  else x for x in tokens]
        return tokens

    def tokenize_second_pass(self, code):
        """Tokenize clean code for syntactic blocks

        Args:
            code (str):
                Input string. Should have `\\n` as the delimiter. Should have no
                comments. Should use `\\n` for end of lines.

        Return:
            (List[Tuple[Token, str]]):
                List of token tuples. Some of the token types:
                lexer are:
                - Text (plain text)
                - Comment.Single (// and *)
                - Comment.Special (///)
                - Comment.Multiline (/* */)
                - Keyword.Namespace (code inside #delimit ; block)
                - Keyword.Reserved (; delimiter)
        """
        block_lexer = StataLexer(stripall=False, stripnl=False)
        return [x for x in lex(code, block_lexer)]

    def _is_complete(self):
        """Determine whether the code provided is complete

        Ways in which code entered is not complete:
        - If in the middle of a block construct, i.e. foreach, program, input
        - If the last token provided is inside a line-continuation comment, i.e.
          `di 2 + ///` or `di 2 + /*`.
        - If in a #delimit ; block and there are non-whitespace characters after
          the last semicolon.

        Special case for code to be complete:
        - %magics
        """

        magic_regex = re.compile(
            r'\A%(?P<magic>.+?)(?P<code>\s+.*)?\Z',
            flags=re.DOTALL + re.MULTILINE)
        if magic_regex.search(self.input):
            return True

        # block constructs
        if str(self.tokens_final[-1][0]).startswith('Token.TextBlock'):
            return False

        # last token a line-continuation comment
        if str(self.tokens_fp_all[-1][0]) in ['Token.Comment.Multiline',
                                              'Token.Comment.Special']:
            return False

        if self.ends_sc:
            # Find indices of `;`
            inds = [
                ind for ind, x in enumerate(self.tokens_fp_no_comments)
                if (str(x[0]) == 'Token.SemicolonDelimiter') and x[1] == ';']

            if not inds:
                inds = [0]

            # Check if there's non whitespace text after the last semicolon
            # If so, then it's not complete
            tr_text = ''.join([
                x[1]
                for x in self.tokens_fp_no_comments[max(inds) + 1:]]).strip()
            if tr_text:
                return False

        return True

    def get_text(self, config, stata=None):
        """Get valid, executable text

        For any text longer than one line, I save the text to a do file and send
        `include path_to_do_file` to Stata. I insert `graph export` after
        _every_ graph keyword. This way, even if the graph is created within a
        loop or program, I can still see that it was created and I can grab it.

        I create an md5 of the lines of text that I run, and then add that as
        `md5' so that I can definitively know when Stata has finished with the
        code I sent it.

        Args:
            config (.config.Config): Configuration instance

        Returns:
            (str, str, str):
            (Text to run in kernel, md5 to expect for, code lines to remove from output)
        """

        tokens = self.tokens_final

        text = ''.join([x[1] for x in tokens]).strip()
        lines = text.split('\n')

        # Remove empty lines. This is important because there are often extra
        # newlines from removed comments. And they can confuse the code that
        # removes code lines from the log output.
        lines = [x for x in lines if x.strip() != '']

        has_block = bool([x for x in tokens if str(x[0]) == 'Token.TextBlock'])

        use_include = has_block
        cap_re = re.compile(r'\bcap(t|tu|tur|ture)?\b').search
        qui_re = re.compile(r'\bqui(e|et|etl|etly)?\b').search
        noi_re = re.compile(r'\bn(o|oi|ois|oisi|oisil|oisily)?\b').search
        if cap_re(text) or qui_re(text) or noi_re(text):
            use_include = True

        if len(lines) > 1:
            use_include = True

        if stata:
            use_include = use_include and not stata.mata_open
            use_include = use_include and not stata.mata_mode

        # Insert `graph export`
        graph_fmt = config.get('graph_format', 'svg')
        graph_scale = float(config.get('graph_scale', '1'))
        graph_width = int(config.get('graph_width', '600'))
        graph_height = config.get('graph_height')
        cache_dir = config.get('cache_dir')
        if graph_fmt == 'svg':
            pdf_dup = config.get('graph_svg_redundancy', 'True')
        elif graph_fmt == 'png':
            pdf_dup = config.get('graph_png_redundancy', 'False')
        pdf_dup = pdf_dup.lower() == 'true'

        dim_str = " width({})".format(int(graph_width * graph_scale))
        if graph_height:
            graph_height = int(graph_height)
            dim_str += " height({})".format(int(graph_height * graph_scale))
        if graph_fmt == 'pdf':
            dim_str = ''

        cache_dir_str = str(cache_dir)
        if platform.system() == 'Windows':
            cache_dir_str = re.sub(r'\\', '/', cache_dir_str)
        gph_cnt = 'stata_kernel_graph_counter'

        # yapf: disable
        if not pdf_dup:
            g_exp = dedent("""
            if _rc == 0 {{
                noi gr export {0}/graph${1}.{2},{3} replace
                global {1} = ${1} + 1
            }}\
            """.format(cache_dir_str, gph_cnt, graph_fmt, dim_str))
        else:
            g_exp = dedent("""
            if _rc == 0 {{
                noi gr export {0}/graph${1}.{2},{3} replace
                noi gr export {0}/graph${1}.pdf, replace
                global {1} = ${1} + 1
            }}\
            """.format(cache_dir_str, gph_cnt, graph_fmt, dim_str))

        if stata:
            g_exp = stata._mata_escape(g_exp)
        # yapf: enable

        user_graph_keywords = config.get(
            'user_graph_keywords', 'coefplot,vioplot')
        user_graph_keywords = [
            re.sub(r'\s+', '\\\\s+', x.strip())
            for x in user_graph_keywords.split(',')]
        graph_keywords = r'^\s*\b({})\b'.format(
            '|'.join([*base_graph_keywords, *user_graph_keywords]))
        lines = [
            'cap noi ' + x + g_exp if re.match(graph_keywords, x) else x
            for x in lines]

        text = '\n'.join(lines)
        hash_text = hashlib.md5(text.encode('utf-8')).hexdigest()
        text_to_exclude = text
        if use_include:
            with (cache_dir / 'include.do').open('w', encoding='utf-8') as f:
                f.write(text + '\n')
            text = "include {}/include.do".format(cache_dir_str)
            text_to_exclude = text + '\n' + text_to_exclude

        text += "\n`{}'".format(hash_text)
        return text, hash_text, text_to_exclude
