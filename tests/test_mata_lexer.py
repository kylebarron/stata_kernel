import pytest
from pygments.token import Token
from stata_kernel.code_manager import CodeManager


# yapf: disable
class TestCommentsFromMataList(object):
    """
    Tests derived from
    https://www.statalist.org/forums/forum/general-stata-discussion/general/1448244-understanding-stata-s-comment-hierarchy
    """

    def test_multiline_comment(self):
        """
        ```stata
        mata
        /* This will be a multi-line comment
        printf("Not printed\n")
        */
        end
        ```
        """
        code = 'mata\n/*a\na\n*/\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_ignored_multiline_after_inline_comment(self):
        """
        ```stata
        mata
        // /* Ignored due to inline comment
        printf("Printed 2\n")
        end
        ```
        """
        code = 'mata\n// /*a\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, 'a'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_comment_after_pointer(self):
        """
        ```stata
        mata
        *&1 /* Comment after star
        printf("Not printed\n")
        */
        end
        ```
        """
        code = 'mata\n*&1 /*a\na\n*/\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, '*'),
            (Token.Text, '&'),
            (Token.Text, '1'),
            (Token.Text, ' '),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_line_continuation(self):
        """
        ```stata
        mata
        a = 1
        b = &a
        *b ///
        = 2
        a
        end
        ```
        """
        code = 'mata\na=1\nb=&a\n*b ///\n=2\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '='),
            (Token.Text, '1'),
            (Token.Text, '\n'),
            (Token.Text, 'b'),
            (Token.Text, '='),
            (Token.Text, '&'),
            (Token.Text, 'a'),
            (Token.Text, '\n'),
            (Token.Text, '*'),
            (Token.Text, 'b'),
            (Token.Text, ' '),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Text, '='),
            (Token.Text, '2'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_line_continuation_ignored_after_inline_comment(self):
        """
        ```stata
        mata
        // /// Line continuation ignored due to inline comment
        printf("Printed 3\n")
        end
        ```
        """
        code = 'mata\n// /// a\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_nesting_of_multiline_comments(self):
        """
        ```stata
        mata
        /*
        /* Nested */
        disp "Not printed"
        */* disp "Not printed"
        disp "Not printed"
        */
        printf("printed\n")
        end
        ```
        """
        code = 'mata\n/*\n/* a */\na\n*/* a\na\n*/\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
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
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_inline_comment_breaks_line_continuation_comment(self):
        """
        ```stata
        a = 1 ///
        // Breaks line continuation ///
        1
        ```
        """
        code = 'mata\na=1 ///\n// a ///\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '='),
            (Token.Text, '1'),
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
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestMultilineCommentsMata(object):
    def test_multiline_comment_across_empty_whitespace_lines(self):
        """
        ```stata
        mata /*

        */ 1
        mata
        /*

        */
        end
        ```
        """
        code = 'mata /*\n\n*/ 1\nmata\n/*\n\n*/\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Text, 'm'),
            (Token.Text, 'a'),
            (Token.Text, 't'),
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Text, ' '),
            (Token.Text, '1'),
            (Token.Text, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestLineContinuationCommentsMata(object):
    def test1(self):
        code = 'mata:\na ///\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test2(self):
        code = 'mata:\na///\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test3(self):
        code = 'mata:\n///\na\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'a'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test4(self):
        code = 'mata:\na ///\n/// a ///\nend\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, '\n'),
            (Token.Comment.Special, '///'),
            (Token.Comment.Special, ' '),
            (Token.Comment.Special, 'a'),
            (Token.Comment.Special, ' '),
            (Token.Comment.Special, '/'),
            (Token.Comment.Special, '/'),
            (Token.Comment.Special, '/'),
            (Token.Comment.Special, '\n'),
            (Token.Text, 'e'),
            (Token.Text, 'n'),
            (Token.Text, 'd'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test5(self):
        code = 'mata:\na ///\n// a ///\n\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
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
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestSingleLineCommentsMata(object):
    def test1(self):
        code = 'mata\nx=//*\n*/1'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, 'x'),
            (Token.Text, '='),
            (Token.Text, '/'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, '*/'),
            (Token.Text, '1'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test2(self):
        code = 'mata:\n//\n'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestStringsMata(object):
    def test_multiline_comment_inside_string(self):
        code = 'mata\n"/*"\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, '"'),
            (Token.Text, '/'),
            (Token.Text, '*'),
            (Token.Text, '"'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_string(self):
        code = 'mata\n"//"\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, '"'),
            (Token.Text, '/'),
            (Token.Text, '/'),
            (Token.Text, '"'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_star_comment_inside_string(self):
        code = 'mata\na "*"\nend'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, '*'),
            (Token.Text, '"'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestBlocksMata(object):
    def test_multiple_mata_blocks(self):
        code = 'mata\nmata\nmata:\nend\nmata:'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.Text, 'm'),
            (Token.Text, 'a'),
            (Token.Text, 't'),
            (Token.Text, 'a'),
            (Token.Text, '\n'),
            (Token.Text, 'm'),
            (Token.Text, 'a'),
            (Token.Text, 't'),
            (Token.Text, 'a'),
            (Token.Text, ':'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n'),
            (Token.Mata.OpenError, 'mata:'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_paren_chunk(self):
        code = 'mata\n(\n 1\n)\nend'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlockParen, '('),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ' '),
            (Token.TextBlockParen, '1'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ')'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_paren_chunk_recursive(self):
        code = 'mata\n(\n(\n a\n)\n)\nend'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlockParen, '('),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, '('),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ' '),
            (Token.TextBlockParen, 'a'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ')'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ')'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_cap_chunk_with_inner_line_comment(self):
        code = 'mata\n(\n//(\n a\n)\nend'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlockParen, '('),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ' '),
            (Token.TextBlockParen, 'a'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ')'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_cap_chunk_with_inner_multiline_comment(self):
        code = 'mata\n(\n/*(*/\n a\n)\nend'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlockParen, '('),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ' '),
            (Token.TextBlockParen, 'a'),
            (Token.TextBlockParen, '\n'),
            (Token.TextBlockParen, ')'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_if_block_not_matching_preceding_newline(self):
        code = 'mata\n1 if {\na\n}\nend'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlock, '1 if {'),
            (Token.TextBlock, '\n'),
            (Token.TextBlock, 'a'),
            (Token.TextBlock, '\n'),
            (Token.TextBlock, '}'),
            (Token.Mata.Close, '\nend'),
            (Token.Text, '\n')]
        assert tokens == expected

    def test_if_block_with_preceding_string(self):
        """ GH issue 139 """
        code = 'mata\nif ("0" == "1") {'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, 'mata'),
            (Token.Text, '\n'),
            (Token.TextBlock, 'if ("0" == "1") {'),
            (Token.TextBlock, '\n')]
        assert tokens == expected


