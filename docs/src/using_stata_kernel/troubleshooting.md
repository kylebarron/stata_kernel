# Troubleshooting

## Installation

- If the `pip install` step gives you an error like "DEPRECATION: Uninstalling a distutils installed project (pexpect) has been deprecated", try

    ```
    pip install stata_kernel --ignore-install pexpect
    ```

- If you have multiple installations of Python on your machine, make sure you run `python -m stata_kernel.install` during installation with the same Python executable as the one you usually use. This matters especially when using several Python virtual environments. You'll need to install `stata_kernel` within each environment you use.
