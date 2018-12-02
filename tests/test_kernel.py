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


    # Samples of code which generate a result value (ie, some text
    # displayed as Out[n])
    # code_execute_result = [
    #     {'code': 'di 6*7', 'result': '42\n\n'}
    # ]

    # Samples of code which should generate a rich display output, and
    # the expected MIME type
    # code_display_data = [
    #     {'code': 'sysuse auto\nscatter price mpg', 'mime': 'image/svg+xml'}
    # ]

    # You can also write extra tests. We recommend putting your kernel name
    # in the method name, to avoid clashing with any tests that
    # jupyter_kernel_test adds in the future.
    def test_stata_simple_display(self):
        self.flush_channels()
        reply, output_msgs = self.execute_helper(code='di "hi"')
        self.assertEqual(output_msgs[0]['header']['msg_type'], 'stream')
        self.assertEqual(output_msgs[0]['content']['name'], 'stdout')
        self.assertEqual(output_msgs[0]['content']['text'], 'hi\n')

    def test_stata_stdout(self):
        self._test_execute_stdout('di "hi"\ndi "bye"', 'hi\n\nbye')
        self._test_execute_stdout('di 6*7', '42')


    # def _test_display_data()

    def _test_execute_stdout(self, code, output):
        """
        This strings all output sent to stdout together and then checks that
        `code` is in `output`
        """
        self.flush_channels()
        reply, output_msgs = self.execute_helper(code=code)
        self.assertEqual(reply['content']['status'], 'ok')
        self.assertGreaterEqual(len(output_msgs), 1)

        all_output = []
        for msg in output_msgs:
            if (msg['msg_type'] == 'stream') and (msg['content']['name'] == 'stdout'):
                all_output.append(msg['content']['text'])
        self.assertIn(output, ''.join(all_output))


if __name__ == '__main__':
    unittest.main()
