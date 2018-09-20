import argparse
import ephem
import katpoint
import sys
import time
import numpy

from datetime import datetime

from astrokat import Observatory


import matplotlib.pyplot as pyplot
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, MultipleLocator
from matplotlib.dates import DateFormatter
from matplotlib.font_manager import FontProperties


def coords(value):
    values = value.split()
    if len(values) != 2:
        raise argparse.ArgumentError
    values = map(str, values)
    return values

def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options]".format(prog)
    description = 'LST calculations for MeerKAT telescope'

    parser = argparse.ArgumentParser(
            usage=usage,
            description=description)
    parser.add_argument(
            '--version',
            action='version',
            version=version)
    parser.add_argument(
            '--utc',
            type=str,
            help="Provides the LST for MeerKAT at a given UCT datetime (format 'YYYY-MM-DD HH:MM')")
    parser.add_argument(
            '--current',
            action='store_true',
            help='Provides the current MeerKAT LST')
    parser.add_argument(
            '--lst',
            type=int,
            help='Provides UTC date time for MeerKAT LST hour')
    parser.add_argument(
            '--target',
            type=coords,  # handle negative values
            help="Returns MeerKAT LST range for a celestial target (format 'RA Decl')")
    parser.add_argument(
            '--catalogue',
            type=str,
            help="Display target elevation over LST range")

    return parser.parse_args()


def LST2UTC(req_lst, date):
    cat = katpoint.Catalogue(add_specials=True)
    cat.antenna = katpoint.Antenna(Observatory().location)
    target = cat['Zenith']
    date = datetime.strptime(date, '%Y-%m-%d %H:%M')
    time_range = katpoint.Timestamp(time.mktime(date.timetuple())).secs + numpy.arange(0, 24.*3600., 60)
    lst_range = katpoint.rad2deg(target.antenna.local_sidereal_time(time_range)) / 15
    lst_idx = numpy.abs(lst_range-req_lst).argmin()
    return time_range[lst_idx]


def source_elevation(catalogue):
    cat = katpoint.Catalogue(file(catalogue))
    cat.antenna = katpoint.Antenna(Observatory().location)
    target = cat.targets[0]
    time_range = katpoint.Timestamp().secs + numpy.arange(0, 24. * 60. * 60., 360.)
    lst_range = katpoint.rad2deg(target.antenna.local_sidereal_time(time_range)) / 15

    # create a variety of coloured markers.  After a while the plots get really crowded,
    # but you can add on to this if you like.
    markers = []
    colors = ['b','g','r','c','m','y','k']
    pointtypes = ['o','*','x','^','s','p','h','+','D','d','v','H','d','v']
    for point in  pointtypes:
        for color in colors:
            markers.append(str(color+point))


    fig = pyplot.figure(figsize=(15,7), facecolor='white')
    ax = pyplot.subplot(111)
    pyplot.subplots_adjust(right=0.8)
    lines = list()
    labels = list()
    count = 0
    fontP = FontProperties()
    fontP.set_size('small')
    pyplot.ylim(10, 90)
    pyplot.xlim(0, 24)
    ax.xaxis.set_major_locator(MaxNLocator(24))
    minorLocator = MultipleLocator(0.25)
    ax.xaxis.set_minor_locator(minorLocator)

    for cnt, target in enumerate(cat.targets):
       elev = katpoint.rad2deg(target.azel(time_range)[1])
       myplot,= pyplot.plot(lst_range,
               elev,
               markers[cnt],
               linewidth=0,
               label=target.name)
       lines.append(myplot)
       # RPA replaced the line below with the two lines above because: http://matplotlib.org/users/legend_guide.html#adjusting-the-order-of-legend-items
       labels.append(target.name)
    pyplot.legend(lines, labels, bbox_to_anchor = (1, 1), loc = 'best',ncol=2,prop = fontP, fancybox=True)


    pyplot.ylabel('Elevation (deg)')
    pyplot.xlabel ('Local Sidereal Time (hours)')
    pyplot.title('Elevations of targets')
    pyplot.savefig('elevation_lst.png',dpi=300)
    pyplot.grid()
    pyplot.show()


def main(args):
    observer = Observatory().observer

    if args.utc and not args.lst:
        utc_datetime = datetime.strptime(args.utc, '%Y-%m-%d %H:%M')
        observer.date = ephem.Date(utc_datetime)
        print 'At {}z MeerKAT LST is {}'.format(
                observer.date,
                observer.sidereal_time())

    if args.current:
        print 'Current LST at MeerKAT {}'.format(observer.sidereal_time())

    if args.target:
        target = ','.join(['radec target'] + args.target)
        target = katpoint.Target(target).body
        rise_time = observer.next_rising(target)
        observer.date = rise_time
        rise_lst = observer.sidereal_time()
        set_time = observer.next_setting(target, start=rise_time)
        observer.date = observer.next_setting(target, start=rise_time)
        set_lst = observer.sidereal_time()
        print 'Target {} LST range {} to {}'.format(' '.join(args.target), rise_lst, set_lst)

    if args.lst:
        date = args.utc if args.utc else time.strftime('%Y-%m-%d 00:00',time.gmtime())
        utc_time = LST2UTC(args.lst, date)
        print('Your observation should start at {} UTC'.format(
            time.strftime('%Y-%m-%d %H:%M',time.gmtime(utc_time))))

    if args.catalogue:
        source_elevation(args.catalogue)


if __name__ == '__main__':
    main(cli(sys.argv[0]))


# -fin-
