from pygments import lex

from .stata_lexer import StataLexer


class CodeManager(object):
    def __init__(self, code):
        self.input = code
        self.tokens = self.tokenize_code(code)

    def tokenize_code(self, code):
        lexer = StataLexer(stripall=True)
        return [x for x in lex(code, lexer)]

    def remove_comments(self):
        no_com_tokens = [
            x for x in self.tokens if not str(x[0]).startswith('Token.Comment')]
        no_com_tokens = [x[1] for x in no_com_tokens]
        return ''.join(no_com_tokens)
