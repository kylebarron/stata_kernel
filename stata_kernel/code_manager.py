import re
import platform
import hashlib
from pygments import lex

from .stata_lexer import StataLexer
from .stata_lexer import CommentAndDelimitLexer


graph_keywords = [
    r'gr(a|ap|aph)?', r'tw(o|ow|owa|oway)?', r'sc(a|at|att|atte|atter)?',
    r'line', r'hist(o|og|ogr|ogra|ogram)?', r'kdensity', r'lowess', r'lpoly',
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
graph_keywords = r'\b(' + '|'.join(graph_keywords) + r')\b'


class CodeManager(object):
    """Class to deal with text before sending to Stata
    """

    def __init__(self, code, semicolon_delimit=False):
        code = re.sub(r'\r\n', r'\n', code)
        self.input = code
        if semicolon_delimit:
            code = '#delimit ;\n' + code

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
        if not 'Token.TextInSemicolonBlock' in [str(x[0]) for x in tokens]:
            return tokens

        # Replace newlines in `;`-delimited blocks with spaces
        tokens = [('Space instead of newline', ' ')
                  if (str(x[0]) == 'Token.TextInSemicolonBlock') and x[1] == '\n'
                  else x for x in tokens[:-1]]

        # Change the ; delimiters to \n
        tokens = [('Newline delimiter', '\n') if
                  (str(x[0]) == 'Token.SemicolonDelimiter') and x[1] == ';' else x
                  for x in tokens]
        return tokens

    def tokenize_second_pass(self, code):
        """Tokenize clean code for syntactic blocks

        Args:
            code (str):
                Input string. Should have `\\n` as the delimiter. Should have no
                comments. Should use `\\n` for end of lines.

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
        if str(self.tokens_final[-1][0]) == 'Token.TextBlock':
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

    def get_text(self, cache_dir, graph_format):
        """Get valid, executable text

        First split non-comment tokens into semantic chunks. So a (possibly
        multiline) chunk of regular text, then a chunk for a block, and so on.

        Then split each semantic chunk into syntactic chunks. So each of these
        is a string that can be sent to Stata and will return a dot prompt.

        I strip leading and trailing whitespace from each syntactic chunk. This
        shouldn't matter because Stata doesn't give a semantic meaning to extra
        whitespace. I also make sure there are no empty syntactic chunks (i.e.
        no empty lines). If I send an empty line to Stata, no blank line is
        returned between dot prompts, so the pexpect regex fails.

        Returns:
            (str, str): Text to run, md5 to expect for.

        TODO: Add graph size formats to export
        TODO: On automation I might decide to route _everything_ through include
        """

        tokens = self.tokens_final

        text = ''.join([x[1] for x in tokens]).strip()
        lines = text.split('\n')
        has_block = bool([x for x in tokens if str(x[0]) == 'Token.TextBlock'])

        use_include = has_block
        cap_re = re.compile(r'\bcap(t|tu|tur|ture)?\b').search
        qui_re = re.compile(r'\bqui(e|et|etl|etly)?\b').search
        noi_re = re.compile(r'\bn(o|oi|ois|oisi|oisil|oisily)?\b').search
        if cap_re(text) or qui_re(text) or noi_re(text):
            use_include = True

        if len(lines) > 3:
            use_include = True

        # Insert `graph export`
        cache_dir_str = str(cache_dir)
        if platform.system() == 'Windows':
            cache_dir_str = re.sub(r'\\', '/', cache_dir_str)
        gph_cnt = 'stata_kernel_graph_counter'
        g_exp = '\nnoi graph export {}'.format(cache_dir_str)
        g_exp += '/graph${' + gph_cnt + '}'
        g_exp += '.{}, replace'.format(graph_format)
        g_exp += '\nglobal {0} = ${0} + 1'.format(gph_cnt)

        lines = [x + g_exp if re.search(graph_keywords, x) else x for x in lines]

        text = '\n'.join(lines)
        hash_text = hashlib.md5(text.encode('utf-8')).hexdigest()
        text_to_exclude = text
        if use_include:
            with open(cache_dir / 'include.do', 'w') as f:
                f.write(text + '\n')
            text = "include {}/include.do".format(cache_dir_str)
            text_to_exclude = text + '\n' + text_to_exclude

        text += "\n`{}'".format(hash_text)
        return text, hash_text, text_to_exclude
