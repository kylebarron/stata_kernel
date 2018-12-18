import jupyter_kernel_test


class StataKernelTestFramework(jupyter_kernel_test.KernelTests):
    # The name identifying an installed kernel to run the tests against
    kernel_name = 'stata'

    # language_info.name in a kernel_info_reply should match this
    language_name = 'stata'

    def _test_completion(self, text, matches=None, exact=True):
        msg_id = self.kc.complete(text)
        reply = self.kc.get_shell_msg()
        jupyter_kernel_test.messagespec.validate_message(
            reply, 'complete_reply', msg_id)
        if matches is not None:
            if exact:
                self.assertEqual(set(reply['content']['matches']), set(matches))
            else:
                print(set(matches))
                print(set(reply['content']['matches']))
                self.assertTrue(
                    set(matches) <= set(reply['content']['matches']))
        else:
            self.assertFalse(None)

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
