#! /bin/bash

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

INPUT=(
# input target coordinate formats: equatorial, horizontal and galactic
targets-sim
# observe list of only calibrators same as list of targets
two-calib-sim
# only perform observation target list once
image-single-sim
# continue observation of target for a given duration
image-sim
# more calibrator imaging
image-cals-sim
# exit when targets are below horizon
below-horizon-sim)

for infile in ${INPUT[@]}
do
    echo
    CMD="astrokat-observe.py --yaml test_obs/$infile.yaml"
    echo -e "${YELLOW} Testing: $CMD ${NOCOLOR}"
    if $CMD
    then
        echo -e "${GREEN} Success ${NOCOLOR}"
    else
        echo -e "${RED} Failure ${NOCOLOR}"
        break
    fi
done


# -fin-

