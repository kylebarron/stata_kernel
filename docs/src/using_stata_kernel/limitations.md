# Limitations

Due to the architecture of `stata_kernel`, there is some usual functionality that won't work.

### Log files

#### Log files have extra code in them

In order to provide extra functionality like magics and autocomplete,
`stata_kernel` runs a few extra commands in Stata after your command has
completed. The downside of this is that all those extra commands and their
output show up in user-created log files.

In general, I recommend using `stata_kernel` to create Jupyter Notebooks, rather than using Stata's log file exporting.

#### Can't run `log close _all` on Windows

Some people have `log close _all` as a standard command at the top of each
script. On Windows and on macOS using [Automation
mode](http://localhost:8000/getting_started/#general-settings), this will break
`stata_kernel` functionality, because that line closes the log file that it uses
to receive communications.
