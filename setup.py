from distutils.core import setup

with open('README.md') as f:
    readme = f.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

requirements = [
    'jupyter_client>=5.2.3', 'IPython>=6.5.0', 'ipykernel>=4.8.2',
    'pexpect>=4.6.0;platform_system=="Darwin"',
    'pexpect>=4.6.0;platform_system=="Linux"', 'python-dateutil>=2.7.3',
    'pygments>=2.2.0', "regex>=2018.7.11"]

setup_requirements = [
    'setuptools >= 38.6.0',
    'twine >= 1.11.0']

test_requirements = [
    'mkdocs==1.0',
    'mkdocs-material==3.0.3',
    'bumpversion==0.5.3',
    'coverage==4.5.1',
    'flake8==3.5.0',
    'pip==18.0',
    'pytest==3.7.1',
    'tox==2.9.1',
    'wheel==0.30.0',
    'yapf==0.20.2']

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
    version='1.2.0',
    include_package_data=True
)
