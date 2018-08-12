from pygments import lex
from pygments.token import Token
from stata_kernel.stata_lexer import StataLexer

def get_tokens(code):
    lexer = StataLexer(stripall=True)
    return [x for x in lex(code, lexer)]

class TestCommentsFromStataList(object):
    """
    Tests derived from
    https://www.statalist.org/forums/forum/general-stata-discussion/general/1448244-understanding-stata-s-comment-hierarchy
    """

    def test_multiline_comment_after_star(self):
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

    def test_ignored_multiline_after_inline_comment_after_star_comment(self):
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

    def test_ignored_multiline_after_inline_comment(self):
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

    def test_inline_comment_needs_preceding_whitespace(self):
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

    def test_line_continuation_comment_after_star_comment(self):
        """
        ```stata
        * ///
        disp "Not printed. Line continuation applies"
        ```
        """
        code = '* ///\na\na'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '///\n'),
            (Token.Comment.Special, 'a'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_line_continuation_ignored_after_inline_comment(self):
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

    def test_nesting_of_multiline_comments(self):
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

    def test_inline_comment_breaks_line_continuation_comment(self):
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

    def test_inline_comment_breaks_line_continuation_comment2(self):
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
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '/'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestMultilineComments(object):
    def test_multiline_comment_across_empty_whitespace_lines(self):
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

    def test_multiline1(self):
        code = 'a/* a */a'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'a'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, ' '),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, ' '),
            (Token.Comment.Multiline, '*/'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestLineContinuationComments(object):
    def test1(self):
        code = 'a ///\na'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test2(self):
        code = 'a///\na'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'a'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test3(self):
        code = '///\na'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestSingleLineComments(object):
    def test1(self):
        code = 'di//*\n*/1'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'd'),
            (Token.Text, 'i'),
            (Token.Text, '/'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Text, '1'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test2(self):
        code = '//\n'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '//'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestStrings(object):
    def test_multiline_comment_inside_string(self):
        code = 'di "/*"'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'd'),
            (Token.Text, 'i'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, '/'),
            (Token.Text, '*'),
            (Token.Text, '"'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_string(self):
        code = 'di "//"'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'd'),
            (Token.Text, 'i'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '"'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_star_comment_inside_string(self):
        code = 'a "*"'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, '*'),
            (Token.Text, '"'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestBlocks(object):
    def test_cap_chunk(self):
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

    def test_cap_chunk_recursive(self):
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

    def test_cap_chunk_with_inner_line_comment(self):
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

    def test_cap_chunk_with_inner_multiline_comment(self):
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

    def test_if_block_not_matching_preceding_newline(self):
        code = 'di 1\nif {\na\n}'
        tokens = get_tokens(code)
        expected = [
            (Token.Text, 'd'),
            (Token.Text, 'i'),
            (Token.Text, ' '),
            (Token.Text, '1'),
            (Token.Text, '\n'),
            (Token.MatchingBracket.Other, 'if {'),
            (Token.MatchingBracket.Other, '\n'),
            (Token.MatchingBracket.Other, 'a'),
            (Token.MatchingBracket.Other, '\n'),
            (Token.MatchingBracket.Other, '}'),
            (Token.Text, '\n')]
        assert tokens == expected

class TestSemicolonDelimitComments(object):
    def test_inline_comment(self):
        """
        ```stata
        #delimit ;
        // This line is ignored, but the line break is not
        di "Printed 1";
        ```
        """
        code = '#delimit ;\n// a\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected

    def test_multiline_comment_after_inline_comment(self):
        """
        ```stata
        #delimit ;
        // Same for multi-line /*
        di "Printed 2";
        ```
        """
        code = '#delimit ;\n// /* a\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected

    def test_star_comment(self):
        """
        ```stata
        #delimit ;
        * Line continuations do apply
        di "Not printed";
        ```
        """
        code = '#delimit ;\n* a\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Comment.Single, '\n'),
            (Token.Comment.Single, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected

    def test_multiline_comment_after_star(self):
        """
        ```stata
        #delimit ;
        * Same for multi-line /*
        di "Not printed"  */;
        ```
        """
        code = '#delimit ;\n* /* a\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, ' '),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, ';'),
            (Token.Comment.Multiline, '\n')]
        assert tokens == expected

    def test_inline_comment_after_star_comment(self):
        """
        ```stata
        #delimit ;
        * Line continuation
        // Does not break line continuation
        di "Not printed";
        ```
        """
        code = '#delimit ;\n* // a\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Comment.Single, '\n'),
            (Token.Comment.Single, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_expr_with_whitespace(self):
        """
        ```stata
        #delimit ;
        disp "Line start"
         // This is ignored, and does not give error
        "; Line end" ;
        ```
        """
        code = '#delimit ;\na\n // c\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Comment.Single, ' //'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'c'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_expr_without_whitespace(self):
        """
        ```stata
        #delimit ;
        disp "Line start"
        // This is ignored, and does not give error
        "; Line end" ;
        ```
        """
        code = '#delimit ;\na\n// c\na;'
        tokens = get_tokens(code)
        expected = [
            (Token.Comment.Single, '#delimit ;\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Keyword.Namespace, '/'),
            (Token.Keyword.Namespace, '/'),
            (Token.Keyword.Namespace, ' '),
            (Token.Keyword.Namespace, 'c'),
            (Token.Keyword.Namespace, '\n'),
            (Token.Keyword.Namespace, 'a'),
            (Token.Keyword.Reserved, ';'),
            (Token.Keyword.Namespace, '\n')]
        assert tokens == expected
