## Troubleshooting

If the `pip install` step gives you an error like "DEPRECATION: Uninstalling a distutils installed project (pexpect) has been deprecated", try
```
$ pip install git+https://github.com/kylebarron/stata_kernel --ignore-install pexpect
```
