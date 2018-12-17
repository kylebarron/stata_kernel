import platform
from subprocess import run
from setuptools import setup

with open('README.md') as f:
    readme = f.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

with open('requirements.txt') as requirements_file:
    requirements = requirements_file.readlines()
    requirements = [x[:-1] for x in requirements]

with open('requirements_dev.txt') as test_requirements_file:
    test_requirements = test_requirements_file.readlines()
    test_requirements = [x[:-1] for x in test_requirements]

setup_requirements = ['setuptools >= 38.6.0', 'twine >= 1.11.0']

# Recompile included docs
if platform.system() != 'Windows':
    run(['bash', 'make.sh'], cwd='./stata_kernel/docs/')

# yapf: disable
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
    keywords='stata',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    name='stata_kernel',
    packages=['stata_kernel'],
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/kylebarron/stata_kernel',
    version='1.8.1',
    include_package_data=True
)
