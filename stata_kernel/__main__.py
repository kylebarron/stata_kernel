from ipykernel.kernelapp import IPKernelApp
from .kernel import StataKernel

IPKernelApp.launch_instance(kernel_class=StataKernel)
