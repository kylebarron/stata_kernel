import re
from pygments.lexer import RegexLexer, include
from pygments.token import Comment, String, Text, Token

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
            include('strings'),
            (r'(cap(t|tu|tur|ture)?|qui(e|et|etl|etly)?|n(o|oi|ois|oisi|oisil|oisily))\s*:?\s*\{', Token.MatchingBracket.Other, 'cap-noi-qui-chunk'),
            (r'.', Text),
        ],
        'cap-noi-qui-chunk': [
            (r'\{', Token.MatchingBracket.Other, '#push'),
            (r'\}', Token.MatchingBracket.Other, '#pop'),
            include('comments'),
            include('strings'),
            (r'.', Token.MatchingBracket.Other)
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
            (r'///.*?\n', Comment.Single,
                ('#pop', 'comments-triple-slash')),
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single,
                ('#pop', 'comments-double-slash')),
            (r'/\*', Comment.Multiline, 'comments-block'),
            # include('comments'),
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'comments-triple-slash': [
            (r'.(?=\n)', Comment.Special, '#pop'),
            # A // breaks out of a comment for the rest of the line
            (r'//.*?(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'comments-double-slash': [
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'strings': [
            # `"compound string"'
            (r'`"', String.Other, 'string-compound'),
            # "string"
            (r'(?<!`)"', String.Double, 'string-regular'),
        ],
        'string-compound': [
            (r'`"', String.Other, '#push'),
            (r'"\'', String.Other, '#pop'),
            (r'.', String.Other)
        ],
        'string-regular': [
            (r'(")(?!\')|(?=\n)', String.Double, '#pop'),
            (r'.', String.Double)
        ]
    }
