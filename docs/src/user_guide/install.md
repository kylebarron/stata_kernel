# Installation

## Prerequisites

- **Python**. In order to install the kernel, Python >= 3.5 needs to be installed. I suggest installing the [Anaconda distribution](https://www.anaconda.com/download/), which doesn't require administrator privileges and is simple to install. If you want to use less disk space, install [Miniconda](https://conda.io/miniconda.html), which includes few packages other than Python.
- **Windows only:**
    - Install [pywin32](https://github.com/mhammond/pywin32/releases/latest), which lets Python talk to Stata. Choose the version of Python you have installed:
        - [Python 3.5](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.5.exe)
        - [Python 3.6](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.6.exe)
        - [Python 3.7](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.7.exe)
    - [Link the Stata Automation library](https://www.stata.com/automation/#install). The Stata executable is most likely in the folder `C:\Program Files (x86)\Stata15`.

        1. In the installation directory, right-click on the Stata executable, for example, StataSE.exe. Choose "Create Shortcut".
        2. Right-click on the newly created "Shortcut to StataSE.exe", choose "Property", and change the Target from "C:\Program Files\Stata13\StataSE.exe" to "C:\Program Files\Stata13\StataSE.exe" /Register. Click "OK".
        3. Right-click on the updated "Shortcut to StataSE.exe"; choose "Run as administrator"

## Package Install

To install the kernel, run:

```
$ pip install stata_kernel
$ python -m stata_kernel.install
```
