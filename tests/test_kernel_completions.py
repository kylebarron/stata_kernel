from utils import StataKernelTestFramework
from stata_kernel.config import Config


class TestKernelCompletions(StataKernelTestFramework):

    # samples for the autocompletion functionality
    # for each dictionary, `text` is the input to try and complete, and
    # `matches` the list of all complete matching strings which should be found
    completion_samples = [
        # Magics
        {
            'text': '%',
            'matches': {'browse', 'delimit', 'globals', 'head', 'help',
                        'hide_gui', 'locals', 'set', 'show_gui', 'status',
                        'tail', 'html', 'latex'}
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
    ]  # yapf: disable

    def test_stata_global_completion(self):
        code = """\
            global abcd "helloworld"
            global abdef "foo"
            global aef "bar"
            """
        self._run(code)

        text = 'di $a'
        matches = {'abcd', 'abdef', 'aef'}
        self._test_completion(text, matches, exact=True)

        text = 'di ${a'
        matches = {'abcd', 'abdef', 'aef'}
        self._test_completion(text, matches, exact=True)

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

    def test_stata_path_completion6(self):
        text = 'use "CHANGE'
        matches = {'CHANGELOG.md'}
        self._test_completion(text, matches, exact=True)

    def test_stata_path_completion7(self):
        text = 'use "stata_kernel/'
        matches = {'stata_kernel/completions.py', 'stata_kernel/code_manager.py', 'stata_kernel/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion8(self):
        text = 'use "stata_kernel/c'
        matches = {'stata_kernel/completions.py', 'stata_kernel/code_manager.py', 'stata_kernel/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion9(self):
        self._run('global datadir "stata_kernel"')
        text = 'use "$datadir/'
        matches = {'$datadir/completions.py', '$datadir/code_manager.py', '$datadir/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion10(self):
        self._run('global datadir "stata_kernel"')
        text = 'use "$datadir/c'
        matches = {'$datadir/completions.py', '$datadir/code_manager.py', '$datadir/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion11(self):
        self._run('global datadir "stata_kernel"')
        text = 'use "${datadir}/'
        matches = {'${datadir}/completions.py', '${datadir}/code_manager.py', '${datadir}/config.py'}
        self._test_completion(text, matches, exact=False)

    def test_stata_path_completion12(self):
        text = 'use "${datadir}/c'
        matches = {'${datadir}/completions.py', '${datadir}/code_manager.py', '${datadir}/config.py'}
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
