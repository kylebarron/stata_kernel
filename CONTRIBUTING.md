# Contributing

All types of contributions are welcome. You can:

- [Submit a bug report](#bug-reports)
- [Update or add new documentation or examples](#updating-the-docs)
- [Add automated tests](#tests)
- Submit a pull request for a new feature

## Bug reports

The best way to get your issue solved is to provide a [minimal, complete, verifiable example.](https://stackoverflow.com/help/mcve) In order to submit a bug report, [click here](https://github.com/kylebarron/stata_kernel/issues/new/choose) and fill out the template.

## Debugging

The following seems to be the easiest way to debug internals:

```py
from stata_kernel.kernel import StataKernel
from stata_kernel.code_manager import CodeManager

kernel = StataKernel()
session = kernel.stata

# If on windows, may be helpful
session.show_gui()

code = 'sysuse auto, clear'
cm = CodeManager(code)
text_to_run, md5, text_to_exclude = cm.get_text(kernel.conf, session)
rc, res = session.do(
    text_to_run, md5, text_to_exclude=text_to_exclude, display=False)
```

## Tests

### Adding tests

Tests are contained in the Python files in the `tests/` folder. The `test_stata_lexer.py` and `test_mata_lexer.py` files run automated tests on the code Stata kernel uses to parse user input.

### Running tests

To run the tests, you need to install `pytest` and `jupyter_kernel_test`:
```
pip install pytest jupyter_kernel_test
```

From the project root, to run all tests, run

```
pytest tests/
```

To run just the non-automated tests that depend on having Stata available locally, run

```
pytest tests/test_kernel.py
```

For each of the above, if you get a `ModuleNotFound` error, you may need to use `python -m pytest tests/`.

## Updating the docs

First install `mkdocs`:

```
pip install mkdocs mkdocs-material
```

Then `cd` to the docs folder:
```
cd docs/
```

Then to serve the documentation website in real time, run
```
mkdocs serve
```
This starts a web server on localhost, usually on port 8000. So you can open your web browser and type in `localhost:8000`, click <kbd>Enter</kbd>, and you should see the website. This will update in real time as you write more documentation.

To create a static website, run:
```
mkdocs build
```

To publish the website to the documentation website (if you have repository push access) run:
```
mkdocs gh-deploy
```


## Releasing new versions

To increment version numbers, run one of:
```
bumpversion major
bumpversion minor
bumpversion patch
```
in the project's root directory. This will also automatically create a git commit and tag of the version. Then push with:

```
git push origin master --tags
```

so that Github sees the newest tag.

Then to release:

```
python setup.py sdist bdist_wheel
python -m twine upload dist/stata_kernel-VERSION*
```
and put in the PyPI username and password.
