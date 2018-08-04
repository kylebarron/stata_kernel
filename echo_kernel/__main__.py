from ipykernel.kernelapp import IPKernelApp
from . import StataKernel

IPKernelApp.launch_instance(kernel_class=StataKernel)
