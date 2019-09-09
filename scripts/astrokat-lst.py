#!/usr/bin/env python
"""MeerKAT LST calculation helper tools."""

import argparse
import ephem
import katpoint
import sys
import time

from astrokat import Observatory, lst2utc, __version__
from datetime import datetime


def cli(prog):
    """LST calculations for MeerKAT telescope."""
    usage = "{} [options]".format(prog)
    description = "LST calculations for MeerKAT telescope"

    parser = argparse.ArgumentParser(
            usage=usage,
            description=description)
    parser.add_argument(
            "--version",
            action="version",
            version=__version__)
    parser.add_argument(
            "--date",
            type=str,
            help="Provides the MeerKAT UTC given an LST at a"
                 "given date (format 'YYYY-MM-DD')")
    parser.add_argument(
            "--lst",
            type=float,
            help="Provides MeerKAT UTC date time for desired"
                 "LST hour")
    parser.add_argument(
            "--target",
            nargs=2,
            type=str,
            metavar=("RA", "Decl"),
            help="Returns MeerKAT LST range for a celestial"
                 "target with coordinates HH:MM:SS DD:MM:SS")
    parser.add_argument(
            "--utc",
            type=str,
            help="Provides the LST for MeerKAT at a given UCT"
                 "datetime (format 'YYYY-MM-DD HH:MM')")
    parser.add_argument(
            "--simple",
            action="store_true",
            help="Only shows the LST for script parsing")

    return parser.parse_args()


def main(args):
    """Calculates target rise and set LST."""
    observer = Observatory().observer

    if args.target:
        args.target = [target.strip() for target in args.target]
        target = ','.join(["radec target"] + args.target)
        target = katpoint.Target(target).body
        rise_lst = Observatory()._ephem_risetime_(target)
        set_lst = Observatory()._ephem_settime_(target)
        return_str = "Target ({}) rises at LST {} and sets at LST {}".format(
                ' '.join(args.target),
                rise_lst,
                set_lst)

    elif args.utc and not args.lst:
        utc_datetime = datetime.strptime(args.utc, "%Y-%m-%d %H:%M")
        observer.date = ephem.Date(utc_datetime)
        return_str = "At {}Z MeerKAT LST will be {}".format(
            observer.date,
            observer.sidereal_time())

    elif args.lst:
        date_str = args.utc if args.utc else time.strftime("%Y-%m-%d",
                                                           time.gmtime())
        date = datetime.strptime(date_str, "%Y-%m-%d")
        date_lst = lst2utc(args.lst, Observatory().location, date=date)
        return_str = "{} {} LST corresponds to {}Z UTC".format(
                date_str,
                args.lst,
                date_lst)

    else:
        # default results is to return the current LST at MeerKAT
        return_str = "Current clock times at MeerKAT:\n"
        return_str += "Now is {}Z UTC and {} LST".format(
                observer.date,
                observer.sidereal_time())

    if args.simple:
        print(ephem.hours(observer.sidereal_time()))
    else:
        print(return_str)


if __name__ == "__main__":
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg
    main(cli(sys.argv[0]))


# -fin-
