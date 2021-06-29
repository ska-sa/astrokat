#!/usr/bin/env python
"""MeerKAT LST calculation helper tools."""

import argparse
import ephem
import katpoint
import re
import sys
import time

from astrokat import Observatory, lst2utc, __version__
from datetime import datetime


def cli(prog):
    """LST calculations for MeerKAT telescope."""
    usage = "{} [options]".format(prog)
    description = "LST calculations for MeerKAT telescope"

    parser = argparse.ArgumentParser(usage=usage, description=description)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--date",
        type=str,
        help="Provides the LST for MeerKAT at a given UCT "
             "datetime (format 'YYYY-MM-DD HH:MM')",
    )
    parser.add_argument(
        "--lst",
        type=float,
        help="Provides MeerKAT UTC date time for desired "
             "LST hour",
    )
    parser.add_argument(
        "--target",
        nargs=2,
        type=str,
        metavar=("RA", "Decl"),
        help="Returns MeerKAT LST range for a celestial "
             "target with coordinates HH:MM:SS DD:MM:SS",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Only shows the LST for script parsing"
    )

    return parser.parse_args()


def longformat_date(date_str):
    r = re.compile(r'^(\d{4})-(0[1-9]|1[0-2]|[1-9])'
                   r'-(([12]\d|0[1-9]|3[01])|[1-9])'
                   r'[tT\s]'
                   r'([01]\d|2[0-3])'
                   r'\:([0-5]\d)'
                   r'(\:([0-5]\d))?$')

    m = r.match(date_str)
    if m is None:
        # date only
        if len(date_str.split(' ')) == 1:
            date_str = '{} 00:00'.format(date_str)
        else:
            date_str = '{}:00'.format(date_str)
    m = r.match(date_str)
    Y, M, _, d, H, m, _, s = m.groups()
    if s is not None:
        date_str = '{}-{}-{} {}:{}'.format(Y, M, d, H, m)
    return date_str


def lst2datetime(lst, date):
    date_str = longformat_date(date)
    utc_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    date_lst = lst2utc(lst, Observatory().location, date=utc_datetime)
    return ("{} {} LST corresponds to {}Z UTC"
            .format(date, lst, date_lst))


def date2lst(utc_datetime, observer=None):
    if observer is None:
        observer = Observatory().observer
    observer.date = ephem.Date(utc_datetime)
    return ("At {}Z MeerKAT LST will be {}"
            .format(observer.date, observer.sidereal_time()))


def targetlst(target_str):
    target = ",".join(["radec target"] + target_str)
    target = katpoint.Target(target).body
    rise_lst, set_lst = Observatory().target_rise_and_set_times(target)
    return ("Target ({}) rises at LST {} and sets at LST {}"
            .format(" ".join(target_str),
                    rise_lst,
                    set_lst))


def main(args):
    """Calculates target rise and set LST."""
    observer = Observatory().observer
    if args.date:
        date_str = longformat_date(args.date)
    else:
        date_str = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
    utc_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

    if args.target:
        target = [target.strip() for target in args.target]
        return_str = targetlst(target)

    elif args.date and not args.lst:
        return_str = date2lst(utc_datetime, observer=observer)

    elif args.lst:
        return_str = lst2datetime(args.lst, args.date)
    else:
        # default results is to return the current LST at MeerKAT
        return_str = "Current clock times at MeerKAT:\n"
        return_str += ("Now is {}Z UTC and {} LST"
                       .format(observer.date,
                               observer.sidereal_time()))

    if args.simple:
        print(ephem.hours(observer.sidereal_time()))
    else:
        print(return_str)


if __name__ == "__main__":
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if len(arg) < 2:
            continue
        if (arg[0] == "-") and arg[1].isdigit():
            sys.argv[i] = " " + arg
    main(cli(sys.argv[0]))


# -fin-
