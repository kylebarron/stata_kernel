import re
from pygments import lex

from .stata_lexer import StataLexer


class CodeManager(object):
    """Class to deal with text before sending to Stata
    """

    def __init__(self, code, semicolon_delimit=False):
        if semicolon_delimit:
            code = '#delimit ;\n' + code
        self.input = code
        self.tokens = self.tokenize_code(code)
        self.tokens_nocomments = self.remove_comments()

        self.ends_sc = str(self.tokens_nocomments[-1][0]) in ['Token.Keyword.Namespace', 'Token.Keyword.Reserved']

        self.has_sc_delimits = 'Token.Keyword.Namespace' in [str(x[0]) for x in self.tokens_nocomments]
        if self.has_sc_delimits:
            self.adjust_for_semicolons()


    def tokenize_code(self, code):
        """Tokenize input code using custom lexer

        Args:
            code (str):
                Input string. I make no assumptions about the structure
                of the code entered here. It could have any line separator and
                comprise of any number of lines.

        Return:
            (List[Tuple[Token, str]]):
                List of token tuples. The only token types currently used in the
                lexer are:
                - Token.MatchingBracket.Other
                - Text
                - Comment.Single
                - Comment.Special
                - Comment.Multiline
        """
        lexer = StataLexer(stripall=True)
        code = re.sub(r'\r\n', r'\n', code)
        return [x for x in lex(code, lexer)]

    def remove_comments(self):
        """Remove comments from tokens

        Return:
            (List[Tuple[Token, str]]):
                list of non-comment tokens
        """
        return [
            x for x in self.tokens if not str(x[0]).startswith('Token.Comment')]

    def adjust_for_semicolons(self):
        # Remove any \n with label Token.Keyword.Namespace
        # These are embedded newlines inside #delimit ; blocks

        tokens = [x for x in self.tokens_nocomments if not ((str(x[0]) == 'Token.Keyword.Namespace') and (x[1] == '\n'))]

        # Find indices of `;`
        inds = [ind for ind, x in enumerate(tokens) if (str(x[0]) == 'Token.Keyword.Reserved') and x[1] == ';']

        # If there are no semicolons,
        if not inds:
            self.tokens_nocomments = self.tokenize_code('')
            return

        # Drop all lines after the last index of ;
        # This is so that a non ;-delimited last line doesn't still get run
        # This actually discards the final ;, but this means that I don't have
        # an extra newline from changing the ; to \n
        tokens = tokens[:max(inds)]

        # Change the ; delimiters to \n
        tokens = [('Newline delimiter', '\n') if (str(x[0]) == 'Token.Keyword.Reserved') and x[1] == ';' else x for x in tokens ]

        # and then join all text together
        text = ''.join([x[1] for x in tokens])

        # Then run it through the tokenizer again once more to get blocks
        self.tokens_nocomments = self.tokenize_code(text)

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

        tokens = self.tokens_nocomments

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
