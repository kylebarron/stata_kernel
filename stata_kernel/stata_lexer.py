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
    Token.SemicolonDelimiter: Delimiter (either \\n or ;), depending on the block

    For mata, we use:
        Token.Mata.Open
        Token.Mata.OpenError
        Token.Mata.Close
        Token.TextBlockParen

    If mata was opened with a colon, :, an error will close mata. We
    take into account when determining if mata was left open. Further,
    we make sure parenthesis behave as blocks, {}, to force the user to
    close them.
    """
    flags = re.MULTILINE | re.DOTALL
    tokens = {
        'root': [
            (r'`"', Text, 'string-compound'),
            (r'(?<!`)"', Text, 'string-regular'),
            (r'^[^\r\n\S]*m(ata)?[^\r\n\S]*$', Token.Mata.Open, 'mata'),
            (r'^[^\r\n\S]*m(ata)?[^\r\n\S]*:[^\r\n\S]*$', Token.Mata.OpenError, 'mata'),
            (r'\{', Token.TextBlock, 'block'),
            (r'^\s*(pr(ogram|ogra|ogr|og|o)?)\s+(?!di|dr|l)(de(fine|fin|fi|f)?\s+)?', Token.TextBlock, 'program'),
            (r'^\s*inp(u|ut)?', Token.TextBlock, 'program'),
            (r'.', Text),
        ],

        'mata': [
            include('strings'),
            (r'^[^\n]*?\{', Token.TextBlock, 'block'),
            (r'^[^\r\n]*?\(', Token.TextBlockParen, 'paren'),
            (r'[\r\n][^\r\n\S]*end(?=(\s|[^\s\w\.]).*?$|$)', Token.Mata.Close, '#pop'),
            (r'.', Text),
        ],
        'paren': [
            (r'\(', Token.TextBlockParen, '#push'),
            (r'\)[^\r\n]*?(?=\)|$|[\r\n])', Token.TextBlockParen, '#pop'),
            (r'\)[^\r\n]*?\(', Token.TextBlockParen),
            include('strings-inside-paren'),
            (r'.', Token.TextBlockParen)
        ],
        'strings-inside-paren': [
            # `"compound string"'
            (r'`"', Token.TextBlockParen, 'string-compound-inside-paren'),
            # "string"
            (r'(?<!`)"', Token.TextBlockParen, 'string-regular-inside-paren'),
        ],
        'string-compound-inside-paren': [
            (r'`"', Token.TextBlockParen, '#push'),
            (r'"\'', Token.TextBlockParen, '#pop'),
            (r'.', Token.TextBlockParen)
        ],
        'string-regular-inside-paren': [
            (r'(")(?!\')|(?=\n)', Token.TextBlockParen, '#pop'),
            (r'.', Token.TextBlockParen)
        ],

        'block': [
            (r'\{', Token.TextBlock, '#push'),
            (r'\}', Token.TextBlock, '#pop'),
            include('strings-inside-blocks'),
            (r'.', Token.TextBlock)
        ],
        'program': [
            include('strings-inside-blocks'),
            (r'^\s*end\b', Token.TextBlock, '#pop'),
            (r'.', Token.TextBlock)
        ],
        'strings': [
            # `"compound string"'
            (r'`"', Text, 'string-compound'),
            # "string"
            (r'(?<!`)"', Text, 'string-regular'),
        ],
        'strings-inside-blocks': [
            # `"compound string"'
            (r'`"', Token.TextBlock, 'string-compound-inside-blocks'),
            # "string"
            (r'(?<!`)"', Token.TextBlock, 'string-regular-inside-blocks'),
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
            (r'`"', Token.TextBlock, '#push'),
            (r'"\'', Token.TextBlock, '#pop'),
            (r'.', Token.TextBlock)
        ],
        'string-regular-inside-blocks': [
            (r'(")(?!\')|(?=\n)', Token.TextBlock, '#pop'),
            (r'.', Token.TextBlock)
        ],
    }


class CommentAndDelimitLexer(RegexLexer):
    """Lexer for Comments and Delimit blocks

    This lexer:
    - Removes all comments
    - Removes newlines from ;-delimited code and then replace ; with newlines
    - Determines the delimiter at the end of the block

    The StataLexer then uses the output of this lexer to form semantic blocks
    that can be sent through Stata.

    Notes:
    - If current delimiter is `;`, prepend `#delimit ;` to the input string before running this lexer.

    I have to use the Pygments token types, which don't really let me express what I want to express.

    Text: Arbitrary text
    Token.SemicolonDelimiter: Delimiter (either \\n or ;), depending on the block
    """
    flags = re.MULTILINE | re.DOTALL
    tokens = {
        'root': [
            include('comments'),
            include('strings'),
            (r'^\s*#d(e|el|eli|elim|elimi|elimit)?\s*;\s*?$', Comment.Single, 'delimit;'),
            (r'^[^\r\n\S]*m(ata)?[^\r\n\S]*$', Token.Mata.Open, 'mata'),
            (r'^[^\r\n\S]*m(ata)?[^\r\n\S]*:[^\r\n\S]*$', Token.Mata.OpenError, 'mata'),
            (r'.', Text),
        ],
        'mata': [
            # Just exclude linestar
            (r'(^//|(?<=\s)//)(?!/)', Comment.Single, 'comments-double-slash'),
            (r'/\*', Comment.Multiline, 'comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'comments-triple-slash'),
            include('strings'),
            (r'[\r\n][^\r\n\S]*end(?=(\s|[^\s\w\.]).*?$|$)', Token.Mata.Close, '#pop'),
            (r'.', Text),
        ],
        'mata-delimit': [
            # Just exclude linestar
            (r'((^\s+//)|(?<=\s)\s*//)(?!/)', Comment.Single, 'delimit;-comments-double-slash'),
            (r'/\*', Comment.Multiline, 'delimit;-comments-block'),
            (r'(^///|(?<=\s)///)', Comment.Special, 'delimit;-comments-triple-slash'),
            include('delimit;-strings'),
            (r'(?=^|;)\s*end(?=(\s|[^\s\w\.]).*?$|$)', Token.Mata.Close, '#pop'),
            (r';', Token.SemicolonDelimiter),
            (r'.', Token.TextInSemicolonBlock),
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
            (r'///.*?\n', Comment.Special,
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
            (r'(^//|(?<=\s)//)(?!/)[^\n]*', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'comments-double-slash': [
            (r'\n', Text, '#pop'),
            (r'.', Comment.Single),
        ],
        'strings': [
            # `"compound string"'
            (r'`"', Text, 'string-compound'),
            # "string"
            (r'(?<!`)"', Text, 'string-regular'),
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
        'delimit;': [
            (r'^\s*#d(e|el|eli|elim|elimi|elimit)?\s+cr\s*?$', Comment.Single, '#pop'),
            (r'(?=^|;)\s*m(ata)?\s*(?=;)', Token.Mata.Open, 'mata-delimit'),
            (r'(?=^|;)\s*m(ata)?\s*:\s*(?=;)', Token.Mata.OpenError, 'mata-delimit'),
            include('delimit;-comments'),
            include('delimit;-strings'),
            (r';', Token.SemicolonDelimiter),
            (r'.', Token.TextInSemicolonBlock),
        ],
        # Made changes for //, // inside of *, and ending character for *
        'delimit;-comments': [
            # Either after a ; delimiter or has whitespace after beginning of the line
            (r'((^\s+//)|(?<=\s)\s*//)(?!/)', Comment.Single, 'delimit;-comments-double-slash'),
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
            (r'///.*?\n', Comment.Special,
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
            (r'((^\s+//)|(?<=\s)\s*//)(?!/)[^\n]*', Comment.Single, '#pop'),
            (r'.', Comment.Special),
        ],
        'delimit;-comments-double-slash': [
            (r'\n', Token.TextInSemicolonBlock, '#pop'),
            (r'.', Comment.Single),
        ],
        'delimit;-strings': [
            # `"compound string"'
            (r'`"', Token.TextInSemicolonBlock, 'delimit;-string-compound'),
            # "string"
            (r'(?<!`)"', Token.TextInSemicolonBlock, 'delimit;-string-regular'),
        ],
        'delimit;-string-compound': [
            (r'`"', Token.TextInSemicolonBlock, '#push'),
            (r'"\'', Token.TextInSemicolonBlock, '#pop'),
            (r'.', Token.TextInSemicolonBlock)
        ],
        'delimit;-string-regular': [
            (r'(")(?!\')', Token.TextInSemicolonBlock, '#pop'),
            (r'.', Token.TextInSemicolonBlock)
        ]
    }
# yapf: enable
