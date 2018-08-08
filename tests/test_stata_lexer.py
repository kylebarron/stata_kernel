from pygments import lex
from pygments.token import Comment, String, Text
from stata_kernel.stata_lexer import StataLexer

def get_tokens(code):
    lexer = StataLexer(stripall=True)
    return [x for x in lex(code, lexer)]

def test_multiline_comment_after_star():
    """
    ```stata
    * /* This will be a multi-line comment
    disp "Not printed"
    */
    ```
    """
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

def test_ignored_multiline_after_inline_comment_after_star_comment():
    """
    ```stata
    * // /* Ignored due to inline comment
    disp "Printed 1"
    ```
    """
    code = '* // /* a\na'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '*'),
        (Comment.Single, ' '),
        (Comment.Single, '//'),
        (Comment.Single, ' '),
        (Comment.Single, '/'),
        (Comment.Single, '*'),
        (Comment.Single, ' '),
        (Comment.Single, 'a'),
        (Text, '\n'),
        (Text, 'a'),
        (Text, '\n')]
    assert tokens == expected

def test_ignored_multiline_after_inline_comment():
    """
    ```stata
    // /* Also ignored due to inline comment
    disp "Printed 2"
    ```
    """
    code = '// /* a\na'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '//'),
        (Comment.Single, ' '),
        (Comment.Single, '/'),
        (Comment.Single, '*'),
        (Comment.Single, ' '),
        (Comment.Single, 'a'),
        (Text, '\n'),
        (Text, 'a'),
        (Text, '\n')]
    assert tokens == expected

def test_inline_comment_needs_preceding_whitespace():
    """
    ```stata
    *// /* This is not an inline comment, so this is multi-line again
    disp "Not printed"
    */
    ```
    """
    code = '*// /* a\na\n*/'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '*'),
        (Comment.Single, '/'),
        (Comment.Single, '/'),
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

def test_line_continuation_comment_after_star_comment():
    """
    ```stata
    * ///
    disp "Not printed. Line continuation applies"
    ```
    """
    code = '* ///\na'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '*'),
        (Comment.Single, ' '),
        (Comment.Single, '///\n'),
        (Comment.Special, 'a'),
        (Comment.Single, '\n')]
    assert tokens == expected

def test_line_continuation_ignored_after_inline_comment():
    """
    ```stata
    // /// Line continuation ignored due to inline comment
    disp "Printed 3"
    ```
    """
    code = '// /// a\na'
    tokens = get_tokens(code)
    expected = [
        (Comment.Single, '//'),
        (Comment.Single, ' '),
        (Comment.Single, '/'),
        (Comment.Single, '/'),
        (Comment.Single, '/'),
        (Comment.Single, ' '),
        (Comment.Single, 'a'),
        (Text, '\n'),
        (Text, 'a'),
        (Text, '\n')]
    assert tokens == expected

def test_nesting_of_multiline_comments():
    """
    ```stata
    /*
    /* Nested */
    disp "Not printed"
    */* disp "Not printed"
    disp "Not printed"
    */
    di "printed"

    ```
    """
    code = '/*\n/* a */\na\n*/* a\na\n*/\na'
    tokens = get_tokens(code)
    expected = [
        (Comment.Multiline, '/*'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, '/*'),
        (Comment.Multiline, ' '),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, ' '),
        (Comment.Multiline, '*/'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, '*/*'),
        (Comment.Multiline, ' '),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, 'a'),
        (Comment.Multiline, '\n'),
        (Comment.Multiline, '*/'),
        (Text, '\n'),
        (Text, 'a'),
        (Text, '\n')]
    assert tokens == expected
