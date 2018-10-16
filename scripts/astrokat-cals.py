# MeerKAT calibrator selection tools
#  Returns the closest calibrator(s) for per target

from __future__ import print_function

import argparse
import katpoint
import numpy
import os
import json
import sys

from astrokat import Observatory
from datetime import datetime

# check if system can create images and pdf report
# TODO: replace this global flag with a better test
text_only = False
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import MaxNLocator, MultipleLocator
    from matplotlib.font_manager import FontProperties
    from matplotlib.backends.backend_pdf import PdfPages
except ImportError:  # not a processing node
    text_only = True


def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options]".format(prog)
    description = 'Calibrator selection for MeerKAT telescope'

    parser = argparse.ArgumentParser(
            usage=usage,
            description=description,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
            '--cal-tags',
            type=str,
            nargs='+',
            metavar='<tag>',
            help='\
List of tags for types of calibrators to provide per target: \
gain, bandpass, flux, polarisation.')
    parser.add_argument(
            '--target',
            nargs=3,
            type=str,
            metavar=('Name', 'RA', 'Decl'),
            help='\
Returns MeerKAT LST range for a celestial target with coordinates \
HH:MM:SS DD:MM:SS')
    parser.add_argument(
            '--cat-path',
            type=str,
            help='\
Path to calibrator catalogue folder')

    group = parser.add_argument_group(
            title="Catalogue output options",
            description="Options to view constructed observation catalogue")
    group.add_argument(
            '--output-path',
            type=str,
            default='.',  # working dir
            help='\
Path to write observation catalogue CSV file and report if requested')
    group.add_argument(
            '--view',
            type=str,
            metavar='CATALOGUE',
            help='\
Display catalogue sources elevation over time')
    group.add_argument(
            '--report',
            action='store_true',
            help='\
Display catalogue source elevation over time')
    group.add_argument(
            '--text-only',
            action='store_true',
            help='\
Output observation target information text only')

    return parser.parse_args()


# Generates a plot of elevation over time for all sources in catalogue
def source_elevation(catalogue, location, report=False):
    catalogue.antenna = katpoint.Antenna(location)
    target = catalogue.targets[0]
    now_timestamp = katpoint.Timestamp()
    time_range = now_timestamp.secs + numpy.arange(0, 24. * 60. * 60., 360.)
    timestamps = [datetime.utcfromtimestamp(ts) for ts in time_range]

    if report:
        fig = plt.figure(figsize=(11, 8), facecolor='white')
        ax = plt.subplot(212)
    else:
        fig = plt.figure(figsize=(15, 7), facecolor='white')
        ax = plt.subplot(111)
    plt.subplots_adjust(right=0.8)
    lines = list()
    labels = list()
    fontP = FontProperties()
    fontP.set_size('small')

    for cnt, target in enumerate(catalogue.targets):
        elev = katpoint.rad2deg(target.azel(time_range)[1])
        myplot, = plt.plot_date(
               timestamps,
               elev,
               fmt='.',
               linewidth=0,
               label=target.name)
        lines.append(myplot)
        labels.append(target.name)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(24), interval=1))
    labels = ax.get_xticklabels()
    plt.setp(labels, rotation=30, fontsize=10)
    plt.ylim(20, 90)
    plt.grid()
    plt.legend()
    plt.ylabel('Elevation (deg)')
    plt.xlabel('Time (UTC) starting from {}'.format(now_timestamp.to_string()))

    ax2 = ax.twiny()
    ax2.xaxis.set_major_locator(MaxNLocator(24))
    minorLocator = MultipleLocator(0.25)
    ax2.xaxis.set_minor_locator(minorLocator)
    plt.yticks(fontsize=10)
    plt.xlabel('Local Sidereal Time (hours)')
    plt.savefig('elevation_utc_lst.png', dpi=300)
    return fig


# --Output observation target stats--
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


# Create observation table
def obs_table(timestamp,  # time of calculation
              ref_antenna,  # reference location for pointing calculation
              catalogue=None,
              ):
    observation_table = '\nObservation Table for {}Z\n'.format(timestamp)
    observation_table += '{: <16}{: <16}{: <16}{: <16}\n'.format(
            'Sources', 'Rise Time', 'Set Time', 'Separation Angle')

    sun = katpoint.Target('Sun, special')
    if catalogue is not None:
        catalogue = katpoint.Catalogue(file(catalogue))
        # targets are not calibrators
        target_tags = ['~bpcal', '~gaincal', '~fluxcal', '~polcal', '~phasecal']
        for target in catalogue.filter(target_tags):
            observation_table += 'Target\n'
            observation_table += table_line(target, sun, timestamp, ref_antenna)
            observation_table += 'Primary calibrators\n'
            for calibrator in catalogue.filter(['bpcal', 'fluxcal', 'polcal']):
                observation_table += table_line(calibrator, target, timestamp, ref_antenna)
            observation_table += 'Secondary calibrators\n'
            for calibrator in catalogue.filter(['gaincal', 'phasecal']):
                observation_table += table_line(calibrator, target, timestamp, ref_antenna)

    return observation_table
# --Output observation target stats--


