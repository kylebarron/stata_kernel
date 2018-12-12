import unittest
import jupyter_kernel_test

from stata_kernel.config import Config


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
        # Path completion
        {
            'text': 'use tests/test_data/',
            'matches': {'tests/test_data/auto.dta'}
        },
        # Magics
        {
            'text': '%',
            'matches': {'browse', 'delimit', 'globals', 'head', 'help',
                        'hide_gui', 'locals', 'set', 'show_gui', 'status',
                        'tail'}
        },
        {
            'text': '%b',
            'matches': {'browse'}
        },
        {
            'text': '%set ',
            'matches': set(Config().all_settings)
        },
        {
            'text': '%set au',
            'matches': {x for x in Config().all_settings if x.startswith('au')}
        }
    ] # yapf: disable

    # Samples of code which should generate a rich display output, and
    # the expected MIME type
    # code_display_data = [
    #     {'code': 'sysuse auto\nscatter price mpg', 'mime': 'image/svg+xml'}
    # ]

    def test_stata_path_completion(self):
        text = 'use "'
        matches = {
            'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE', 'MANIFEST.in',
            'README.md'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion1(self):
        text = 'use "'
        self._test_completion(text)

    def test_stata_path_completion2(self):
        text = 'use "./'
        matches = {
            './CHANGELOG.md', './CONTRIBUTING.md', './LICENSE', './MANIFEST.in',
            './README.md'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion3(self):
        text = 'use "./CHANGE'
        matches = {'./CHANGELOG.md'}
        self._test_completion(text, matches, exact=True)

    def test_stata_path_completion4(self):
        text = 'use "./stata_kernel/'
        matches = {'./stata_kernel/completions.py', './stata_kernel/code_manager.py', './stata_kernel/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion5(self):
        text = 'use "./stata_kernel/c'
        matches = {'./stata_kernel/completions.py', './stata_kernel/code_manager.py', './stata_kernel/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_varlist_completion(self):
        self._run()
        text = 'list '
        matches = [
            'make', 'price', 'mpg', 'rep78', 'headroom', 'trunk', 'weight',
            'length', 'turn', 'displacement', 'gear_ratio', 'foreign']
        self._test_completion(text, matches, exact=False)

    def test_stata_varlist_completion1(self):
        self._run()
        text = 'list m'
        matches = ['make', 'mpg']
        self._test_completion(text, matches, exact=False)

    def _test_completion(self, text, matches=None, exact=True):
        msg_id = self.kc.complete(text)
        reply = self.kc.get_shell_msg()
        jupyter_kernel_test.messagespec.validate_message(
            reply, 'complete_reply', msg_id)
        if matches is not None:
            if exact:
                self.assertEqual(set(reply['content']['matches']), set(matches))
            else:
                self.assertTrue(
                    set(matches) <= set(reply['content']['matches']))
        else:
            self.assertFalse(None)

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
            if (msg['msg_type'] == 'stream') and (
                    msg['content']['name'] == 'stdout'):
                all_output.append(msg['content']['text'])
        all_output = ''.join(all_output).strip()
        if exact:
            self.assertEqual(output, all_output)
        else:
            self.assertIn(output, all_output)

    def _run(self, code=None, dataset='auto', **kwargs):
        """Wrapper to run arbitrary code in the Stata kernel
        """
        self.flush_channels()
        res = self.execute_helper(f'sysuse {dataset}, clear')
        if code is not None:
            res = self.execute_helper(code=code, **kwargs)
        return res


if __name__ == '__main__':
    unittest.main()
