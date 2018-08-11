# stata_kernel

`stata_kernel` is a Jupyter kernel for Stata; It works on Windows, macOS, and
Linux.

Atom             |  Jupyter Notebook
:-------------------------:|:-------------------------:
![Atom](img/atom.png)    |  ![Jupyter Notebook](img/jupyter_notebook.png)


## Features

`stata_kernel` is undergoing active development. It works now, but will be more
polished in a week.

- [x] Supports Windows, macOS, and Linux.
- [x] Works with Jupyter Notebook and Atom's Hydrogen package
- [x] Allows for inline and block comments.
- [x] Display graphs (still working out limitations)
- [x] Work with a remote session of Stata
- [ ] Receive results as they appear, not after the entire command finishes.
- [ ] Special shorthand "magics" to aid with, for example benchmarking code.
- [ ] Documentation website.
- [ ] Autocompletions as you type based on the variables, macros, and return objects currently in memory.
- [ ] Mata interactive support
- [ ] `#delimit ;` support.
- [ ] Cross-session history file
- [ ] Easily pull up help files within the kernel.