# --write observation catalogue--
def write_header(args):
    catalogue_header = '# Observation catalogue for proposal ID {}\n'.format(
            args.prop_id)
    catalogue_header += '# PI: {}\n'.format(args.pi)
    catalogue_header += '# Contact details: {}\n'.format(args.contact)
    return catalogue_header


def write_catalogue(filename, catalogue_header, katpoint_catalogue):
    katpoint_catalogue.save(filename)
    with open(filename, 'r+') as fcat:
        sources = fcat.readlines()
        fcat.seek(0)
        fcat.write(catalogue_header)
        for target in sources:
            fcat.write(target)
# --write observation catalogue--


def get_cal(catalogue, target, ref_antenna):
    return catalogue.closest_to(target, antenna=ref_antenna)


def main(args):

    cam_config_path = '/var/kat/config'
    node_file = '/var/kat/node.conf'
    settings = {}

    try:
        import katconf
        # Set up configuration source
        if os.path.isdir(cam_config_path):
            katconf.set_config(katconf.environ(override=cam_config_path))
        elif os.path.isfile(node_file):
            with open(node_file, 'r') as fh:
                node_conf = json.loads(fh.read())
            for key, val in node_conf.items():
                # Remove comments at the end of the line
                val = val.split("#", 1)[0]
                settings[key] = val.strip()
                if node_conf.get("configuri", False):
                    katconf.set_config(katconf.environ(node_conf["configuri"]))
                else:
                    print('katconf config not set')
        else:
            raise ValueError("Could not open node config file")
        node_config_available = True
    except ImportError:
        node_config_available = False


    location = Observatory().location
    creation_time = katpoint.Timestamp()
    ref_antenna = katpoint.Antenna(location)

    # TODO: think about moving this to a separate script
    if args.view:
        # output observation stats for catalogue
        obs_summary = obs_table(creation_time,
                                ref_antenna,
                                catalogue=args.view,
                                )
        if args.text_only or text_only:
            print(obs_summary)
        else:
            source_elevation(katpoint.Catalogue(file(args.view)), location)
            plt.show()
        quit()

    if not args.target:
        raise RuntimeError('No targets provided, exiting')

    if args.cat_path and os.path.isdir(args.cat_path):
        catalogue_path = args.cat_path
        config_file_available = True
    else:
        catalogue_path = 'katconfig/user/catalogues'
        config_file_available = False

    # input target from command line
    args.target = [target.strip() for target in args.target]
    target = ', '.join(map(str, [args.target[0], 'radec target', args.target[1], args.target[2]]))
    targets = [katpoint.Target(target)]

    # constructing observational catalogue
    observation_catalogue = katpoint.Catalogue()
    observation_catalogue.antenna = ref_antenna

    for target in targets:
        observation_catalogue.add(target)
        # read calibrator catalogues and calibrators to catalogue
        for cal_tag in args.cal_tags:
            cal_catalogue = os.path.join(
                    catalogue_path,
                    'Lband-{}-calibrators.csv'.format(cal_tag),
                    )
           
            if config_file_available:
                assert os.path.isfile(cal_catalogue), 'Catalogue file does not exist'
                calibrators = katpoint.Catalogue(file(cal_catalogue))
            elif node_config_available:
                assert katconf.resource_exists(cal_catalogue), 'Catalogue file does not exist'
                calibrators = katpoint.Catalogue(
                    katconf.resource_template(cal_catalogue))
            else:
                raise RuntimeError('Loading calibrator catalogue {} failed!'.format(cal_catalogue))

            calibrator, separation_angle =  get_cal(calibrators, target, ref_antenna)
            observation_catalogue.add(calibrator)

    # write observation catalogue
    fname = ''.join(args.target[0].split(' '))  # remove spaces from filename
    fname = '{}_{}'.format(args.prop_id, fname)
    fname = os.path.join(args.output_path, fname)
    catalogue_fname = '{}.csv'.format(fname)
    write_catalogue(
            catalogue_fname,
            write_header(args),
            observation_catalogue)
    print('Observation catalogue {}'.format(catalogue_fname))

    # output observation stats for catalogue
    obs_summary = obs_table(creation_time,
                            ref_antenna,
                            catalogue=catalogue_fname,
                            )
    print(obs_summary)

    if text_only and not args.text_only:
        msg = 'Required matplotlib functionalities not available\n'
        msg += 'Cannot create elevation plot or generate report\n'
        msg += 'Only producing catalogue file and output to screen'
        print(msg)
    if not (text_only or args.text_only):
        # create elevation plot for sources
        fig = source_elevation(observation_catalogue, location, report=args.report)
        # PDF report for printing
        if args.report:
            report_fname = '{}.pdf'.format(fname)
            with PdfPages(report_fname) as pdf:
                plt.text(0.05, 0.97,
                         obs_summary,
                         transform=fig.transFigure,
                         horizontalalignment='left',
                         verticalalignment='top',
                         size=12)
                pdf.savefig()
                plt.close()
            print('Observation catalogue report {}'.format(report_fname))
        plt.show()


if __name__ == '__main__':
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg
    main(cli(sys.argv[0]))

# -fin-
