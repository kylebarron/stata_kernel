# Configuration

The configuration file is a plain text file named `.stata_kernel.conf` and is
located in your home directory. You can change any of the package's settings by
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
