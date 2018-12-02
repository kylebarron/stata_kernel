import unittest
import jupyter_kernel_test


class MyKernelTests(jupyter_kernel_test.KernelTests):
    # Required --------------------------------------

    # The name identifying an installed kernel to run the tests against
    kernel_name = 'stata'

    # language_info.name in a kernel_info_reply should match this
    language_name = 'stata'

    # Optional --------------------------------------

    # Code in the kernel's language to write "hello, world" to stdout
    code_hello_world = 'display "hello, world"'

    # Pager: code that should display something (anything) in the pager
    # code_page_something = "help(something)"

    # samples for the autocompletion functionality
    # for each dictionary, `text` is the input to try and complete, and
    # `matches` the list of all complete matching strings which should be found
    completion_samples = [
        {
            'text': 'di $S',
            'matches': {'S_ADO', 'S_level', 'S_StataSE', 'S_CONSOLE', 'S_FLAVOR', 'S_OS', 'S_MACH'}
        },
        {
            'text': 'di ${S',
            'matches': {'S_ADO', 'S_level', 'S_StataSE', 'S_CONSOLE', 'S_FLAVOR', 'S_OS', 'S_MACH'}
        },
        {
            'text': 'use tests/test_data/',
            'matches': {'tests/test_data/auto.dta'}
        },
    ]

    # Samples of code which should generate a rich display output, and
    # the expected MIME type
    # code_display_data = [
    #     {'code': 'sysuse auto\nscatter price mpg', 'mime': 'image/svg+xml'}
    # ]

    def test_stata_stdout(self):
        self._test_execute_stdout('di "hi"\ndi "bye"', 'hi\n\nbye')
        self._test_execute_stdout('di 6*7', '42')

    def test_stata_display_data(self):
        self._test_display_data('scatter price mpg', 'text/html')
        self._test_display_data('scatter price mpg', 'image/svg+xml')
        self._test_display_data('scatter price mpg', 'application/pdf')

    def test_stata_more(self):
        self._test_execute_stdout('more', '--more--', exact=True)

    def test_stata_display_unicode_letter(self):
        """https://github.com/kylebarron/stata_kernel/issues/196"""
        code = """\
        local a "ä"
        di "`a'"\
        """
        self._test_execute_stdout(code, 'ä', exact=True)

    def test_stata_scatter_regex(self):
        """https://github.com/kylebarron/stata_kernel/issues/205"""
        self._test_display_data('sc price mpg', 'image/svg+xml')
        self._test_display_data('scatter price mpg', 'image/svg+xml')


    def _test_display_data(self, code, mimetype, _not=False):
        reply, output_msgs = self._run(code=code)
        self.assertEqual(reply['content']['status'], 'ok')
        self.assertGreaterEqual(len(output_msgs), 1)
        self.assertEqual(output_msgs[0]['msg_type'], 'display_data')
        self.assertIn(mimetype, output_msgs[0]['content']['data'])

    def _test_execute_stdout(self, code, output, exact=False):
        """
        This strings all output sent to stdout together and then checks that
        `code` is in `output`
        """
        reply, output_msgs = self._run(code=code)
        self.assertEqual(reply['content']['status'], 'ok')
        self.assertGreaterEqual(len(output_msgs), 1)

        all_output = []
        for msg in output_msgs:
            if (msg['msg_type'] == 'stream') and (msg['content']['name'] == 'stdout'):
                all_output.append(msg['content']['text'])
        all_output = ''.join(all_output).strip()
        if exact:
            self.assertEqual(output, all_output)
        else:
            self.assertIn(output, all_output)

    def _run(self, code, dataset='auto', **kwargs):
        """Wrapper to run arbitrary code in the Stata kernel
        """
        self.flush_channels()
        self.execute_helper(f'sysuse {dataset}, clear')
        return self.execute_helper(code=code, **kwargs)



if __name__ == '__main__':
    unittest.main()
