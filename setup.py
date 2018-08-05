from distutils.core import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='stata_kernel',
    version='1.1',
    packages=['stata_kernel'],
    description='Stata kernel for Jupyter',
    long_description=readme,
    author='Kyle Barron',
    author_email='barronk@mit.edu',
    url='https://github.com/kylebarron/stata_kernel',
    install_requires=[
        'jupyter_client', 'IPython', 'ipykernel', 'pexpect>=4.6.0',
        'python-dateutil>=2.7.3'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
    ],
)
