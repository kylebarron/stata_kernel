# Using the Stata Kernel

`stata_kernel` is the bridge between Stata and the Jupyter ecosystem. It will work with any of the tools outlined in [Using Jupyter](../using_jupyter/intro.md). After [installing](../getting_started.md) and optionally [configuring](configuration.md) `stata_kernel`, it should be ready for use.

On the rest of this page, you can learn more about some of the features `stata_kernel` provides.

## Displaying graphs

`stata_kernel` displays graphs by quietly inserting a `graph export` command after any command that creates a graph, and then loading and displaying the saved file. The advantage of this approach is that it will display _all_ graphs created, even inside a loop or program, as long as that program was defined in text you run with the kernel.

To minimize false positives, the graph keyword must appear at the beginning of a line. To hide the display of a graph, just prefix `graph` with [`quietly`](https://www.stata.com/help.cgi?quietly).

### Graph not displaying?

`stata_kernel` looks for _graph commands_ in your code, and requires that these be the first non-whitespace characters on a given line. This means that if you prefix `scatter` with `quietly`, `noisily`, or `capture`, the graph won't be displayed.

In order to force display of a graph, you can run:
```do
graph display
```

`stata_kernel` checks your command against a list of graph commands, and only tries to export a graph if one matches. This means that some user-created commands that export graphs (e.g., `coefplot` or `vioplot`) won't work out of the box.

To display graphs from user created commands, add the command name to the
[`user_graph_keywords`](../../getting_started#user_graph_keywords) setting. You
can do this either in the configuration file before starting the session or with
```
%set user_graph_keywords command1,command2,...
```
during the session.

### Graph display format

`stata_kernel` must export the image in some format in order to load and display it. Sadly, there are considerable pros and cons to each image format:

- `png` files can't be created with the console version of Stata, and thus are off limits to the Linux and Mac (console) modes of `stata_kernel`. Additionally, they can look pixelated when scaled up.
- `svg` files can be created by Stata 14 and 15 on all platforms, and look crisp at all sizes, but can't be used with LaTeX PDF output.
- `pdf` files can be created by all recent versions of Stata on all platforms, look crisp at all sizes, and work in LaTeX PDF output, but [JupyterLab](../../using_jupyter/lab) is the only front end in which they'll display correctly.
- `tif` files are too large.

`stata_kernel` lets you set the display format to be `png`, `svg`, or `pdf`.

### Graph redundancy

One of the many amazing things about Jupyter Notebooks is that with a single click, you can [export the notebook](https://nbconvert.readthedocs.io/en/latest/) to an aesthetic PDF using LaTeX.

Except on Windows using Stata 14 or earlier, `stata_kernel` displays images in `svg` format by default. However, as [noted above](#graph-display-format), these images can't be included in a LaTeX PDF export without conversion.

To solve this problem, `stata_kernel` has the ability to hand Jupyter _both_ the `svg` or `png` version of an image _and_ the `pdf` version of the same image. While only the former will be displayed, the `pdf` version of the image will be stored in the Notebook and used when exported to PDF.

While ease of use with LaTeX on macOS and Linux is a significant benefit, this redundancy does make `stata_kernel` delay slightly when displaying an image and enlarges the Jupyter Notebook file size (because two formats of every image will be stored within the Jupyter Notebook file).

To turn off graph redundancy, change both configuration options to False:

- `graph_svg_redundancy`: Whether to provide redundant PDF images when `svg` is the display format. `True` by default.
- `graph_png_redundancy`: Whether to provide redundant PDF images when `png` is the display format. `False` by default.

Because both image formats will be stored within the Jupyter Notebook file, `stata_kernel` will warn you if graph redundancy is on and an image is larger than 2 megabytes. To turn off this warning, set `graph_redundancy_warning` to `False`.

## Autocompletion

Based on the current Stata environment, `stata_kernel` will autocomplete variables, locals, globals, scalars, matrices, _and file paths_ (as of version 1.6.0).

As of version 1.6.0, file paths will only generate suggestions if there are no spaces in what you've typed. In the future I hope to relax this restriction, so that quoted file paths with spaces will still allow autocomplete.

By default, autocomplete does not include the trailing character (such as a `'` for a local macro) when you select a suggestion. This is because front ends like [Hydrogen](../../using_jupyter/atom) already autocomplete the `'` for you after you type a `` ` ``. If you're using a different front end, you can turn on the [`autocomplete_closing_symbol`](../../getting_started#autocomplete_closing_symbol) setting so that locals include the ending `'`.

## `#delimit ;` mode

Stata lets you use [`;` as a command
delimiter](https://www.stata.com/help.cgi?delimit) in a do file after a line
`#delimit ;`. This can be helpful when writing very long commands, like
complicated graphs, as it allows for more free-flowing line wrapping. But Stata
doesn't allow for running `;`-delimited code interactively, which makes
debugging code difficult.

`stata_kernel` lets you code interactively with semicolons as the delimiter for commands within the `#delimit ;` mode. When activated, it first removes the extra line breaks in the input code and then removes the semicolon, resulting in the code's carriage return-delimited equivalent, which can then be sent to Stata.

To turn this mode on, just run `#delimit ;`. To turn it off, run `#delimit cr`. To check the current delimiter, run `%delimit`. Code can switch back and forth between delimiters several times with no issue.

Note that when the setting is enabled, sending code to Stata without a `;` at the end will be returned as invalid.
