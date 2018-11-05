# Comparison with [IPyStata](https://github.com/TiesdeKok/ipystata)

## `stata_kernel` is faster with larger datasets

`stata_kernel` takes a different approach to communication with Stata. With `IPyStata` on macOS and Linux, to run each segment of code

1. Your data has to be moved from Python to Stata
2. Run the commands in Stata
3. Return the data to Python to save it for the next command

This process is prohibitive with larger amounts of data. In contrast, `stata_kernel` controls Stata directly, so it generally is no slower than using the Stata program itself.

## `stata_kernel` provides more features

`stata_kernel` is a pure Jupyter kernel, whereas IPyStata is a Jupyter _magic_ within the Python kernel. This means that with `stata_kernel`

- You don't have to include `%%stata` at the beginning of every cell.
- You get features like autocompletion and being able to use `;` as a delimiter.
- You see intermediate results of long-running commands without waiting for the entire command to have finished.
- You can create multiple graphs in the same cell without having to name each of them individually. (Order of the graphs is also guaranteed).
- You don't have to have any knowledge whatsoever of Python [^1].

[^1]: Python is amazing language, and if you want to move on to bigger data, I highly recommend learning Python. Now that `stata_kernel` is installed, if you want to start a Python notebook instead of a Stata notebook, just choose New > Python 3 in the dropdown menu.
