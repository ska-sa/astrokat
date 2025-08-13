# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AstroKAT is a Python package for observation planning and execution tools for the MeerKAT telescope. It provides utilities for target management, observation scheduling, scan patterns, noise diode control, and correlator configuration for radio astronomy observations.

## Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/ska-sa/astrokat.git
cd astrokat
python3 -m venv env
source env/bin/activate
pip install -e .
```

## Common Development Commands

### Testing
- Run all tests: `tox -e py36` or `tox -e py27`
- Run specific test module: `python -m nose astrokat.test.test_scans`
- Run with coverage: `coverage run --source=astrokat -m nose --xunit-file=nosetests.xml`

### Linting and Code Quality
- Pylint: `pylint astrokat --output-format=parseable`
- Flake8: `flake8` (configured in setup.cfg with max-line-length=90)
- Code formatting: Uses Black with line-length=90 (see pyproject.toml)
- Import sorting: Uses isort (configured in pyproject.toml)

### Building
- Build wheel: `python setup.py bdist_wheel`
- Build Debian package: `fpm -s python -t deb .`

## Code Architecture

### Core Modules
- **astrokat/observe_main.py**: Main observation execution logic and chronology checking
- **astrokat/observatory.py**: MeerKAT observatory configuration and antenna management
- **astrokat/targets.py**: Target definition, coordinate handling, and celestial object management
- **astrokat/scans.py**: Scan pattern implementations (drift, raster, reference pointing)
- **astrokat/correlator.py**: Correlator configuration and data processing setup
- **astrokat/noisediode.py**: Noise diode control patterns and triggering
- **astrokat/simulate.py**: Observation simulation and planning utilities
- **astrokat/utility.py**: Common utilities for time conversion, YAML parsing, LST calculations

### Key Design Patterns
- Dual-mode operation: Live telescope control (with katcorelib) or simulation mode (standalone)
- YAML-based observation file format for defining observation plans
- Target objects use katpoint for coordinate transformations and ephemeris calculations
- Observatory configuration automatically detects MeerKAT array setup via katconf when available

### Scripts and CLI Tools
Located in `scripts/`:
- **astrokat-observe.py**: Main observation execution script
- **astrokat-targets.py**: Target visibility and planning utilities
- **astrokat-coords.py**: Coordinate conversion and validation tools
- **astrokat-catalogue2obsfile.py**: Convert target catalogues to observation files
- **astrokat-lst.py**: LST calculation utilities

### Configuration Files
- **obs_plans/**: Template observation files and correlator configurations
- **catalogues/**: Standard calibrator catalogues for L-band and U-band
- **config/**: MeerKAT antenna configuration files

### Test Structure
Tests are organized by functionality:
- **test_offline_observe.py**: Offline observation planning tests
- **test_scans.py**: Scan pattern validation tests
- **test_simulate.py**: Simulation framework tests
- **test_nd_timings.py**: Noise diode timing tests
- Test data in subdirectories (test_obs/, test_scans/, etc.) with YAML observation files

### Dependencies
Core: astropy, pyephem, katpoint, matplotlib, numpy, pyyaml
Live system: katcorelib, katconf (for telescope control)
Development: coverage, mock, nose, tox

### Testing Notes
- Uses nose test framework with XML output for CI
- Tests run against both Python 2.7 and 3.6 via tox
- Coverage reports generated automatically
- Many tests use simulation mode with YAML configuration files in test/ subdirectories