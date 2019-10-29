#! /bin/bash

## Test astrokat basic calibrator selection functionality

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[0;33m"
NOCOLOR="\033[0m"

CMD="astrokat-cals.py --cat-path ../../catalogues/"
date='2018-08-06 12:34'

echo
name='NGC641_03D03'
ra='01:38:13.250'
dec='-42:37:41.000'
$CMD --target "$name" $ra $dec --cal-tags gain bp pol flux delay --pi No_One --contact dummy@ska.ac.za --text-only  --datetime "$date"
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
infile='test_cals/sample_targetlist_for_cals.csv'
outfile='test_cals/AR1_mosaic_NGC641.csv'
$CMD --cal-tags gain bp --outfile $outfile --infile $infile --text-only  --datetime "$date"
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
$CMD --view $outfile --text-only --solar-angle=55 --datetime "$date" --lst
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

echo
infile='test_cals/sample_targetlist_for_cals.yaml'
$CMD --view $infile --text-only  --datetime "$date"
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

# -fin-
