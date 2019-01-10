# Troubleshooting

## Installation

- If the `pip install` step gives you an error like "DEPRECATION: Uninstalling a distutils installed project (pexpect) has been deprecated", try

    ```
    pip install stata_kernel --ignore-install pexpect
    ```

- If you have multiple installations of Python on your machine, make sure you run `python -m stata_kernel.install` during installation with the same Python executable as the one you usually use. This matters especially when using several Python virtual environments. You'll need to install `stata_kernel` within each environment you use.

## Graphs won't display

- If you're using a user-written command to generate your graph, you'll need to add that command to the [list of graph keywords](configuration.md#user_graph_keywords).
- If you're on Windows and using Edge as your browser, SVG images won't work. This is a known issue.

    Easy solutions:

    - Don't use Internet Explorer/Edge
    - Set the graph format to PNG instead of SVG. Run one of the following to [change the graph's storage format](configuration.md#graph_format):

        ```
        %set graph_format png
        %set graph_format png --permanently
        ```
