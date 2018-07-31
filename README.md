# astrokat
General observational tools for astronomy observations with the MeerKAT telescope

### Basic procedure for creating an observation configuration file
* create an observation catalogue with observation sources   
```Name, tags, RA, Decl```

* convert catalogue CSV file to input observation configuration file   
```python catalogue2config.py -i <abs_path/filename>.csv -o config.yaml```   

* edit configuration file if needed for more complex observations

* verify observation configuration file before observation planning   
```python readconfig.py config.yaml```
