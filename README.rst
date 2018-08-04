stata_kernel
===========

``stata_kernel`` is a simple example of a Jupyter kernel. This repository
complements the documentation on wrapper kernels here:

http://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html

Installation
------------
To install ``stata_kernel`` from PyPI::

    pip install stata_kernel
    python -m stata_kernel.install

Using the Stata kernel
---------------------
**Notebook**: The *New* menu in the notebook should show an option for an Stata notebook.

**Console frontends**: To use it with the console frontends, add ``--kernel stata`` to
their command line arguments.
