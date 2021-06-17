# AstroKAT development tests
Development tests must by applied at different levels when adding new features.
Starting with some command line bash/Jenkins tests that ignores telescope settings and uses the
`ephem`/`astropy` libraries to simulate observation runs and timings.   
Followed by SDP dry-run simulation on a CAM VM such as `devcomm` to verify the similar progress output
as the simulations, but this time with simulated telescope systems included.


## Helper scripts
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


## Development simulations
Scan type observations are not operationally supported and added on a best effort for the astronomer
to verify
Basic YAML variations for scans are provided and a bash script that show anticipated behaviour for
checking    
`./check-scan-observe.sh`


## Offline simulations
Basic bash integration tests to check that all parts of the functionality is still working after
development.

When using the bash integration tests, follow the same SOP as for the helper scripts, visually
comparing the resulting output between the site installed branch and your development branch.

* Some test examples of simulated observations    
`./check-offline-observe.sh`    
or for testing    
`./check-offline-observe.sh > output.txt`    

* Noise diode setting example files    
`./check-nd-timings.sh`    
or for testing    
`./check-nd-timings.sh > output.txt`    


## VM simulations
If access to a SARAO GUI mockup/VM is available some CAM dry-runs with simulated telescope systems can
be used to double check the offline simulations

Building schedule blocks using `IPython` interface
```
obs.sb.new(owner='AstroKAT')
obs.sb.type=katuilib.ScheduleBlockTypes.OBSERVATION
obs.sb.antenna_spec='available'
obs.sb.controlled_resources_spec='cbf,sdp'
obs.sb.description='AstroKAT development tests'
obs.sb.proposal_id='devel'
```

Example test YAML test files
```
obs.sb.instruction_set="run-obs-script /home/kat/usersnfs/framework/astrokat/scripts/astrokat-observe.py --yaml /home/kat/usersnfs/ruby/test/nd-pattern-sim.yaml"
obs.sb.desired_start_time='2019-11-14 07:00:00'
```
```
obs.sb.instruction_set="run-obs-script /home/kat/usersnfs/framework/astrokat/scripts/astrokat-observe.py --yaml /home/kat/usersnfs/ruby/test/nd-trigger-long.yaml"
obs.sb.desired_start_time='2019-11-14 07:00:00'
```
```
obs.sb.instruction_set="run-obs-script /home/kat/usersnfs/framework/astrokat/scripts/astrokat-observe.py --yaml /home/kat/usersnfs/ruby/test/scans-sim.yaml"
obs.sb.desired_start_time='2018-10-31 14:00:00'
```
```
obs.sb.instruction_set="run-obs-script /home/kat/usersnfs/framework/astrokat/scripts/astrokat-observe.py --yaml /home/kat/usersnfs/ruby/test/targets-sim.yaml"
obs.sb.desired_start_time='2018-07-23 18:00:00'
```
```
obs.sb.instruction_set="run-obs-script /home/kat/usersnfs/framework/astrokat/scripts/astrokat-observe.py --yaml /home/kat/usersnfs/ruby/test/image-sim.yaml"
obs.sb.desired_start_time='2019-02-11 02:10:47'
```

Add schedule block to mock GUI interface
```
obs.sb.to_defined()
obs.sb.to_approved()
obs.sb.unload()
```

-fin-
