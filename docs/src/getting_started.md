# Getting Started

It doesn't take much to get `stata_kernel` up and running. Here's how:

## Prerequisites

- **Python**. In order to install the kernel, Python >= 3.5 needs to be installed on the computer on which Stata is running.

    I suggest installing the [Anaconda
    distribution](https://www.anaconda.com/download/), which doesn't require
    administrator privileges and is simple to install.

    The Anaconda installer includes many third party libraries for Python that
    `stata_kernel` doesn't use. If you don't plan to use Python and want to use
    less disk space, install [Miniconda](https://conda.io/miniconda.html), which
    includes few packages other than Python. Then in [Package
    Install](#package-install) any other necessary dependencies will be
    downloaded automatically.


???+ note "Windows-specific steps"

    If you're using macOS or Linux, disregard this section.

    - Install [pywin32](https://github.com/mhammond/pywin32/releases/latest), which lets Python talk to Stata. Choose the version of Python you have installed (you can find the version of Python installed by typing `python --version` into your command prompt.):
        - [Python 3.5](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.5.exe)
        - [Python 3.6](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.6.exe)
        - [Python 3.7](https://github.com/mhammond/pywin32/releases/download/b223/pywin32-223.win-amd64-py3.7.exe)
    - [Link the Stata Automation library](https://www.stata.com/automation/#install).

        1. In the installation directory (most likely `C:\Program Files (x86)\Stata15` or similar), right-click on the Stata executable, for example, `StataSE.exe`. Choose `Create Shortcut`.
        2. Right-click on the newly created `Shortcut to StataSE.exe`, choose `Property`, and change the target from `"C:\Program Files\Stata15\StataSE.exe"` to `"C:\Program Files\Stata15\StataSE.exe" /Register`. Click `OK`.
        3. Right-click on the updated `Shortcut to StataSE.exe`; choose `Run as administrator`.

## Package Install

To install the kernel, from a terminal or command prompt run:

```
pip install stata_kernel
python -m stata_kernel.install
```

The second command will try to find your Stata executable, and will warn you if
it can't. In that case, you'll have to set it yourself. Refer to the
[configuration](#configuration) below.

`python -m stata_kernel.install` only needs to be run _once ever_. Running it
more than once will reset any settings to the original defaults.

If Python 2 is the default version of Python on your system, you may need to use
```
pip3 install stata_kernel
python3 -m stata_kernel.install
```

To upgrade from a previous version of `stata_kernel`, from a terminal or command prompt run

```
pip install stata_kernel --upgrade
```

When upgrading, don't run `python -m stata_kernel.install` again. It will
overwrite any settings you've defined in the [configuration](#configuration).

## Configuration

The configuration file is named `.stata_kernel.conf` and is located in your home
directory. You can change any of the package's settings by opening the file and
changing the `value` of any line of the form

```
configuration_setting = value
```

### General settings

- `stata_path`: the path on your file system to your Stata executable. Usually this can be found automatically in the [install step](getting_started.md#package-install), but sometimes may need to be set manually.

- `cache_directory`: the directory for the kernel to store temporary log files and graphs. By default, this is `~/.stata_kernel_cache`, where `~` means your home directory. You may wish to change this location if, for example, you're working under a Data Use Agreement where all related files must be stored in a specific directory.

- `execution_mode`: For macOS users, this allows for setting the method in which `stata_kernel` communicates with Stata. `automation` uses [Stata Automation](https://www.stata.com/automation/) while `console` controls the console version of Stata.

    `console` is the default because it allows for multiple independent sessions
    of Stata to run at the same time. `automation` may be useful if you wish to
    browse the data interactively with `browse`.

    On Windows, all communication with Stata happens through Stata Automation,
    and on Linux/Unix all communication happens through the console.

### Graph settings

These settings can be changed during a session with the `%set` magic, like so:

```
%set graph --format svg
%set graph --scale 1
%set graph --width 500
%set graph --width 400 --height 300
```

- `graph_format`: `svg` or `png`, the format to export and display graphs. By default this is `svg` for most operating systems and versions of Stata, but is `png` by default for Windows on Stata 14 and below.

- `graph_scale`: a decimal number. This scales equally the width and height of plots displayed. By default, plots are 600 pixels wide.

- `graph_width`: an integer. This is the width in pixels of graphs displayed. If no `graph_height` is set, Stata will determine the optimal height for the specific image.

- `graph_height`: an integer. This is the height in pixels of graphs displayed.
