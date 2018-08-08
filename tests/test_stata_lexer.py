from pygments import lex
from pygments.token import Comment, String, Text
from stata_kernel.stata_lexer import StataLexer

def get_tokens(code):
    lexer = StataLexer(stripall=True)
    return [x for x in lex(code, lexer)]

def test_multiline_comment_after_star():
    code = '* /* a\na\n*/'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '*'),
        (Comment.Single, ' '),
        (Comment.Multiline, '/*'),
        (Comment.Multiline, ' '),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, '*/'),
        (Comment.Single, '\n')]
    assert tokens == expected

