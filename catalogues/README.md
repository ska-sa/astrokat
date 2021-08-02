## Update catalogues
Update catalogues for katconfig repo for offline planning with AstroKAT

If you have access: update the catalogues to ensure they are up to date with katconfig    
`git clone https://github.com/ska-sa/katconfig.git`

Update astrokat catalogues manually
```
git clone https://github.com/ska-sa/astrokat.git
cd astrokat/catalogues
for file in ../../katconfig/user/catalogues/*calibrators.csv ; do echo $file ; cp $file bak/ ; cp $file . ; done
```

OR

Edit and run bash script for all in one solution:    
`./update_catalogues.sh <path to katconfig user catalogues>`    
e.g.    
`./update_catalogues.sh ../../katconfig/user/catalogues/`

Note: the script assumes the MeerKAT catalogue naming convention as described in the 
[MeerKAT calibrators and CSV catalogues](https://github.com/ska-sa/astrokat/wiki/MeerKAT-calibrators-and-CSV-catalogues)
wiki page

-fin-
