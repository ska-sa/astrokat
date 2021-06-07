#! /bin/bash

## Standard checks to run after new development to ensure typical conversion are still successful

RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW='\033[0;33m'
NOCOLOR="\033[0m"

CMD="astrokat-catalogue2obsfile.py"

echo
$CMD --infile test_convert/targets.csv --target-duration 10
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi


echo
$CMD --infile test_convert/two_calib.csv --integration-period 4 --product c856M4k --primary-cal-duration 300
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi


echo
$CMD --infile test_convert/image.csv --target-duration 180 --primary-cal-duration 300 --secondary-cal-duration 65 --primary-cal-cadence 1800 --max-duration 3600
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi


echo
$CMD --infile test_convert/OH_periodic_masers.csv --target-duration 600 --primary-cal-duration 300 --secondary-cal-duration 60 --product c856M32k
ret=$?
if [ "0" -eq "$ret" ]
then
    echo -e "${GREEN} Success ${NOCOLOR}"
else
    echo -e "${RED} Failure ${NOCOLOR}"
    exit
fi

# -fin-

