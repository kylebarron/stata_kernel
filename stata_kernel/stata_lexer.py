from pygments.lexer import RegexLexer, include
from pygments.token import Comment, Name, String, Text


class StataLexer(RegexLexer):
    """Modified Pygments Stata Lexer

    I only need accurate handling of comment, string, and line-continuation
    environments
    """
    tokens = {
        'root': [
            include('comments'),
            include('vars-strings'),
            (r'.', Text),
        ],
        # Global and local macros; regular and special strings
        'vars-strings': [
            (r'\$[\w{]', Name.Variable.Global, 'var_validglobal'),
            (r'`\w{0,31}\'', Name.Variable),
            (r'"', String, 'string_dquote'),
            (r'`"', String, 'string_mquote'),
        ],
        # For either string type, highlight macros as macros
        'string_dquote': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'\$', Name.Variable.Global, 'var_validglobal'),
            (r'`', Name.Variable, 'var_validlocal'),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        'string_mquote': [
            (r'"\'', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'\$', Name.Variable.Global, 'var_validglobal'),
            (r'`', Name.Variable, 'var_validlocal'),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        # * only OK at line start, // OK anywhere
        'comments': [
            (r'^\s*\*.*$', Comment),
            (r'//.*', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline),
            (r'/[*](.|\n)*?[*]/', Comment.Multiline),
        ]
    }
