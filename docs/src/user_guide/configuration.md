# Configuration

The configuration file is named `.stata_kernel.conf` and is located in your home
directory. You can change any of the package's settings by opening the file and
changing the `value` of any line of the form

```
configuration_setting = value
```

- `stata_path`: the path to your Stata executable. The [install step](install.md#package-install) should have found your executable if you installed it in the standard location. If you receive a warning during the install step, you'll need to manually find the location of Stata and add it to this file.
- `execution_mode`: For macOS users, this allows for setting the method in which `stata_kernel` communicates with Stata. `automation` uses [Stata Automation](https://www.stata.com/automation/) while `console` controls the console version of Stata.

    `console` is the default because it allows for multiple independent sessions
    of Stata to run at the same time. `automation` may be useful if you wish to
    browse the data interactively with `browse`.

    On Windows, all communication with Stata happens through Stata Automation,
    and on Linux/Unix all communication happens through the console.

- `cache_directory`: the directory for the kernel to store temporary log files and graphs. By default, this is `~/.stata_kernel_cache`, where `~` means your home directory. You may wish to change this location if, for example, you're working under a Data Use Agreement where all related files must be stored in a specific directory.

- `graph_format`: the format to export and display graphs. By default this is `svg`, but if you're on an older version of Stata, you could switch to `png`. There is also some support for `pdf` if using Jupyter Notebook.
