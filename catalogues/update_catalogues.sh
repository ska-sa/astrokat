#! /bin/bash

#Usage: ./update_catalogues.sh ../../katconfig/user/catalogues/

all_calibrators='*calibrators.csv'
l_band_calibrators='Lband-*calibrators.csv'

# katconfig catalogues
katconfig=$1

# current date as yyyy-mm-dd
today=$(date '+%Y-%m-%d')
# temp backup
mkdir bak/$today

# update with current catalogues from katconfig
for file in $l_band_calibrators
do
    echo $file
    cp $file bak/$today
    cp $katconfig/$file .
done

# -fin-
