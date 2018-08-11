# Comparison with [ipystata](https://github.com/TiesdeKok/ipystata)

Except for Windows, this package takes a different approach to communication
with Stata. On macOS and Linux, this controls the Stata console directly, which
prevents speed degradation with larger data sets. In contrast, `ipystata` saves
the data set to disk after each code cell, slowing execution.

This is also a pure Jupyter kernel, whereas `ipystata` is a Jupyter "magic" within the Python kernel. This means that you don't need to have any knowledge of Python* and don't need to have packages like Pandas installed.

\* Python is amazing language, and if you want to move on to bigger data, I highly recommend learning Python.
