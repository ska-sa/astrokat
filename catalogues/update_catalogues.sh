#! /bin/bash

#Usage: ./update_catalogues.sh ../../katconfig/user/catalogues/

if [ "$#" -lt 1 ]
then
    echo "Usage: ./update_catalogues.sh <path to katconfig user catalogues>"
    echo "  e.g: ./update_catalogues.sh ../../katconfig/user/catalogues/"
    exit
fi

# assuming naming convention
# <L/U>band-<calibrator_classification>-calibrators.csv
# e.g. L-band calibrators = 'Lband-*-calibrators.csv'
# e.g. UHF-band calibrators = 'Uband-*-calibrators.csv'
all_calibrators='*calibrators.csv'

# katconfig catalogues
katconfig=$1

# current date as yyyy-mm-dd
today=$(date '+%Y-%m-%d')
# temp backup
mkdir bak/$today

# update with current catalogues from katconfig
for file in $katconfig/$all_calibrators
do
    echo $file
    cp $file bak/$today
    cp $file .
done

# -fin-
