# Configuration

The configuration file is a plain text file named `.stata_kernel.conf` and is
located in your home directory, or defined by the environmental variable
`STATA_KERNEL_USER_CONFIG_PATH`. Settings must be under the heading
`[stata_kernel]`. You can change any of the package's settings by
opening the file and changing the `value` of any line of the form

```
configuration_setting_name = value
```

You can also make changes to the configuration while the kernel is running with the [%set magic](magics.md#set). For example:

```
%set autocomplete_closing_symbol False
%set graph_format png
```

If you want these changes to be stored permanently, add `--permanently`:
```
%set graph_format png --permanently
```

!!! info "System wide configuration file for JupyterHub"

    If you are installing `stata_kernel` in Jupyter Hub you must create a system
    wide configuration file to provide default values. The default location
    is in `/etc/stata_kernel.conf`, or defined by the environmental variable
    `STATA_KERNEL_GLOBAL_CONFIG_PATH`.

## General settings

### `stata_path`

A string; the path on your file system to your Stata executable. Usually this can be found automatically during the [install step](../getting_started.md#package-install), but sometimes may need to be set manually. This cannot be changed while using `%set`, and must be edited in the configuration file before starting Jupyter.

### `cache_directory`

A string; the directory for the kernel to store temporary log files and graphs. By default, this is `~/.stata_kernel_cache`, where `~` means your home directory. You may wish to change this location if, for example, you're working under a Data Use Agreement where all related files must be stored in a specific directory.

### `execution_mode`

**macOS only**, a string of either `"automation"` or `"console"`.

This is the method through which `stata_kernel` communicates with Stata. `automation` uses [Stata Automation](https://www.stata.com/automation/) while `console` controls the console version of Stata.

`console` is the default because it allows for multiple independent sessions
of Stata to run at the same time, and can be faster. `automation` supports running `browse`, to bring up the Stata data explorer, however the [`%browse` magic](magics.md#browse) can also be used to inspect data within Jupyter (with either execution mode).

On Windows, all communication with Stata happens through Stata Automation, because Stata console doesn't exist for Windows. On Linux/Unix all communication happens through the console, because Stata Automation doesn't exist for Linux/Unix.

???+ warning "Notice for StataIC Mac users"

    The main way that `stata_kernel` communicates with the running Stata session
    on macOS and Linux is with the _console version_ of Stata. This runs in a
    terminal instead of with the Stata GUI. For no good reason StataCorp decided
    not to ship the console program with StataIC on macOS.

    To work around this, StataIC Mac users must use `automation` execution mode.

    On macOS, using Automation is slower than using console mode, but there's
    nothing I can do about it. I asked StataCorp why they don't ship a console
    version with StataIC on Mac, when they do on Linux. Basically you're not a
    "power user".

    > Unix operating systems often have an optional graphical user interface so we
    > need to include console versions of Stata for all flavors of Stata on those
    > systems.
    >
    > The Mac operating system always has a graphical user interface so the console
    > version of Stata on the Mac is a special tool that is included for power users.
    > The Stata/IC for Mac is designed for regular Stata users and does not include a
    > console version.
    >
    > Originally the Mac versions of Stata were just like the Windows versions and
    > did not have any console support.

    \- Stata Technical Support

### `autocomplete_closing_symbol`

either `True` or `False`; whether autocompletion suggestions should include the closing symbol (i.e. ``'`` for a local macro or `}` if the global starts with `${`). This is `False` by default.

## Graph settings

These settings determine how graphs are displayed internally. [Read here](intro.md#displaying-graphs) for more information about how `stata_kernel` displays graphs.

### `graph_format`

`svg` or `png`, the format to export and display graphs. By default this is `svg` for most operating systems and versions of Stata, but is `png` by default for Windows on Stata 14 and below.

### `graph_scale`

a decimal number. This scales equally the width and height of plots displayed. By default, plots are 600 pixels wide.

### `graph_width`

an integer. This is the width in pixels of graphs displayed. If no `graph_height` is set, Stata will determine the optimal height for the specific image.

### `graph_height`

an integer. This is the height in pixels of graphs displayed.

### `user_graph_keywords`

a string. `stata_kernel` [displays graphs](intro.md#displaying-graphs) by quietly inserting a `graph export` command after any command that creates a graph, and then loading and displaying the saved file. By default, it only looks for the base list of graph commands.

If you use third party commands that generate figures, this option allows you to provide a list of commands that will also display graphs. Provide multiple graph names as a comma-delimited string, e.g. in the configuration file add:

```
user_graph_keywords = vioplot,coefplot
```

Note that when using the [`%set` magic](magics.md#set), the list of comma-delimited keywords must not have any spaces in it. For example, you must run

```
%set user_graph_keywords vioplot,coefplot
```

and not

```
%set user_graph_keywords vioplot, coefplot
```

### `graph_svg_redundancy`

Whether to provide redundant PDF images when `svg` is the display format. `True` by default.
For more information about what _Graph Redundancy_ is, [read here](intro.md#graph-redundancy).

### `graph_png_redundancy`

Whether to provide redundant PDF images when `png` is the display format. `False` by default.
For more information about what _Graph Redundancy_ is, [read here](intro.md#graph-redundancy).

## Example config file

An example config file:

``` ini
[stata_kernel]
stata_path = "C:\Program Files\Stata16\StataMP-64.exe"
execution_mode = automation
cache_directory = ~/.stata_kernel_cache
autocomplete_closing_symbol = False
graph_format = svg
graph_scale = 1
user_graph_keywords = coefplot,vioplot
```
