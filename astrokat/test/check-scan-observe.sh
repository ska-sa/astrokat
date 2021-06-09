#! /bin/bash

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

INPUT=(
# possible drift scan observation options
drift-targets-sim
# summary of all possible scans
scans-sim
# combinations of track, scan and raster scan
raster-scans-sim
# some additional combinations
targets-scan-sim
# combinations of scans and noise diodes
scan-with-nd-pattern
scan-with-nd-trigger
)


for infile in ${INPUT[@]}
do
    echo
    CMD="astrokat-observe.py --yaml test_scans/$infile.yaml"
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

