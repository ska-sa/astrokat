# AstroKAT development tests
Development tests must by applied at different levels when adding new features.
Starting with some command line bash/Jenkins tests that ignores telescope settings and uses the
`ephem`/`astropy` libraries to simulate observation runs and timings.   
Followed by SDP dry-run simulation on a CAM VM such as `devcomm` to verify the similar progress output
as the simulations, but this time with simulated telescope systems included.


## Helper scripts`
Helper scripts are provided to the users in the `scripts` directory and notebook interfaces through
COLAB.
These scripts do not form part of the `AstroKAT` library, but while in use and when updated, these
should at least pass the basic command line tests

Simply run the bash test setup scripts and capture the output for comparison between developments.
There are no hard and fast rules to check, visual inspection evaluating expectation is main form of
verification.

Basic SOP:
* Run bash test scripts on release branch currently on site
and capture output to a dated text file
* Rerun bash test scripts on feature branch and capture output
* Run a basic `diff <site branch file> <devel branch file>` to compare output

List of helper test scripts:
* Test examples getting suggested calibrators    
`./check-cals-select.sh > output.txt`
* Test examples converting CSV catalogues to observation YAML files    
`./check-csv-convert.sh > output.txt`


## Offline simulations
Basic bash integration tests to check that all parts of the functionality is still working after
development.

* Some test examples of simulated observations    
`./check-offline-observe.sh`

* Noise diode setting example files    
`./check-nd-timings.sh`


## Use python unit tests
```
pip install mock
pip install tox
```

Running individual test
```
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_targets_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_two_calib_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_image_single_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_image_sim
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_below_horizon
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_targets_sim
```
Using tox
```
LC_ALL=C test_flags=astrokat tox -e py27
```

-fin-
