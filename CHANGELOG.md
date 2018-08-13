# Changelog

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
