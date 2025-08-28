from ipykernel.kernelapp import IPKernelApp

import traceback
try:
    from .kernel import StataKernel
except Exception as e:
    print('Error while importing StataKernel:', e)
    traceback.print_exc()

IPKernelApp.launch_instance(kernel_class=StataKernel)
