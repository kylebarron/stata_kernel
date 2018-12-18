from utils import StataKernelTestFramework

class TestKernelStdout(StataKernelTestFramework):
    # Code in the kernel's language to write "hello, world" to stdout
    code_hello_world = 'display "hello, world"'

    def test_stata_stdout(self):
        self._test_execute_stdout('di "hi"\ndi "bye"', 'hi\n\nbye')
        self._test_execute_stdout('di 6*7', '42')

    def test_stata_more(self):
        self._test_execute_stdout('more', '--more--', exact=True)

    def test_stata_display_unicode_letter(self):
        """https://github.com/kylebarron/stata_kernel/issues/196"""
        code = """\
        local a "ä"
        di "`a'"\
        """
        self._test_execute_stdout(code, 'ä', exact=True)
