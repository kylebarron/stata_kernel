from pygments import lex
from pygments.token import Token
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
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, ' '),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '*/'),
        (Token.Comment.Single, '\n')]
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
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '//'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, 'a'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
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
        (Token.Comment.Single, '//'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, 'a'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
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
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, ' '),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '*/'),
        (Token.Comment.Single, '\n')]
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
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '///\n'),
        (Token.Comment.Special, 'a'),
        (Token.Text, '\n')]
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
        (Token.Comment.Single, '//'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, '/'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, 'a'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
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
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, ' '),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, ' '),
        (Token.Comment.Multiline, '*/'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '*/*'),
        (Token.Comment.Multiline, ' '),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, 'a'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '*/'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_inline_comment_breaks_line_continuation_comment():
    """
    ```stata
    * Line continuation ///
    // Breaks line continuation ///
    di "Printed 1"
    ```
    """
    code = '* a ///\n// a ///\na'
    tokens = get_tokens(code)
    expected = [
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, 'a'),
        (Token.Comment.Single, ' '),
        (Token.Comment.Single, '///\n'),
        (Token.Comment.Single, '// a ///'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_inline_comment_breaks_line_continuation_comment2():
    """
    ```stata
    disp "Line continuation" ///
    // Breaks line continuation ///
    di "Printed 2"
    ```
    """
    code = 'a ///\n// a ///\na'
    tokens = get_tokens(code)
    expected = [
        (Token.Text, 'a'),
        (Token.Text, ' '),
        (Token.Comment.Special, '///\n'),
        (Token.Comment.Single, '// a ///'),
        (Token.Text, '\n'),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_multiline_comment_across_empty_whitespace_lines():
    """
    ```stata
    di /*

    */ "hi"
    ```
    """
    code = 'a /*\n\n*/ a'
    tokens = get_tokens(code)
    expected = [
        (Token.Text, 'a'),
        (Token.Text, ' '),
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '\n'),
        (Token.Comment.Multiline, '*/'),
        (Token.Text, ' '),
        (Token.Text, 'a'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_multiline_comment_inside_string():
    code = 'di "/*"'
    tokens = get_tokens(code)
    expected = [
        (Token.Text, 'd'),
        (Token.Text, 'i'),
        (Token.Text, ' '),
        (Token.Literal.String.Double, '"'),
        (Token.Literal.String.Double, '/'),
        (Token.Literal.String.Double, '*'),
        (Token.Literal.String.Double, '"'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_inline_comment_inside_string():
    code = 'di "//"'
    tokens = get_tokens(code)
    expected = [
        (Token.Text, 'd'),
        (Token.Text, 'i'),
        (Token.Text, ' '),
        (Token.Literal.String.Double, '"'),
        (Token.Literal.String.Double, '/'),
        (Token.Literal.String.Double, '/'),
        (Token.Literal.String.Double, '"'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_star_comment_inside_string():
    code = 'a "*"'
    tokens = get_tokens(code)
    expected = [
        (Token.Text, 'a'),
        (Token.Text, ' '),
        (Token.Literal.String.Double, '"'),
        (Token.Literal.String.Double, '*'),
        (Token.Literal.String.Double, '"'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_cap_chunk():
    code = 'cap {\n a\n}'
    tokens = get_tokens(code)
    expected = [
        (Token.MatchingBracket.Other, 'cap {'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, ' '),
        (Token.MatchingBracket.Other, 'a'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '}'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_cap_chunk_recursive():
    code = 'cap {\n{\n a\n}\n}'
    tokens = get_tokens(code)
    expected = [
        (Token.MatchingBracket.Other, 'cap {'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '{'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, ' '),
        (Token.MatchingBracket.Other, 'a'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '}'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '}'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_cap_chunk_with_inner_line_comment():
    code = 'cap {\n*{\n a\n}'
    tokens = get_tokens(code)
    expected = [
        (Token.MatchingBracket.Other, 'cap {'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.Comment.Single, '*'),
        (Token.Comment.Single, '{'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, ' '),
        (Token.MatchingBracket.Other, 'a'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '}'),
        (Token.Text, '\n')]
    assert tokens == expected

def test_cap_chunk_with_inner_multiline_comment():
    code = 'cap {\n/*{*/\n a\n}'
    tokens = get_tokens(code)
    expected = [
        (Token.MatchingBracket.Other, 'cap {'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.Comment.Multiline, '/*'),
        (Token.Comment.Multiline, '{'),
        (Token.Comment.Multiline, '*/'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, ' '),
        (Token.MatchingBracket.Other, 'a'),
        (Token.MatchingBracket.Other, '\n'),
        (Token.MatchingBracket.Other, '}'),
        (Token.Text, '\n')]
    assert tokens == expected