class TestSemicolonDelimitCommentsMata(object):
    def test_inline_comment(self):
        """
        ```stata
        #delimit ;
        mata;
        // This line is ignored, but the line break is not
        "Printed 1";
        end;
        ```
        """
        code = '#delimit ;\nmata;\n// a\na;\nend;'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Comment.Single, '#delimit ;'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, 'a'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Close, 'end'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n')]
        assert tokens == expected

    def test_multiline_comment_after_inline_comment(self):
        """
        ```stata
        mata;
        #delimit ;
        // Same for multi-line /*
        "Printed 2";
        end;
        ```
        """
        code = '#delimit ;\nmata;\n// /* a\na;\nend;'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Comment.Single, '#delimit ;'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, '/'),
            (Token.Comment.Single, '*'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'a'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, 'a'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Close, 'end'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n')]
        assert tokens == expected

    def test_multiline_comment_after_star(self):
        """
        ```stata
        #delimit ;
        mata;
        /* multi-line
        "Not printed"  */;
        end;
        ```
        """
        code = '#delimit ;\nmata;\n/* a\na; */;'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Comment.Single, '#delimit ;'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Comment.Multiline, '/*'),
            (Token.Comment.Multiline, ' '),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, '\n'),
            (Token.Comment.Multiline, 'a'),
            (Token.Comment.Multiline, ';'),
            (Token.Comment.Multiline, ' '),
            (Token.Comment.Multiline, '*/'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_expr_with_whitespace(self):
        """
        ```stata
        #delimit ;
        mata;
        "Line start",
         // This is ignored, and does not give error
        "; Line end" ;
        end;
        ```
        """
        code = '#delimit ;\nmata;\n"a",\n // c\n"; b";\nend;'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Comment.Single, '#delimit ;'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, 'a'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, ','),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Comment.Single, ' //'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'c'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, ';'),
            (Token.TextInSemicolonBlock, ' '),
            (Token.TextInSemicolonBlock, 'b'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Close, 'end'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n')]
        assert tokens == expected

    def test_inline_comment_inside_expr_without_whitespace(self):
        """
        Stata does not give this error in mata. This code runs OK.
        ```stata
        #delimit ;
        mata;
        "Line start",
        // This is ignored, and does not give error
        "; Line end" ;
        end;
        ```
        """
        code = '#delimit ;\nmata;\n"a",\n// c\n"; b";\nend;'
        tokens = CodeManager(code).tokens_fp_all
        expected = [
            (Token.Comment.Single, '#delimit ;'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Open, 'mata'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, 'a'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, ','),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Comment.Single, '//'),
            (Token.Comment.Single, ' '),
            (Token.Comment.Single, 'c'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.TextInSemicolonBlock, ';'),
            (Token.TextInSemicolonBlock, ' '),
            (Token.TextInSemicolonBlock, 'b'),
            (Token.TextInSemicolonBlock, '"'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n'),
            (Token.Mata.Close, 'end'),
            (Token.SemicolonDelimiter, ';'),
            (Token.TextInSemicolonBlock, '\n')]
        assert tokens == expected

    def test_newlines_in_semicolon_block_become_spaces(self):
        """
        This actually fails in mata
        ```stata
        #delimit ;
        mata;
        "
        a
        2
        b
        "
        ;
        end;
        ```
        """
        code = '#delimit ;\nmata;\n"\na\n2\nb\n"\n;\nend;'
        tokens = CodeManager(code).tokens_final
        expected = [
            (Token.Mata.Open, ' mata'),
            (Token.Text, '\n'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, ' '),
            (Token.Text, 'a'),
            (Token.Text, ' '),
            (Token.Text, '2'),
            (Token.Text, ' '),
            (Token.Text, 'b'),
            (Token.Text, ' '),
            (Token.Text, '"'),
            (Token.Text, ' '),
            (Token.Mata.Close, '\n end'),
            (Token.Text, '\n')]
        assert tokens == expected


class TestIsCompleteMata(object):
    @pytest.mark.parametrize(
        'code,complete',
        [
            ('mata\n//',        True),
            ('mata\n// sdfsa',  True),
            ('mata\n/// sdfsa', False),
            ('mata\n/// \n',    False),
            ('mata\n/// \n\n',  True),
            ('mata\n/* \n\n',   False),
            ('mata\n/* \n\n*/', True),
        ]
    )  # yapf: disable
    def test_is_comment_complete(self, code, complete):
        assert CodeManager(code, False).is_complete == complete

    @pytest.mark.parametrize(
        'code,complete',
        [
            ('mata;\n//',               True),
            ('mata;\n// sdfsa',         True),
            ('mata;\n/// sdfsa',        False),
            ('mata;\n/// \n',           False),
            ('mata;\n/// \n\n',         True),
            ('mata;\n/// \n;',          True),
            ('mata;\n/// \n\n;',        True),
            ('mata;\n/* \n\n',          False),
            ('mata;\n/* \n\n*/',        True),
            ('mata;\n/* \n\n*/ di hi;', True),
            ('mata;\n/* \n\n*/;',       True),
        ]
    )  # yapf: disable
    def test_is_comment_complete_in_sc_delimit_block(self, code, complete):
        assert CodeManager(code, True).is_complete == complete

    @pytest.mark.parametrize(
        'code,complete',
        [
            ('mata\n1',                                  True),
            ('mata\n;',                                  True),
            ('mata\nfor (i = 1; i<=10; i++) {}',         True),
            ('mata\nfor (i = 1; i<=10; i++) {',          False),
            ('mata\nwhile (0) {\nif (1) {\n} else {\n}', False),
            ('mata\n"hi"; // seems fine',                True),
            ('mata\n"hi" // seems fine',                 True),
            ('mata\nif ("0" == "1") {',                  False),
            ('mata\nif ("0" == "1") {\n"hi"\n}',         True),
        ]
    )  # yapf: disable
    def test_is_block_complete(self, code, complete):
        assert CodeManager(code, False).is_complete == complete

    @pytest.mark.parametrize(
        'code,complete',
        [
            ('mata;\n1',                               False),
            ('mata;\n1;',                              True),
            ('mata;\n;',                               True),
            ('mata;\nfor (i = 1; i<=10; i++)',         False),  # for gets messed up
            ('mata;\n"hi"; // seems fine',             True),
            ('mata;\n"hi" // seems fine',              False),
            ('mata;\nif ("0" == "1") {;',              False),
            ('mata;\nif ("0" == "1") {;\n"hi";\n};',   True),
            ('mata;\nif ("1" == "1") {;"hi";};',       True),
        ]
    )  # yapf: disable
    def test_is_block_complete_in_sc_delimit_block(self, code, complete):
        assert CodeManager(code, True).is_complete == complete

# yapf: enable
