# Configuration

The configuration file is named `.stata_kernel.conf` and is located in your home directory. On Windows, this attempts to find the path to your Stata executable. Otherwise, you need to set the path to your Stata executable before running the kernel.

- `stata_path`: The path to your Stata executable.

    On Mac, the default installation is in a place like
    ```
    /Applications/Stata/StataSE.app/Contents/MacOS/
    ```

    There are two executables: `StataSE` and `stata-se`. The former opens the GUI
    and should be used if you choose `automation` mode, while the latter opens the
    console and should be used if you choose `console` mode.

- `execution_mode`: This can be set to `automation` or `console`, and is the manner in which this kernel talks to Stata. `automation` uses Stata Automation to communicate to Stata while `console` controls the console version of Stata. `automation` is only available on Windows or macOS. `console` is only available on macOS or Linux. On macOS, `automation` is the preferred option, though may have more bugs at the moment than `console`.
- `cache_directory`: This is the directory for the kernel to store temporary log files and graphs. By default, this is `~/.stata_kernel_cache`, where `~` means your home directory.
- `graph_format`: This is the format to export and display graphs. By default this is `svg`, but if you're on an older version of Stata, you could switch to `png`. There is also some support for `pdf` if using Jupyter Notebook.
