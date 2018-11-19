#! /bin/bash

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

INPUT=(
targets-sim
two-calib-sim
nd-pattern-sim
nd-pattern-plus-off
nd-pattern-cycle
nd-pattern-ants
drift-targets-sim
raster-scans-sim
image-single-sim
image-sim)

for infile in ${INPUT[@]}
do
    echo
    CMD="python astrokat-observe.py --observer werner --yaml test_obs/$infile.yaml"
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

