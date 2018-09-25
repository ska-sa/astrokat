## MeerKAT calibrator selection tools

import argparse
import katpoint
import numpy
import os
import sys

from astrokat import Observatory
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, MultipleLocator
from matplotlib.dates import DateFormatter
from matplotlib.font_manager import FontProperties
from matplotlib.backends.backend_pdf import PdfPages

# set up path and access method for calibrator catalogues
catalogue_path = 'katconfig/user/catalogues'
try:
    import katconf
except ImportError:
    pass  # not on live system


def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options]".format(prog)
    description = 'Calibrator selection for MeerKAT telescope'

    parser = argparse.ArgumentParser(
            usage=usage,
            description=description)
    parser.add_argument(
            '--version',
            action='version',
            version=version)
    parser.add_argument(
            '--pi',
            type=str,
            help="\
Name of principle investigator or designated project leader")
    parser.add_argument(
            '--contact',
            type=str,
            help="\
PI contact details, such as email address or phone number")
    parser.add_argument(
            '--prop-id',
            type=str,
            help="\
Proposal ID")
    parser.add_argument(
            '--calibrators',
            type=str,
            nargs='+',
            metavar='<tag>',
            help='\
List of tags for types of calibrators to provide per target: \
gain, bandpass, flux, polarisation.')
    group = parser.add_argument_group(
title="Observation target specification (*required*)",
description = "Multiple targets are added using a catalogue file, " \
"while for a single target a quick command line option is also available. " \
"Note: Simultaneous use of a catalogue and input target is not allowed.")
    ex_group = group.add_mutually_exclusive_group(required=True)
    ex_group.add_argument(
            '--catalogue',
            type=str,
            help='\
Observation catalogue CSV file for output or view')
    ex_group.add_argument(
            '--target',
            nargs=3,
            type=str,
            metavar=('Name', 'RA', 'Decl'),
            help='\
Returns MeerKAT LST range for a celestial target with coordinates \
HH:MM:SS DD:MM:SS')

    group = parser.add_argument_group(
title="Catalogue output options",
description = "Options to view and output suggested observation catalogue")
    group.add_argument(
            '--view',
            action='store_true',
            help='\
Display catalogue source elevation over time')
    group.add_argument(
            '--catalogue-path',
            type=str,
            default='.',  # working dir
            help='\
Path to write observation CSV file')
    group.add_argument(
            '--report',
            action='store_true',
            help='\
Display catalogue source elevation over time')

    return parser.parse_args()

# Generates a plot of source elevation over LST range for all sources in catalogue
def source_elevation(catalogue, location, report=False):
    catalogue.antenna = katpoint.Antenna(location)
    target = catalogue.targets[0]
    now_timestamp = katpoint.Timestamp()
    time_range = now_timestamp.secs + numpy.arange(0, 24. * 60. * 60., 360.)
    timestamps = [datetime.utcfromtimestamp(ts) for ts in time_range]
    lst_range = katpoint.rad2deg(target.antenna.local_sidereal_time(time_range)) / 15

    if report:
        fig = plt.figure(figsize=(11, 8), facecolor='white')
        ax = plt.subplot(312)
    else:
        fig = plt.figure(figsize=(15,7), facecolor='white')
        ax = plt.subplot(111)
    plt.subplots_adjust(right=0.8)
    lines = list()
    labels = list()
    fontP = FontProperties()
    fontP.set_size('small')

    for cnt, target in enumerate(catalogue.targets):
       elev = katpoint.rad2deg(target.azel(time_range)[1])
       myplot,= plt.plot_date(
               timestamps,
               elev,
               fmt = '.',
               linewidth=0,
               label=target.name)
       lines.append(myplot)
       labels.append(target.name)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(24),interval=1))
    labels = ax.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=10)
    plt.ylim(20, 90)
    plt.grid()
    plt.legend()
    plt.ylabel('Elevation (deg)')
    plt.xlabel ('Time (UTC) starting from {}'.format(now_timestamp.to_string()))

    ax2 = ax.twiny()
    ax2.xaxis.set_major_locator(MaxNLocator(24))
    minorLocator = MultipleLocator(0.25)
    ax2.xaxis.set_minor_locator(minorLocator)
    new_ticks = plt.xticks(
            numpy.linspace(0,1,24),
            numpy.round(lst_range[numpy.linspace(1, len(lst_range), num=24, dtype = int)-1], 2),
            rotation = 30,
            fontsize=10)
    plt.yticks(fontsize=10)
    plt.xlabel('Local Sidereal Time (hours)')
    # plt.savefig('elevation_utc_lst.png',dpi=300)
    return fig

