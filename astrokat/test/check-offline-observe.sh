#! /bin/bash

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

INPUT=(
targets-sim
two-calib-sim
drift-targets-sim
raster-scans-sim
image-single-sim
image-sim
image-cals-sim)

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

