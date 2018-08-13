import re
from pygments import lex

from .stata_lexer import StataLexer
from .stata_lexer import CommentAndDelimitLexer


class CodeManager(object):
    """Class to deal with text before sending to Stata
    """

    def __init__(self, code, semicolon_delimit=False, mata_mode=False):

        # mata goes second since it obeys #delimit! Append \n to detect
        # whenever input ends but mata was left in a line continuaton
        code = re.sub(r'\r\n', r'\n', code)
        self.input = code
        if semicolon_delimit:
            if mata_mode:
                code = 'mata;\n' + code + '\n'

            code = '#delimit ;\n' + code + '\n'
        elif mata_mode:
            code = 'mata\n' + code + '\n'

        # First use the Comment and Delimiting lexer
        self.tokens_fp_all = self.tokenize_first_pass(code)
        self.tokens_fp_no_comments = self.remove_comments(self.tokens_fp_all)

        if not self.tokens_fp_no_comments:
            self.tokens_fp_no_comments = [('Token.Text', '')]

        self.ends_sc = str(self.tokens_fp_no_comments[-1][0]) in [
            'Token.Keyword.Namespace', 'Token.Keyword.Reserved']

        tokens_nl_delim = self.convert_delimiter(self.tokens_fp_no_comments)
        text = ''.join([x[1] for x in tokens_nl_delim])
        self.tokens_final = self.tokenize_second_pass(text)

        self.has_mata_mode = False
        if mata_mode:
            self.has_mata_mode = True
            self.tokens_final = self.tokens_final[1:]

        self.ends_mata = False
        for token, chunk in self.tokens_final:
            if str(token) == 'Token.Aborted':
                self.ends_mata = True
                self.has_mata_mode = False
            elif str(token) == 'Token.Other':
                self.ends_mata = False
                self.has_mata_mode = True

        # = 'Token.Other' in [
        #     str(x[0]) for x in self.tokens_final]
        # if mata_mode:
        #     self.ends_mata = 'Token.Aborted' in [
        #         str(x[0]) for x in self.tokens_final]
        # else:
        #     self.ends_mata = False

        self.is_complete = self._is_complete()

        # Append "" to mata to force statements like "if" to end.
        if self.has_mata_mode:
            self.tokens_final += [('Token.Text', '""')]

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
        if not 'Token.Keyword.Namespace' in [str(x[0]) for x in tokens]:
            return tokens

        # Replace newlines in `;`-delimited blocks with spaces
        tokens = [('Space instead of newline', ' ')
                  if (str(x[0]) == 'Token.Keyword.Namespace') and x[1] == '\n'
                  else x for x in tokens[:-1]]

        # Change the ; delimiters to \n
        tokens = [('Newline delimiter', '\n') if
                  (str(x[0]) == 'Token.Keyword.Reserved') and x[1] == ';' else x
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
        if str(self.tokens_final[-1][0]) == 'Token.MatchingBracket.Other':
            return False

        # last token a line-continuation comment
        if str(self.tokens_fp_all[-1][0]) in ['Token.Comment.Multiline',
                                              'Token.Comment.Special']:
            return False

        if self.ends_sc:
            # Find indices of `;`
            inds = [
                ind for ind, x in enumerate(self.tokens_fp_no_comments)
                if (str(x[0]) == 'Token.Keyword.Reserved') and x[1] == ';']

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

    def get_chunks(self):
        """Get valid, executable chunks

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
            List[Tuple[Token, str]]
        """

        tokens = self.tokens_final

        sem_chunks = []
        token_names = []
        last_token = ''
        counter = -1
        for i in range(len(tokens)):
            if tokens[i][0] != last_token:
                sem_chunks.append([tokens[i][1]])
                token_names.append(tokens[i][0])
                last_token = tokens[i][0]
                counter += 1
                continue

            sem_chunks[counter].append(tokens[i][1])

        sem_chunks = [''.join(x).strip() for x in sem_chunks]
        syn_chunks = []
        for chunk, token in zip(sem_chunks, token_names):
            if str(token) != 'Token.MatchingBracket.Other':
                syn_chunks.extend([[token, x] for x in chunk.split('\n')])
            else:
                syn_chunks.append([token, chunk])

        return [(token, text.strip())
                for token, text in syn_chunks
                if text.strip() != '']
