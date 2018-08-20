# Getting Started

It doesn't take much to get `stata_kernel` up and running. Here's how:

## Prerequisites

- **Python**. In order to install the kernel, Python >= 3.5 needs to be installed.

    I suggest installing the [Anaconda
    distribution](https://www.anaconda.com/download/), which doesn't require
    administrator privileges and is simple to install. If you want to use less
    disk space, install [Miniconda](https://conda.io/miniconda.html), which
    includes few packages other than Python.


???+ note "Windows-specific steps"

    If you're using macOS or Linux, disregard this section.

    - Install [pywin32](https://github.com/mhammond/pywin32/releases/latest), which lets Python talk to Stata. Choose the version of Python you have installed (you can find the version of Python installed by typing `python --version` into your command prompt.):
        - [Python 3.5](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.5.exe)
        - [Python 3.6](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.6.exe)
        - [Python 3.7](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.7.exe)
    - [Link the Stata Automation library](https://www.stata.com/automation/#install). The Stata executable is most likely in the folder `C:\Program Files (x86)\Stata15`.

        1. In the installation directory, right-click on the Stata executable, for example, `StataSE.exe`. Choose `Create Shortcut`.
        2. Right-click on the newly created `Shortcut to StataSE.exe`, choose `Property`, and change the target from `"C:\Program Files\Stata15\StataSE.exe"` to `"C:\Program Files\Stata15\StataSE.exe" /Register`. Click `OK`.
        3. Right-click on the updated `Shortcut to StataSE.exe`; choose `Run as administrator`.

## Package Install

To install the kernel, run:

```
$ pip install stata_kernel --upgrade
$ python -m stata_kernel.install
```

The latter command will try to find the path to your Stata executable, and will
warn you if it can't. If it can't find your Stata executable, you'll have to set it yourself. Refer to the [configuration](#configuration).

## Configuration

The configuration file is named `.stata_kernel.conf` and is located in your home
directory. You can change any of the package's settings by opening the file and
changing the `value` of any line of the form

```
configuration_setting = value
```

- `stata_path`: the path to your Stata executable. The [install step](getting_started.md#package-install) should have found your executable if you installed it in the standard location. If you receive a warning during the install step, you'll need to manually find the location of Stata and add it to this file.
- `execution_mode`: For macOS users, this allows for setting the method in which `stata_kernel` communicates with Stata. `automation` uses [Stata Automation](https://www.stata.com/automation/) while `console` controls the console version of Stata.

    `console` is the default because it allows for multiple independent sessions
    of Stata to run at the same time. `automation` may be useful if you wish to
    browse the data interactively with `browse`.

    On Windows, all communication with Stata happens through Stata Automation,
    and on Linux/Unix all communication happens through the console.

- `cache_directory`: the directory for the kernel to store temporary log files and graphs. By default, this is `~/.stata_kernel_cache`, where `~` means your home directory. You may wish to change this location if, for example, you're working under a Data Use Agreement where all related files must be stored in a specific directory.

- `graph_format`: the format to export and display graphs. By default this is `svg`, but if you're on an older version of Stata, you could switch to `png`. There is also some support for `pdf` if using Jupyter Notebook.
