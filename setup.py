from distutils.core import setup

with open('README.rst') as f:
    readme = f.read()

setup(
    name='echo_kernel',
    version='1.1',
    packages=['echo_kernel'],
    description='Simple example kernel for Jupyter',
    long_description=readme,
    author='Jupyter Development Team',
    author_email='jupyter@googlegroups.com',
    url='https://github.com/jupyter/echo_kernel',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
    ],
)