# Target information line in table
def table_line(target, comparitor, timestamp, location):

    rise_time = Observatory()._ephem_risetime_(target.body, lst=False)
    set_time = Observatory()._ephem_settime_(target.body, lst=False)
    separation_angle = comparitor.separation(target,
        timestamp=timestamp,
        antenna=location)

    return '{: <16}{: <16}{: <16}{:.2f} deg from {}\n'.format(
                target.name,
                rise_time.datetime().strftime("%H:%M:%S")+'Z',
                set_time.datetime().strftime("%H:%M:%S")+'Z',
                numpy.degrees(separation_angle),
                comparitor.name,
                )

def main(args):
    location = Observatory().location
    creation_time = katpoint.Timestamp()
    ref_antenna = katpoint.Antenna(location)

    if args.view:
        source_elevation(katpoint.Catalogue(file(args.catalogue)), location)
        quit()

    calibrator = lambda catalogue, target, ref_antenna: catalogue.closest_to(target, antenna=ref_antenna)
    sun = katpoint.Target('Sun, special')

    if args.catalogue:
        catalogue = katpoint.Catalogue(file(args.catalogue))
        catalogue.antenna = katpoint.Antenna(location)
        targets = catalogue.filter(['~bpcal', '~gaincal', '~fluxcal', '~polcal'])
    elif args.target:
        args.target = [target.strip() for target in args.target]
        target = ', '.join(map(str, [args.target[0], 'radec target', args.target[1], args.target[2]]))
        targets = [katpoint.Target(target)]
    else:
        raise RuntimeError('No targets provided, exiting')

    # constructing observational catalogue
    observation_catalogue = katpoint.Catalogue()
    observation_catalogue.antenna = ref_antenna

    # output stats
    observation_table = '\nObservation Table for {}Z\n'.format(creation_time)
    # observation_table += 'Target\t\tRise Time\tSet Time\tSeparation Angle [deg]\n'
    observation_table += '{: <16}{: <16}{: <16}{: <16}\n'.format(
            'Target', 'Rise Time', 'Set Time', 'Separation Angle')

    for target in targets:
        observation_catalogue.add(target)
        observation_table += table_line(target, sun, creation_time, ref_antenna)

        # read calibrator catalogues
        for cal_tag in args.calibrators:
            # TODO: add katconf read
            # (katconf.resource_string(opts.configdelayfile).split('\n'))
            cal_catalogue = os.path.join(
                    catalogue_path,
                    'Lband-interferometric-{}-calibrators.csv'.format(cal_tag),
                    )
            calibrators = katpoint.Catalogue(file(cal_catalogue))
            calibrator_, separation_angle =  calibrator(calibrators, target, ref_antenna)
            observation_catalogue.add(calibrator_)
            observation_table += table_line(calibrator_, target, creation_time, ref_antenna)

    # write observation catalogue
    catalogue_header = '# Observation catalogue for proposal ID {}\n'.format(
            args.prop_id)
    catalogue_header += '# PI: {}\n'.format(args.pi)
    catalogue_header += '# Contact details: {}\n'.format(args.contact)

    if args.prop_id is None:
        raise RuntimeError('Proposal ID must be provided when creating catalogue CSV file')
    if args.target is not None:
        cat_name_ = ''.join(args.target[0].split(' '))  # remove spaces from filename
    else:
        cat_name_ = os.path.splitext(os.path.basename(args.catalogue))[0]
    catalogue_fname = '{}_{}.csv'.format(args.prop_id, cat_name_)
    catalogue_fname = os.path.join(args.catalogue_path, catalogue_fname)

    catalogue_data = '\nObservation catalogue for {}Z\n'.format(creation_time)
    catalogue_data += catalogue_header
    observation_catalogue.save(catalogue_fname)
    with open(catalogue_fname, 'r+') as fcat:
        sources = fcat.readlines()
        fcat.seek(0)
        fcat.write(catalogue_header)
        for target in sources:
            catalogue_data += target
            fcat.write(target)
    print catalogue_data

    fig = source_elevation(observation_catalogue, location, report=args.report)
    if args.report:
        report_fname = '{}_{}.pdf'.format(args.prop_id, cat_name_)
        print report_fname
        with PdfPages(report_fname) as pdf:
            plt.text(0.05, 0.97,
                    catalogue_data,
                    transform=fig.transFigure,
                    horizontalalignment='left',
                    verticalalignment='top',
                    size=12)
            plt.text(0.05, 0.27,
                    observation_table,
                    transform=fig.transFigure,
                    horizontalalignment='left',
                    verticalalignment='top',
                    size=12)
            pdf.savefig()
            plt.close()

    else:
        print observation_table
        print('Catalogue will be written to file {}'.format(catalogue_fname))
        plt.show()

if __name__ == '__main__':
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg
    main(cli(sys.argv[0]))


# -fin-
