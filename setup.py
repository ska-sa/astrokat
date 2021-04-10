#!/usr/bin/env python
"""astrokat setup script."""
from setuptools import setup, find_packages


with open("README.md") as readme:
    long_description = readme.read()

setup(
    name="astrokat",
    description="Tools for astronomy observations with the MeerKAT telescope",
    long_description=long_description,
    author="Ruby van Rooyen / MeerKAT CAM team",
    author_email="cam@ska.ac.za",
    packages=find_packages(),
    scripts=[
        "scripts/astrokat-catalogue2obsfile.py",
        "scripts/astrokat-coords.py",
        # "scripts/astrokat-fitflux.py",
        "scripts/astrokat-lst.py",
        "scripts/astrokat-observe.py",
        "scripts/astrokat-targets.py",
        # "scripts/astrokat-uvcoverage.py",
    ],
    url="https://github.com/ska-sa/astrokat",
    license="BSD 2-Clause",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    platforms=["OS Independent"],
    keywords="meerkat ska",
    zip_safe=False,
    setup_requires=["katversion"],
    use_katversion=True,
    install_requires=["astropy", "pyephem", "katpoint", "matplotlib", "numpy", "pyyaml"],
    extras_require={"live": ["katcorelib", "katconf"]},
)
