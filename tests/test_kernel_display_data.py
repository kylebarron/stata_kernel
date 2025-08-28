from utils import StataKernelTestFramework


class TestKernelDisplayData(StataKernelTestFramework):
    # Samples of code which should generate a rich display output, and
    # the expected MIME type
    # code_display_data = [
    #     {'code': 'sysuse auto\nscatter price mpg', 'mime': 'image/svg+xml'}
    # ]

    def test_stata_display_data(self):
        self._test_display_data('scatter price mpg', 'text/html')
        self._test_display_data('scatter price mpg', 'image/svg+xml')
        self._test_display_data('scatter price mpg', 'application/pdf')

    def test_stata_scatter_regex(self):
        """https://github.com/kylebarron/stata_kernel/issues/205"""
        self._test_display_data('sc price mpg', 'image/svg+xml')
        self._test_display_data('scatter price mpg', 'image/svg+xml')
