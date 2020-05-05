#! /bin/bash

## standard checks to run after editing to verify that the basic observations will still succeed

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

INPUT=(
# set pattern all antennas in the array
nd-pattern-sim
# set pattern for only 2 antennas and apply user defined lead time
nd-pattern-ants
# # deactivate noise diode for target
# nd-pattern-plus-off
# # set trigger time to shorter and longer than lead time
# nd-trigger
)

for infile in ${INPUT[@]}
do
    echo
    CMD="astrokat-observe.py --yaml test_nd/$infile.yaml"
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

