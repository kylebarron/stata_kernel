# stata_kernel

`stata_kernel` is a Jupyter kernel for Stata. It works on Windows, macOS, and
Linux.

## What is Jupyter?

Jupyter is an open-source ecosystem for interactive data science. Originally developed around the Python programming language, Jupyter has grown to interface with dozens of programming languages. `stata_kernel`
is the bridge that interactively connects Stata to all the elements in the ecosystem.

- The **Jupyter Notebook** is a web-based interactive editor that allows for interweaving of code, text, and results.

    - Splice models in LaTeX math mode with the code that implements them and the graphs depicting their output.
    - Jupyter Notebooks can be exported as PDFs or HTML, and are as good for teaching new students as they are for displaying research results.
    - Use Stata in the same document with R, Python, or Julia code.

- The **Jupyter console** is an enhanced interactive console. Its features include enhanced autocompletion, better searching of history, syntax highlighting, among others.
- **Hydrogen** is a package for the Atom text editor that connects with Jupyter kernels to display results interactively in your text editor.
- Enhanced remote work. You can set up Jupyter to run computations remotely but to show results locally, vastly enhancing productivity compared to working with the Stata console through a command line.

## `stata_kernel` Features

- [x] Supports Windows, macOS, and Linux.
- [x] Use any type of comments in your code, not just `*`.
- [x] Autocompletions as you type based on the variables, macros, and return objects currently in memory.
- [x] Display graphs.
- [x] Receive results as they appear, not after the entire command finishes.
- [x] [Pull up interactive help files within the kernel.](using_stata_kernel/magics.md#help)
- [x] [Browse data interactively](using_stata_kernel/magics.md#browse)
- [x] [`#delimit ;` interactive support.](using_stata_kernel/magics.md#delimit)
- [x] Work with a remote session of Stata
- [ ] Mata interactive support
- [ ] Cross-session history file

If you find bugs, please [submit a bug report here](https://github.com/kylebarron/stata_kernel/issues/new?template=bug_report.md).

## Screenshots

**Jupyter Notebook**

![Jupyter Notebook](img/jupyter_notebook.png)

**Atom**

![Atom](img/stata_kernel_example.gif)
