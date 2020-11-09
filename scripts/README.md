## Available functionality
Helper scripts are stand alone scripts that implement AstroKAT functionality to perform some calculation that may be useful to an astronomer when setting up or planning an observation.
Adding a python script and or notebook to the planning scripts does not need test functionality, but must come with an implementation example for an astronomer to evaluate the pull request.


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


### Convenience calculator converting galactic coordinates to ICRS frame
Utility script that takes in galactic coordinates and converts it to equatorial coordinates
```
astrokat-coords.py --galactic T11R00C02 21h51m30.37s +00d59m15.56s
```

Usage details can be found on the
[Galactic coordinates to ICRS](https://github.com/ska-sa/astrokat/wiki/Galactic-coordinates-to-ICRS)    
wiki page

An online notebook is also available: 
`astrokat-coords.ipynb`


### Typical LST calculations
Most often given a target you need the rise and set times for an anticipated date

* Calculate per target LST rise and set times
`astrokat-lst.py --target 17:22:27.46877 -38:12:09.4023`
* Return the time (UTC) of a given LST (such as rise time) for a given date
`astrokat-lst.py --lst 10.6 --date 2018-08-06`

Usage details can be found on the
[MeerKAT LST tools](https://github.com/ska-sa/astrokat/wiki/MeerKAT-LST-tools)
wiki page

An online notebook is also available: 
`astrokat-lst.ipynb`



-fin-
