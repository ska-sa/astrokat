#! /bin/bash

echo
python catalogue2config.py --catalogue ../catalogues/targets.csv --product c856M4k --target-duration 10
echo
python catalogue2config.py --catalogue ../catalogues/two_calib.csv --dump-rate 4 --product c856M4k --bpcal-duration 30

echo
python catalogue2config.py --catalogue ../catalogues/drift_targets.csv --dump-rate 2 --noise-source 0.1 -1 --target-duration 180 --drift-scan
echo
python catalogue2config.py --catalogue ../catalogues/image.csv --target-duration 180 --bpcal-duration 60 --gaincal-duration 30 --bpcal-interval 1800 --product bc856M4k
echo
python catalogue2config.py --catalogue ../catalogues/image.csv --target-duration 180 --bpcal-duration 300 --gaincal-duration 65 --gaincal-interval 600 --bpcal-interval 1800 --product bc856M4
echo
python catalogue2config.py --catalogue ../catalogues/OH_periodic_masers.csv --target-duration 600 --bpcal-duration 300 --gaincal-duration 60 --product c856M32k

# -fin-

