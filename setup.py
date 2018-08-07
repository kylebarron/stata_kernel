from distutils.core import setup

with open('README.md') as f:
    readme = f.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

requirements = [
    'jupyter_client>=5.2.3', 'IPython>=6.5.0', 'ipykernel>=4.8.2',
    'pexpect>=4.6.0;platform_system=="Darwin"',
    'pexpect>=4.6.0;platform_system=="Linux"', 'python-dateutil>=2.7.3']

setup_requirements = [
    'setuptools >= 38.6.0',
    'twine >= 1.11.0'
]

setup(
    author='Kyle Barron',
    author_email='barronk@mit.edu',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'],
    description='A Jupyter kernel for Stata. Works with Windows, macOS, and Linux. Preserves program state.',
    install_requires=requirements,
    license='GPLv3',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    keywords='stata',
    name='stata_kernel',
    packages=['stata_kernel'],
    url='https://github.com/kylebarron/stata_kernel',
    version='1.1.0',
)
