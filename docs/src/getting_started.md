# Getting Started

It doesn't take much to get `stata_kernel` up and running. Here's how:

## Prerequisites

- **Python**. In order to install the kernel, Python 3.5, 3.6, or 3.7 needs to be installed on the computer on which Stata is running.

    I suggest installing the [Anaconda
    distribution](https://www.anaconda.com/download/). This doesn't require
    administrator privileges, and is the simplest way to install Python.

    If you don't install Python through Anaconda, you may need to install some
    dependencies manually, like [Cython](https://cython.org/#download).

    The Anaconda installer includes many third party libraries for Python that
    `stata_kernel` doesn't use. If you don't plan to use Python and want to use
    less disk space, install [Miniconda](https://conda.io/miniconda.html), which
    includes few packages other than Python. Then when [installing the package](#package-install) any other necessary dependencies will be
    downloaded automatically.


???+ note "Windows-specific steps"

    In order to let `stata_kernel` talk to Stata, you need to [link the Stata Automation library](https://www.stata.com/automation/#install):

    1. In the installation directory (most likely `C:\Program Files (x86)\Stata15` or similar), right-click on the Stata executable, for example, `StataSE.exe`. Choose `Create Shortcut`. Placing it on the Desktop is fine.
    2. Right-click on the newly created `Shortcut to StataSE.exe`, choose `Property`, and append `/Register` to the end of the Target field. So if the target is currently `"C:\Program Files\Stata15\StataSE.exe"`, change it to `"C:\Program Files\Stata15\StataSE.exe" /Register`. Click `OK`.
    3. Right-click on the updated `Shortcut to StataSE.exe`; choose `Run as administrator`.

## Package Install

To install the kernel, from a terminal or command prompt run:

```
pip install stata_kernel
python -m stata_kernel.install
```

The second command will try to find your Stata executable, and will warn you if
it can't. In that case, you'll have to set it yourself. Refer to the
[configuration](using_stata_kernel/configuration.md) settings.

`python -m stata_kernel.install` only needs to be run _once ever_.

If Python 2 is the default version of Python on your system, you may need to use
```
pip3 install stata_kernel
python3 -m stata_kernel.install
```

To upgrade from a previous version of `stata_kernel`, from a terminal or command prompt run

```
pip install stata_kernel --upgrade
```

When upgrading, you don't have to run `python -m stata_kernel.install` again.
