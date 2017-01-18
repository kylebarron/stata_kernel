``echo_kernel`` is a simple example of a Jupyter kernel. This repository
complements the documentation on wrapper kernels here:

http://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html

To install ``echo_kernel`` from PyPI::

    pip install echo_kernel
    python -m echo_kernel.install

The *New* menu in the notebook should show an option for an Echo notebook. To
use it with the console frontends, add ``--kernel echo`` to their command line
arguments.
