"""An example Jupyter kernel"""

import traceback

__version__ = '1.12.2'

try:
    from .kernel import StataKernel
except:
    print('Cannot import kernel')
    traceback.print_exc()
