import re
from pygments.lexer import RegexLexer, include
from pygments.token import Comment, Text, Token


# yapf: disable
class StataLexer(RegexLexer):
    """Modified Pygments Stata Lexer

    I only need accurate handling of comment, string, and line-continuation
    environments.

    When in #delimit ; mode, always add #delimit ; to the first line, then run
    through this same lexer.

    I have to use the Pygments token types, which don't really let me express what I want to express.

    Make a `delimiter` type. Then mark `\\n` and `;` as the delimiter in the respective zones. Then I can use the standard Text or Block keywords in both places. Take out any \\n from Token.Text first, because that's a newline in the ;-delimited block.

    For #delimit; text, do two passes, once to remove comments. Then take out ; and extra text \\n and put in delimiting \\n. Then put through once more to find blocks.

    Text: Arbitrary text
    Token.Keyword.Reserved: Delimiter (either \\n or ;), depending on the block

    Token.Other is used to detect mata
    """
    flags = re.MULTILINE | re.DOTALL
    tokens = {
        'root': [
            include('comments'),
            include('strings'),
            (r'^\s*m(ata)?[^\r\n\S]*:?[^\r\n\S]*$', Token.Other, 'mata'),
            (r'^[^\n]*?\{', Token.MatchingBracket.Other, 'block'),
            (r'^\s*(pr(ogram|ogra|ogr|og|o)?)\s+(?!di|dr|l)(de(fine|fin|fi|f)?\s+)?', Token.MatchingBracket.Other, 'program'),
            (r'^\s*inp(u|ut)?', Token.MatchingBracket.Other, 'program'),
            (r'^\s*#d(e|el|eli|elim|elimi|elimit)?\s*;\s*?$', Comment.Single, 'delimit;'),
            (r'.', Text),
        ],

        'mata': [
            ('^\s*end(\s|[^\s\w\.]).*?$', Token.Other, '#pop'),
            include('mata-comments'),
            include('strings'),
            (r'[\r\n]\s*end(?=(\s|[^\s\w\.]).*?$|$)', Token.Keyword.Reserved),
            (r'^[^\n]*?\{', Token.MatchingBracket.Other, 'block'),
            (r'^\s*#d(e|el|eli|elim|elimi|elimit)?\s*;\s*?$', Comment.Single, 'delimit;'),
            (r'.', Text),
        ],
        'mata-comments': [
            # Just exclude linestar
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single, 'comments-double-slash'),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'comments-triple-slash')
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
            (r'\n', Text, '#pop'),
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
        ],

        'delimit;': [
            (r'^\s*#d(e|el|eli|elim|elimi|elimit)?\s+cr\s*?$', Comment.Single, '#pop'),
            include('delimit;-comments'),
            include('delimit;-strings'),
            (r';', Token.Keyword.Reserved),
            (r'.', Token.Keyword.Namespace),
        ],
        # Made changes for //, // inside of *, and ending character for *
        'delimit;-comments': [
            # Either after a ; delimiter or has whitespace after beginning of the line
            (r'((^\s+//)|(?<=;\s)\s*//)(?!/)', Comment.Single, 'delimit;-comments-double-slash'),
            (r'^\s*\*', Comment.Single, 'delimit;-comments-star'),
            (r'/\*', Comment.Multiline, 'delimit;-comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'delimit;-comments-triple-slash')
        ],
        'delimit;-comments-block': [
            (r'/\*', Comment.Multiline, '#push'),
            # this ends and restarts a comment block. but need to catch this so
            # that it doesn\'t start _another_ level of comment blocks
            (r'\*/\*', Comment.Multiline),
            (r'(\*/\s+\*(?!/)[^\n]*)|(\*/)', Comment.Multiline, '#pop'),
            # Match anything else as a character inside the comment
            (r'.', Comment.Multiline),
        ],
        'delimit;-comments-star': [
            (r'///.*?\n', Comment.Single,
                ('#pop', 'delimit;-comments-triple-slash')),
            # // doesn't break out of star comment inside #delimit ;
            (r'/\*', Comment.Multiline, 'delimit;-comments-block'),
            # ; ends a * comment
            (r'.(?=;)', Comment.Single, '#pop'),
            (r'.', Comment.Single),
        ],
        'delimit;-comments-triple-slash': [
            (r'\n', Comment.Special, '#pop'),
            # A // breaks out of a comment for the rest of the line
            (r'//.*?(?=\n)', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'delimit;-comments-double-slash': [
            (r'\n', Token.Keyword.Namespace, '#pop'),
            (r'.', Comment.Single),
        ],
        'delimit;-strings': [
            # `"compound string"'
            (r'`"', Token.Keyword.Namespace, 'delimit;-string-compound'),
            # "string"
            (r'(?<!`)"', Token.Keyword.Namespace, 'delimit;-string-regular'),
        ],
        'delimit;-string-compound': [
            (r'`"', Token.Keyword.Namespace, '#push'),
            (r'"\'', Token.Keyword.Namespace, '#pop'),
            (r'.', Token.Keyword.Namespace)
        ],
        'delimit;-string-regular': [
            (r'(")(?!\')|(?=\n)', Token.Keyword.Namespace, '#pop'),
            (r'.', Token.Keyword.Namespace)
        ],

    }
# yapf: enable
