## Basic bash integration tests to check that all parts of the functionality is still working after
development.

* Test examples getting suggested calibrators    
`./check-cals-select.sh`

* Test examples converting CSV catalogues to observation YAML files    
`./check-csv-convert.sh`

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
