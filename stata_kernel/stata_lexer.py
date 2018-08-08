import re
from pygments.lexer import RegexLexer, include
from pygments.token import Comment, Name, String, Text


class StataLexer(RegexLexer):
    """Modified Pygments Stata Lexer

    I only need accurate handling of comment, string, and line-continuation
    environments
    """
    flags = re.MULTILINE | re.DOTALL
    tokens = {
        'root': [
            # Later, add include('#delimit;') here
            include('comments'),
            include('vars-strings'),
            (r'.', Text),
        ],
        # Global and local macros; regular and special strings
        'vars-strings': [
            (r'`\w{0,31}\'', Name.Variable),
            (r'"', String, 'string_dquote'),
            (r'`"', String, 'string_mquote'),
        ],
        # For either string type, highlight macros as macros
        'string_dquote': [
            (r'"', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        'string_mquote': [
            (r'"\'', String, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),
            (r'[^$`"\\]+', String),
            (r'[$"\\]', String),
        ],
        'comments': [
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single, 'comments-double-slash'),
            (r'^\s*\*', Comment.Single, 'comments-star'),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'(^///|(?<=\s)///).', Comment.Special, 'comments-triple-slash')
        ],
        'comments-block': [
            (r'/\*', Comment.Multiline, '#push'),
            # this ends and restarts a comment block. but need to catch this so
            # that it doesn\'t start _another_ level of comment blocks
            (r'\*/\*', Comment.Multiline),
            (r'(\*/\s+\*(?!/)[^\n]*)|(\*/)', Comment.Multiline, '#pop'),
            # Match anything else as a character inside the comment
            (r'.', Comment.Multiline),
        ],
        'comments-star': [
            (r'///.*?\n', Comment.Single, '#pop'),
            include('comments'),
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'comments-triple-slash': [
            (r'.(?=\n)', Comment.Special, '#pop'),
            (r'.', Comment.Special),
        ],
        'comments-double-slash': [
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ]
    }
