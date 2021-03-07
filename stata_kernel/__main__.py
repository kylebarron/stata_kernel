from ipykernel.kernelapp import IPKernelApp

import traceback
try:
    from .kernel import StataKernel
except:
    print('Cannot import kernel')
    traceback.print_exc()

IPKernelApp.launch_instance(kernel_class=StataKernel)
