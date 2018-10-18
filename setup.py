from distutils.core import setup
setup(
    name='astrokat',
    version='0.1',
    py_modules=['astrokat'],
    install_requires=['pyephem',
                      'katpoint',
                      'matplotlib',
                      'numpy',
                      'pyyaml'])
