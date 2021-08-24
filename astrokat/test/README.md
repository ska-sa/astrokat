# AstroKAT development tests
Development tests must by applied at different levels when adding new features.
Starting with some command line bash/Jenkins tests that ignores telescope settings and uses the
`ephem`/`astropy` libraries to simulate observation runs and timings.   
Followed by SDP dry-run simulation on a CAM VM such as `devcomm` to verify the similar progress output
as the simulations, but this time with simulated telescope systems included.

Tests related to the AstroKAT library functions are represented in individual unit tests.
It is advised that added functionality be accompanied by at least one unit test describing known input
and expected output.

Some existing functionality, such as the notebooks and helper scripts, do not have explicit unit
tests.
These are generally verified by the developer using visual verification of the output provided when
executed.
Developers working to extent this functionality should note the various test scripts related to integration level bash scripts can be found on the `rvr_obs_devel`
branch.


## Unit tests
Currently, per module tests are grouped in test functions basically names: `test_<name>_<testfunction>.py`

An example command to invoke one of these tests during development:
```
python -m unittest astrokat.test.test_offline_observe.TestAstrokatYAML.test_targets_sim
```


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
