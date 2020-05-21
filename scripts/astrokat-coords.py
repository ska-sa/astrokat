#!/usr/bin/env python
"""MeerKAT galactic to celestial coordinate conversion tool

Returns CSV target catalogue for OPT input

"""

from __future__ import print_function
from astropy import units as u
from astropy.coordinates import Galactic, ICRS
from astropy.coordinates import SkyCoord

import argparse
import sys

from astrokat import __version__


def cli(prog):
    usage = "{} [options]".format(prog)
    description = 'Coordinate conversion helper script for MeerKAT telescope'

    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=__version__)
    parser.add_argument(
        '--radec',
        nargs=3,
        metavar=('NAME', 'RA', 'DEC'),
        help='Display celestial coordinates in string'
             ' and degree float formats.')
    parser.add_argument(
        '--galactic',
        nargs=3,
        metavar=('NAME', 'l', 'b'),
        help='Display galactic coordinates in string'
             ' and degree float formats, as well as'
             ' transformed to (ra, dec)')
    parser.add_argument(
        '--catalogue',
        type=str,
        help='CSV catalogue to generate radec catalogue from')
    parser.add_argument(
        '--outfile',
        type=str,
        help='CSV radec catalogue filename')
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output for debug and verification')

    args = parser.parse_args()
    if args.outfile is None:
        args.outfile = 'galactic_as_equitorial.csv'
    return args


def gal2icrs_skycoord(coord_x, coord_y):
    """Create galactic SkyCoord and transformed ICRS SkyCoord
       galactic longitude l = coord_x
       galactic latitude b = coord_y
    """
    gal_coord = SkyCoord(l=coord_x,  # noqa
                         b=coord_y,
                         frame=Galactic)
    return gal_coord, gal_coord.transform_to(ICRS)


def icrs_skycoord(coord_x, coord_y):
    """Create ICRS SkyCoord"""
    if len(coord_x.split(':')) > 1:
        coord_x += 'h'
    if len(coord_y.split(':')) > 1:
        coord_y += 'd'
    return SkyCoord(ra=coord_x,
                    dec=coord_y,
                    frame=ICRS)


def format_str(astropy_x, astropy_y):
    """ICRS string format HH:MM:SS.f, DD:MM:SS.f"""
    x_str = astropy_x.to_string(unit=u.hourangle,
                                sep=':',
                                precision=4,
                                pad=True)
    y_str = astropy_y.to_string(sep=':',
                                precision=4,
                                alwayssign=True,
                                pad=True)
    return x_str, y_str


def coord_str(astropy_x, astropy_y):
    x_str, y_str = format_str(astropy_x, astropy_y)
    str_format = "({}, {})".format(str(x_str), str(y_str))
    float_format = "({:.4f}h, {:.4f}d)".format(astropy_x.hour,
                                               astropy_y.degree)
    degree_format = "({:.4f}d, {:.4f}d)".format(astropy_x.degree,
                                                astropy_y.degree)
    return '{} = {} = {}'.format(str_format,
                                 float_format,
                                 degree_format)


def display_radec(astropy_radec, name=None):
    if name is not None:
        print('Target {}'.format(name))
    print('(RA, DEC) coordinates')
    print('\t{}'.format(coord_str(astropy_radec.ra,
                                  astropy_radec.dec)))


def display_galactic(astropy_gal, name=None):
    if name is not None:
        print('Target {}'.format(name))
    print('Galactic coordinates')
    print('\t{}'.format(coord_str(astropy_gal.l,
                                  astropy_gal.b)))


def csv_entry(radec_coord, name='target'):
    x_str, y_str = format_str(radec_coord.ra, radec_coord.dec)
    return '{}, radec target, {}, {}\n'.format(name,
                                               x_str,
                                               y_str)


def gal2radec(infile, verbose=False):
    """Read all targets in catalogue and make all ICRS in returned catalogue"""
    with open(infile, 'r') as fin:
        targets = fin.readlines()

    if verbose:
        print('\nInput file')
        for target in targets:
            print(target.strip())

    cat_entry = ''
    for target in targets:
        if target[0] == '#':  # comment
            continue
        [name, tag, coord_x, coord_y] = [item.strip()
                                         for item in target.strip().split(',')]
        if 'radec' in tag:
            radec_coord = icrs_skycoord(coord_x, coord_y)
        else:
            [gal_coord,
             radec_coord] = gal2icrs_skycoord(coord_x, coord_y)

        cat_entry += csv_entry(radec_coord, name=name)

    return cat_entry


def main(args):
    if args.radec is not None:
        radec_coord = icrs_skycoord(args.radec[1], args.radec[2])
        display_radec(radec_coord, name=args.radec[0])
        # exit here
        raise SystemExit
    elif args.galactic is not None:
        [gal_coord,
         radec_coord] = gal2icrs_skycoord(args.galactic[1],
                                          args.galactic[2])
        display_galactic(gal_coord, name=args.galactic[0])
        display_radec(radec_coord)
        cat_entry = csv_entry(radec_coord, name=args.galactic[0])
    elif args.catalogue is not None:
        cat_entry = gal2radec(args.catalogue,
                              verbose=args.verbose)
    else:
        # nothing to do
        raise SystemExit

    with open(args.outfile, 'w') as fout:
        fout.write(cat_entry)

    print('\nEquatorial catalogue file created: {}'.format(args.outfile))
    if args.verbose:
        print('Catalogue file entries')
        print(cat_entry)


if __name__ == '__main__':
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg
    main(cli(sys.argv[0]))

# -fin-
