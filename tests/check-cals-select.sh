#! /bin/bash

## Test astrokat basic calibrator selection functionality

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[0;33m"
NOCOLOR="\033[0m"

echo
python astrokat-cals.py --target 'NGC641_03D03' '01:38:13.250' '-42:37:41.000' --cal-tags gain bp pol flux delay --pi No_One --contact dummy@ska.ac.za --text-only --cat-path 'catalogues/' --datetime '2018-08-06 12:34'
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
python astrokat-cals.py --cat-path catalogues --cal-tags gain bp --outfile test_cals/AR1_mosaic_NGC641.csv --infile test_cals/sample_targetlist_for_cals.csv --text-only
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
python astrokat-cals.py --view test_cals/AR1_mosaic_NGC641.csv --text-only --solar-angle=55 --datetime '2018-04-06 12:34'
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
python astrokat-cals.py --view test_cals/sample_targetlist_for_cals.yaml --text-only
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

# -fin-
