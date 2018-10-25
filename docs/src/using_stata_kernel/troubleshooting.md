# Troubleshooting

## Installation

- If the `pip install` step gives you an error like "DEPRECATION: Uninstalling a distutils installed project (pexpect) has been deprecated", try

    ```
    pip install stata_kernel --ignore-install pexpect
    ```

- If you have multiple installations of Python on your machine, make sure you run `python -m stata_kernel.install` during installation with the same Python executable as the one you usually use. This matters especially when using several Python virtual environments. You'll need to install `stata_kernel` within each environment you use.

## Running

- If you're on Windows, and upon trying to start `stata_kernel` you see an error message in the terminal window that ends with:

    ```
    pywintypes.com_error: (-2147221005, 'Invalid class string', None, None)
    ```

    That means that the Stata type library has not been correctly registered, so
    `stata_kernel` is unable to communicate with Stata. See the [instructions
    here](../../getting_started#prerequisites) (under "Windows-specific steps")
    for how to register the type library. It is not necessary to reinstall
    `stata_kernel` after this.
