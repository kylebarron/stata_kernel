# Changelog

## [1.11.2] - 2020-02-21

- Fix bug where `pdf_dup` was not defined when `graph_format` was not `svg` or `png`. #332

## [1.11.1] - 2020-02-10

- Update search path to find Stata 16 path automatically on Windows. #330

## [1.11.0] - 2020-02-10

- Allow for a global configuration file on Linux. #327
- Fix bug with spaces in log file. #318
- Fix deprecation notice. #324

## [1.10.5] - 2019-01-30

- Fix bug where the return code (`_rc`) was reset by internal code after every user command. #288

## [1.10.4] - 2019-01-29

- _Actually_ fix bug that prevented long commands on Windows from working. #284

## [1.10.3] - 2019-01-28

- Fix "Code editor out of sync" Jupyterlab message. #270

## [1.10.2] - 2019-01-28

- Fix bug that prevented long commands on Windows from working. #284
- Make sure to always find correct Stata path on Mac when using Automation.
- Several documentation updates

## [1.10.1] - 2019-01-08

- Fix bug that prevented from working on Windows. #281

## [1.10.0] - 2019-01-04

- Fix `%help` magic in JupyterLab. #273
- Added example Jupyter Notebook file to documentation. #275
- Throws custom error if the Automation type library isn't registered on Windows. #276
- Adds program names to autocompletion. #280
- Don't sort file paths before variable names. #261

## [1.9.0] - 2018-12-19

- Add `%html` and `%latex` magics for displaying formatted output. #267
- `r()` is no longer cleared between commands. #266
- Add tests

## [1.8.1] - 2018-12-17

- Fix log cleaning for programs and for loops with > 10 lines. #257
- Fix autocomplete to show globals upon typing `${`. #253
- Add kernel tests. #254
- JupyterLab syntax highlighting now exists. Run `jupyter labextension install jupyterlab-stata-highlight`
- Fix bug where incorrect files were suggested. #262
- Allow use of bracketed globals in file path autocompletion

## [1.8.0] - 2018-11-28

- Don't launch Stata with WinExec on Windows. This should have the benefit that 1) a new Stata window isn't created unless it needs to be, and 2) graphs don't show up unnecessarily. #249
- Add magics to show and hide the Stata GUI. #251
- Fix displaying image in QtConsole. #246
- Fix completions bug. #247

## [1.7.4] - 2018-11-21

- Fix finding Stata path on Windows when key not in registry. #242

## [1.7.3] - 2018-11-20

- Fix log cleaning on Windows. #241

## [1.7.2] - 2018-11-20

- Fix install. Add _mata_builtins to MANIFEST.in. #239

## [1.7.1] - 2018-11-19

- Fix `%browse`, `%head`, `%tail` display issues. #237

## [1.7.0] - 2018-11-19

- Add Mata mode. #116
- Allow program to function without a configuration file. #222
- Fixed <kbd>Ctrl</kbd>+<kbd>C</kbd> behavior.
- Hide most Stata kernel output from user logs #228
- Add completions on word boundaries. #229
- Wrap SVGs in iframe tags to prevent cross-image issues. #235
- Don't overwrite configuration file if it already exists.

## [1.6.2] - 2018-10-25

- Revert closing graph window automatically. #219
- Refactor `%browse` to use the same code as `%head` internally. #217

## [1.6.1] - 2018-10-24

- Remove `regex` package as a dependency. #212
- Fix `cap`/`noi`/`qui` completions with scalars and matrices. #213
- Close Stata graph window after saving graph. #214
- Fix regex to hide "note: graph.svg not found"

## [1.6.0] - 2018-10-24

- File path autocompletions. Currently only works when files have no spaces in them. #195
- Only export graph after successful command. #210
- Display `--more--` in frontend when it stops the display. #198
- Fix `scatter` in graph regex. Only `sc` and `scatter` produce plots when not
  preceded by `twoway`. #205
- Give matrix and scalar autocompletions when using shortened command names.
  #206

## [1.5.9] - 2018-10-16

- Fix bugs with Python 3.5. #203

## [1.5.8] - 2018-10-11

- Fix incorrect regex escaping. #201

## [1.5.7] - 2018-10-11

- Fix bug that parsed multiple `///` on a single line incorrectly. #200

## [1.5.6] - 2018-10-09

- Fix bug that prevented `set rmsg on` from working. #199

## [1.5.5] - 2018-10-05

- Add `user_graph_keywords` setting to allow graphs to be displayed for third-party commands.

## [1.5.4] - 2018-09-21

- Force utf-8 encoding when writing `include` code to file. #196
- Catch `EOF` when waiting for the PDF copy of graph. #192

## [1.5.3] - 2018-09-20

- Set pexpect terminal size to 255 columns. #190

## [1.5.2] - 2018-09-19

- Add pywin32 as a pip dependency on Windows, thus making installation easier.
- Add jupyter 1.0.0 metapackage as a dependency, so that installs from Miniconda also install all of Jupyter.

