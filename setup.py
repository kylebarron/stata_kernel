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
        'jupyter_client>=5.2.3', 'IPython>=6.5.0', 'ipykernel>=4.8.2',
        'pexpect>=4.6.0;platform_system=="Darwin"',
        'pexpect>=4.6.0;platform_system=="Linux"', 'python-dateutil>=2.7.3'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3'],
)
