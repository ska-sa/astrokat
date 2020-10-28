# AstroKAT
General observation and planning tools for the MeerKAT telescope.    
Most requirements and implementations are derived from usage cases provided by the MeerKAT Commissioning team.

AstroKAT user documentation can be found on the [wiki pages](https://github.com/ska-sa/astrokat/wiki).
These pages specifying terminology and functionality that is incorporated into the observation framework in
relation to observational requirements.


## Usage

Run AstroKAT helper scripts directly from GitHub using Google COLAB.   
Find available interfaces in notebooks directory.

AstroKAT scripts can be run either as command line utilities (see `pip` installation instructions below), or from GitHub via the Google COLAB notebook interface.
See wiki page `Table of Contents` under the `Input and planning utilities` heading for examples.


## Installation
Python package, pip installation:    
`
pip install git+https://github.com/ska-sa/astrokat.git
`

Dependencies:    
* The following python packages are assumed:
`numpy`, `matplotlib`
* The following python packages are required by the framework:
`pyyaml`, `pyephem`, `katpoint`, `astropy`


## Development
* Clone repository    
`git clone https://github.com/rubyvanrooyen/astrokat.git`    
`cd astrkat`
* Python virtual environment setup    
`python3 -m venv env`    
`source /env/bin/activate`    
`pip install -e .`

-fin-