## [1.5.1] - 2018-09-17

- Fix issues with `--more--`. #103
- PDF Graph redundancy. This improves ease of export to PDF via LaTeX.
- Catch PermissionsError when copying syntax highlighting files
- Add Stata logo for Jupyter Notebook
- Autoclose local macro quotes in Jupyter Notebook
- Highlight /// as comments in Jupyter Notebook
- Highlight macros in Jupyter Notebook
- Check latest PyPi package version and add alert to banner if newer
- Simplify `%set` magic
- Set default linesize to 255 for now to improve image handling. #177

## [1.5.0] - 2018-09-14

- Add CodeMirror syntax highlighting for Jupyter Notebook
- Improve Pygments syntax highlighting for highlighting of Jupyter QtConsole, Jupyter Console, and Notebook outputs in HTML and PDF format.
- Restore PDF graph support. Although it doesn't display within the Jupyter Notebook for security (or maybe just practical) reasons, it's helpful when exporting a Notebook to a PDF via LaTeX.
- Temporarily fix encoding error from CJK characters being split by a line break. #167

## [1.4.8] - 2018-09-12

- Fix use of `which` in install script
- Redirect `xstata` to `stata` on Linux. #149
- Fix hiding code lines when there are hard tab characters (`\t`). #153
- Make HTML help links open in new tab. #158
- Open log files with utf-8 encoding. https://github.com/kylebarron/language-stata/issues/98

## [1.4.7] - 2018-09-08

- Fix pypi upload. Need to use `python setup.py sdist bdist_wheel` and not `python setup.py sdist bdist`. The latter creates two source packages, and only one source package can ever be uploaded to Pypi per release.

## [1.4.6] - 2018-09-08

- Fix `install.py`; previously it had unmatched `{` and `}`
- Fix display of whitespace when entire result is whitespace. #111

## [1.4.5] - 2018-09-07

- Don't embed images in HTML help; link to them. #140
- Fix blocking for line continuation when string is before `{` #139
- Fix hiding of code lines with leading whitespace. #120
- Remove `stata_kernel_graph_counter` from globals suggestions. #109
- Always use UTF-8 encoding when loading SVGs. #130
- Add download count and Atom gif to README. Try to fix images for Pypi page.

## [1.4.4] - 2018-09-06

- Fully hide Stata GUI on Windows. Always export log file, even on Windows and Mac Automation.
- Set more off within ado files. Should fix #132.
- Use bumpversion for easy version number updating.
- Add `%help kernel` and `%help magics` options
- Add general debugging information (like OS/Stata version/package version) to log
- Add help links to Jupyter Notebook's Help dropdown UI
- Various docs fixes

## [1.4.3] - 2018-09-04

- Release to pypi again because 1.4.2 didn't upload correctly. Apparently only a
  Mac version was uploaded, and even that didn't work.

## [1.4.2] - 2018-08-21

- Fix line cleaning for loops/programs of more than 9 lines
- Remove pexpect timeout
- Provide error message upon incomplete input sent to `do_execute`

## [1.4.1] - 2018-08-21

- Add `%head` and `%tail` magics
- Change `%set plot` to `%set graph`

## [1.4.0] - 2018-08-21

- Return results as Stata returns them, not when command finishes
- More stable method of knowing when a command finishes by looking for the text's MD5 hash
- Finds Stata executable during install
- Automatically show graphs after graph commands
- Add %help and %browse magics
- Allow for graph scaling factors
- Fix Windows locals issue
- Fix image spacing

## [1.3.1] - 2018-08-13

- Fix pip installation by adding CHANGELOG and requirements files to `MANIFEST.in`.

## [1.3.0] - 2018-08-13

- Context-aware autocompletions
- Support for #delimit; blocks interactively
- Better parsing for when a user-provided block is complete or not. Typing `2 + ///` will prompt for the next line.
- Split lexer into two lexers. This is helpful to first remove comments and convert #delimit; blocks to cr-delimited blocks.
- Fix svg aspect ratio
- Magics for plotting, retrieving locals and globals, timing commands, seeing current delimiter.
- Add documentation website

## [1.2.0] - 2018-08-11

- Support for `if`, `else`, `else if`, `cap`, `qui`, `noi`, `program`, `input` blocks #28, #27, #30
- Support different graph formats #21
- Heavily refactor codebase into hopefully more stable API #32
- Correctly parse long, text wrapped lines from log file or console #41
- Use a single cache directory, configurable by the user #43
- Correctly remove comments, using a tokenizer #38, #25, #29


## [1.1.0] - 2018-08-06

**Initial release!** This would ordinarily be something like version 0.1.0, but the Echo kernel framework that I made this from was marked as 1.1 internally, and I forgot to change that before people started downloading this. I don't want to move my number down to 0.1 and have people who already installed not be able to upgrade.
