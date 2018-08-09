import re
from pygments import lex

from .stata_lexer import StataLexer

# self = CodeManager('di 1\n//\nif {\na\n}\ndi 3')
class CodeManager(object):
    """Class to deal with text before sending to Stata
    """
    def __init__(self, code):
        self.input = code
        self.tokens = self.tokenize_code(code)
        self.tokens_nocomments = self.remove_comments()

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

    def get_chunks(self):
        """Get valid, executable chunks

        Args:
            tokens
        """

        tokens = self.tokens_nocomments

        chunks = []
        token_names = []
        last_token = ''
        counter = -1
        for i in range(len(tokens)):
            if tokens[i][0] != last_token:
                chunks.append([tokens[i][1]])
                token_names.append(tokens[i][0])
                last_token = tokens[i][0]
                counter += 1
                continue

            chunks[counter].append(tokens[i][1])

        chunks = [''.join(x).strip() for x in chunks]
        lines = []
        for chunk, token in zip(chunks, token_names):
            if str(token) != 'Token.MatchingBracket.Other':
                lines.extend(chunk.split('\n'))
            else:
                lines.append(chunk)

        # Remove leading and trailing whitespace from lines. This shouldn't
        # matter because Stata doesn't give a semantic meaning to whitespace.
        lines = [x.strip() for x in lines]

        # Make sure no empty lines. If empty line, there's no blank line in the
        # stata window between the dot prompts, so the current expect regex
        # fails.
        lines = [x for x in lines if x != '']

        return lines
