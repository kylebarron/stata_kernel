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
            (r'^.*?\{', Token.MatchingBracket.Other, 'block'),
            (r'^\s*(pr(ogram|ogra|ogr|og|o)?)\s+(?!di|dr|l)(de(fine|fin|fi|f)?\s+)?', Token.MatchingBracket.Other, 'program'),
            (r'^\s*inp(u|ut)?', Token.MatchingBracket.Other, 'program'),
            (r'.', Text),
        ],
        'block': [
            (r'\{', Token.MatchingBracket.Other, '#push'),
            (r'\}', Token.MatchingBracket.Other, '#pop'),
            include('comments'),
            include('strings-inside-blocks'),
            (r'.', Token.MatchingBracket.Other)
        ],
        'comments': [
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single, 'comments-double-slash'),
            (r'^\s*\*', Comment.Single, 'comments-star'),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'comments-triple-slash')
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
            (r'\n', Comment.Special, '#pop'),
            # A // breaks out of a comment for the rest of the line
            (r'//.*?(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'comments-double-slash': [
            (r'.(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'program': [
            include('comments'),
            include('strings-inside-blocks'),
            (r'^\s*end\b', Token.MatchingBracket.Other, '#pop'),
            (r'.', Token.MatchingBracket.Other)
        ],
        'strings': [
            # `"compound string"'
            (r'`"', Text, 'string-compound'),
            # "string"
            (r'(?<!`)"', Text, 'string-regular'),
        ],
        'strings-inside-blocks': [
            # `"compound string"'
            (r'`"', Token.MatchingBracket.Other, 'string-compound-inside-blocks'),
            # "string"
            (r'(?<!`)"', Token.MatchingBracket.Other, 'string-regular-inside-blocks'),
        ],
        'string-compound': [
            (r'`"', Text, '#push'),
            (r'"\'', Text, '#pop'),
            (r'.', Text)
        ],
        'string-regular': [
            (r'(")(?!\')|(?=\n)', Text, '#pop'),
            (r'.', Text)
        ],
        'string-compound-inside-blocks': [
            (r'`"', Token.MatchingBracket.Other, '#push'),
            (r'"\'', Token.MatchingBracket.Other, '#pop'),
            (r'.', Token.MatchingBracket.Other)
        ],
        'string-regular-inside-blocks': [
            (r'(")(?!\')|(?=\n)', Token.MatchingBracket.Other, '#pop'),
            (r'.', Token.MatchingBracket.Other)
        ]
    }
