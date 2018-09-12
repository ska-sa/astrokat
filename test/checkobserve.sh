#! /bin/bash

echo
python observe.py --profile ../config/targets.yaml
echo
python observe.py --profile ../config/two_calib.yaml

echo
python observe.py --profile ../config/drift_targets.yaml
echo
python observe.py --profile ../config/image_sim.yaml
echo
python observe.py --profile ../config/image.yaml
echo
python observe.py --profile ../config/OH_periodic_masers.yaml

# -fin-

