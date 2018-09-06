---
name: Bug report
about: Create a report to help us improve

---

#### Problem description

- This should explain **why** the current behavior is a problem and why the expected output is a better solution.
- **Note**: Many problems can be resolved by simply upgrading `stata_kernel` to the latest version. Before submitting, please try:

    ```
    pip install stata_kernel --upgrade
    ```
    and check if your issue is fixed.

#### Debugging log

If possible, attach the text file located at

```
$HOME/.stata_kernel_cache/console_debug.log
```
where `$HOME` is your home directory. This will help us debug your problem quicker.

**NOTE: This file includes a history of your session. If you work with restricted data, do not include this file.**

#### Code Sample

Especially if you cannot attach the debugging log, please include a [minimal, complete, and verifiable example.](https://stackoverflow.com/help/mcve)

```stata
// Your code here

```

#### Expected Output

#### Other information

If you didn't attach the debugging log, please provide:

- Operating System
- Stata version
- Package version (You can find this by running `pip show stata_kernel` in your terminal.)
