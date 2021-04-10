# Helper scripts and functionality
Helper python scripts are stand alone scripts that implement AstroKAT functionality to perform some
calculation that may be useful to an astronomer when setting up or planning an observation.
These scripts are available with the AstroKAT library installation and can be executed as usual
through the command line arguments.

Alternatively, some selected functionality is available with a notebook implementation that can be
executed using Google colab, and does not need explicit installation.

Note for developers: Adding a python script and or notebook to the planning scripts does not need test
functionality, but must come with an implementation example for an astronomer to evaluate the pull
request.


# Available functionality
Using AstroKAT scripts to planning, building and simulating observations.


## Useful LST calculations
Most often given a target you need the rise and set times for an anticipated date

* Calculate per target LST rise and set times    
`astrokat-lst.py --target 17:22:27.46877 -38:12:09.4023`

* Return the time (UTC) of a given LST (such as rise time) for a given date    
`astrokat-lst.py --lst 10.6 --date 2018-08-06`

Usage details can be found on the
[MeerKAT LST tools](https://github.com/ska-sa/astrokat/wiki/MeerKAT-LST-tools)
wiki page

Or use the colab python notebook directly from GitHub:
[`astrokat_lst.ipynb`](https://github.com/rubyvanrooyen/astrokat/blob/colab_helper_interface/notebooks/astrokat_lst.ipynb)


## Convenience calculator converting galactic coordinates to ICRS frame
Current observations assumes celestial target coordinates, (Ra, Decl).
Conversion of galactic and solar body coordinates to celestial coordinates
This utility script takes in galactic coordinates and converts it to equatorial coordinates
```
astrokat-coords.py --galactic T11R00C02 21h51m30.37s +00d59m15.56s
```

Usage details can be found on the
[Galactic coordinates to ICRS](https://github.com/ska-sa/astrokat/wiki/Galactic-coordinates-to-ICRS)    
wiki page

Or use the colab python notebook directly from GitHub:
[`astrokat_coords.ipynb`](https://github.com/rubyvanrooyen/astrokat/blob/colab_helper_interface/notebooks/astrokat_coords.ipynb)


## MeerKAT calibrators
Suggested good calibrators from MeerKAT catalogues

* Using single target as input
```
astrokat-targets.py --target 'NGC641_03D03' '01:38:13.250' '-42:37:41.000' --cal-tags gain bp flux --lst  --cat-path astrokat/catalogues/
```

* Input file listing multiple pointings
```
astrokat-targets.py --cal-tags gain bp flux --infile sample_targetlist_for_cals.csv --datetime '2018-04-06 12:34' --horizon 20
```

* View a catalogue
```
astrokat-targets.py --view test_NGC641_03D03.csv --datetime '2018-04-06 12:34'
```

Usage details can be found on the
[MeerKAT calibrator selection](https://github.com/ska-sa/astrokat/wiki/MeerKAT-calibrator-selection)    
wiki page

Or use the colab python notebook directly from GitHub:
[`astrokat_targets.ipynb`](https://github.com/rubyvanrooyen/astrokat/blob/colab_helper_interface/notebooks/astrokat_targets.ipynb)


### Convert target CSV catalogue to observation YAML file
Older meerkat CSV catalogues can be converted to the newer observation file.
The older observation structure only specified time on target, time on calibrator and how often to visit the calibrator
This structure is implemented in the `astrokat-catalogue2obsfile.py` helper script to generate a draft observation file that can be updated for newer observations.

Example implementation:
```
astrokat-catalogue2obsfile.py --infile image.csv --product c856M4k --band l --integration-period 8 --target-duration 300 --max-duration 35400 --primary-cal-duration 180 --primary-cal-cadence 1800  --secondary-cal-duration 65
```

Usage details can be found on the
[Catalogues to observation files](https://github.com/ska-sa/astrokat/wiki/Catalogues-to-observation-files)
wiki page

An online notebook is also available: 
`astrokat_catalogue2obsfile.ipynb`


-fin-
