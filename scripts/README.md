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
[Galactic coordinates to ICRS](https://github.com/ska-sa/astrokat/wiki/Galactic-coordinates-to-ICRS)    
`astrokat-coords.ipynb`

-fin-
