# astrokat
General observational tools for astronomy observations with the MeerKAT telescope

### Basic procedure for creating an observation configuration file
* create an observation catalogue with observation sources   
```Name, tags, RA, Decl```

* convert catalogue CSV file to input observation configuration file   
```python catalogue2config.py -i <abs_path/filename>.csv -o config.json```   
```python catalogue2config.py -i ../catalogues/OH_periodic_masers_and_calibrators.csv -o ../config/OH_periodic_masers.prms```

* edit configuration file if needed for more complex observations

* verify observation configuration file before observation planning   
```python readconfig.py ../config/OH_periodic_masers_cmplx.prms```
