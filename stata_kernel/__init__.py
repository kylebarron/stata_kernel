"""An example Jupyter kernel"""

__version__ = '1.12.2'

try:
    from .kernel import StataKernel
except:
    print('Cannot import kernel')
