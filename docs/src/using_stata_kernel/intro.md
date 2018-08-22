# Using the Stata Kernel

The Stata kernel is the bridge between Stata and the Jupyter ecosystem. It will work with any of the tools outlined in [Using Jupyter](../using_jupyter/intro.md).

After [installing](../getting_started.md) and optionally [configuring](../getting_started.md#configuration) `stata_kernel`, it should be ready for use.

## Displaying graphs

`stata_kernel` displays graphs by quietly inserting a `graph export` command after any command that creates a graph, and then loading the saved file. The advantage of this approach is that it will display _all_ graphs created, even inside a loop or program.

To minimize false positives, the graph keyword must appear at the beginning of a line. To hide the display of a graph, just prefix `graph` with [`quietly`](https://www.stata.com/help.cgi?quietly).

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
