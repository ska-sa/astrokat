# MeerKAT calibrator selection tools
#  Returns the closest calibrator(s) for per target

from __future__ import print_function

import argparse
import ephem
import katpoint
import numpy
import os
import json
import sys

from astrokat import Observatory
from datetime import datetime

text_only = False
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.font_manager import FontProperties
    from matplotlib.backends.backend_pdf import PdfPages
except ImportError:  # not a processing node
    text_only = True


# define command line input arguments
def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options]".format(prog)
    description = 'calibrator selection for MeerKAT telescope'

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
name of principle investigator or designated project leader")
    parser.add_argument(
            '--contact',
            type=str,
            help="\
PI contact details, such as email address or phone number")
    parser.add_argument(
            '--prop-id',
            type=str,
            help="\
proposal ID")
    cal_tags = ['gain', 'bp', 'flux', 'pol', 'delay']
    parser.add_argument(
            '--cal-tags',
            type=str,
            nargs='+',
            metavar='<tag>',
            choices=cal_tags,
            help='\
list of tags for types of calibrators to provide per target: \
gain, bp, flux, pol.')
    parser.add_argument(
            '--cat-path',
            type=str,
            default='katconfig/user/catalogues',
            help='\
path to calibrator catalogue folder')
    parser.add_argument(
            '--solar-angle',
            type=float,
            default=20,  # angle in degrees
            help='\
solar separation angle from target observation region')
    parser.add_argument(
            '--datetime',
            default=datetime.utcnow(),
            help="\
catalogue creation or viewing date and time with \
string format 'YYYY-MM-DD HH:MM'")

    group = parser.add_argument_group(
                                      title="\
observation target specification (*required*)",
                                      description="\
multiple targets are added using an input file, \
while for a single target a quick command line option is also available \
 -- simultaneous use of a catalogue and input target is not allowed.")
    ex_group = group.add_mutually_exclusive_group(required=True)
    ex_group.add_argument(
            '--infile',
            type=str,
            help='\
observation targets as CSV input file')
    ex_group.add_argument(
            '--target',
            nargs=3,
            type=str,
            metavar=('Name', 'RA', 'Decl'),
            help='\
returns MeerKAT LST range for a celestial target with coordinates \
HH:MM:SS DD:MM:SS')
    ex_group.add_argument(
            '--view',
            type=str,
            metavar='CATALOGUE',
            help='\
display catalogue sources elevation over time')

    group = parser.add_argument_group(
            title="catalogue output options",
            description="options to view constructed observation catalogue")
    group.add_argument(
            '--outfile',
            type=str,
            help='\
path and name for observation catalogue CSV file')
    group.add_argument(
            '--report',
            action='store_true',
            help='\
display catalogue source elevation over time')
    group.add_argument(
            '--text-only',
            action='store_true',
            help='\
output observation target information text only')

    return parser.parse_args()


def source_elevation(catalogue, ref_antenna, report=False):
    """
        Generates a plot of elevation over time for 24 hour period
        for all sources in provided catalogue at a specific location

        @param catalogue: katpoint.Catalogue object
        @param ref_antenna: katpoint.Antenna object
        @param report: [optional] matplotlib figure suitable for PDF report

        @return: matplotlib figure handle
    """
    catalogue.antenna = ref_antenna
    creation_date = catalogue.antenna.observer.date
    now_timestamp = katpoint.Timestamp(creation_date)
    time_range = now_timestamp.secs + numpy.arange(0, 24. * 60. * 60., 360.)
    timestamps = [datetime.utcfromtimestamp(ts) for ts in time_range]

    lst_timestamps = []
    for timestamp in timestamps:
        catalogue.antenna.observer.date = ephem.Date(timestamp)
        lst_time = '{}'.format(catalogue.antenna.observer.sidereal_time())
        lst_timestamps.append(datetime.strptime(lst_time, '%H:%M:%S.%f').strftime('%H:%M'))

    if report:
        fig = plt.figure(figsize=(11, 8), facecolor='white')
        ax = plt.subplot(211)
    else:
        fig = plt.figure(figsize=(15, 7), facecolor='white')
        ax = plt.subplot(111)
    plt.subplots_adjust(right=0.8)
    fontP = FontProperties()
    fontP.set_size('small')

    for cnt, target in enumerate(catalogue.targets):
        elev = katpoint.rad2deg(target.azel(time_range)[1])

        label = '{} '.format(target.name)
        target.tags.remove('radec')
        target.tags.remove('target') if 'target' in target.tags else None
        label += ', '.join(target.tags)

        myplot, = plt.plot_date(
               timestamps,
               elev,
               fmt='.',
               linewidth=0,
               label=label)
    ax.axhspan(15, 20, facecolor='k', alpha=0.3)
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    plt.grid()
    plt.legend(
            loc='center left',
            bbox_to_anchor=(1, 0.5),
            prop={'size': 10},
            numpoints=1)
    plt.ylabel('Elevation (deg)')
    plt.ylim(15, 90)
    plt.yticks(fontsize=10)
    ax.set_xticklabels(timestamps[0::10], rotation=30, fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(24), interval=1))
    ax.set_xlabel('Time (UTC) starting from {}'.format(now_timestamp.to_string()))

    ax2 = ax.twiny()
    box = ax2.get_position()
    ax2.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(ax.get_xticks())
    ax2.set_xticklabels(lst_timestamps[0::10], rotation=30, fontsize=10)
    ax2.set_xlabel('Local Sidereal Time')
    plt.savefig('elevation_utc_lst.png', dpi=300)
    return fig


# --Output observation target stats--
class bcolors:
    """
        Helper class for command line color output
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def table_line(
        target,  # katpoint target
        sep_angle=None,  # degrees
        cal_limit=None,  # degrees
        sol_limit=None,  # degrees
        notes='',
        ):
    """
        Construct a line of target information to display on command line output

        @param target: target from katpoint.Catalogue object
        @param sep_angle: [optional] separation angle in degrees as float
        @param cal_limit: [optional] maximum separation angle between target and calibrator
        @param sol_limit: [optional] minimum separation angle between target and Sun
        @param notes: [optional] user provided extra information

        @return: <name> <risetime UTC> <settime UTC> <Separation> <Notes>
    """
    rise_time = Observatory()._ephem_risetime_(target.body, lst=False)
    set_time = Observatory()._ephem_settime_(target.body, lst=False)

    clo_clr = bcolors.ENDC
    sep_note = ''
    if sep_angle is not None:
        sep_note = '%.2f' % sep_angle
    if cal_limit is not None:
        if sep_angle > cal_limit:
            clo_clr = bcolors.WARNING
            sep_note += ' ***'
    if sol_limit is not None:
        if sep_angle < sol_limit:
            clo_clr = bcolors.FAIL
            sep_note += ' ***'

    table_info = '{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n'.format(
            target.name,
            ','.join(target.tags[1:]),
            rise_time.datetime().strftime("%H:%M:%S"),
            set_time.datetime().strftime("%H:%M:%S"),
            sep_note,
            notes,
            )
    return clo_clr + table_info + bcolors.ENDC


# Create observation table
def obs_table(timestamp,
              ref_antenna,
              catalogue,
              cal_ref_list=[],
              solar_sep=90,
              ):
    """
        Construct a command line table to displaying catalogue target information

        @param timestamp: time of calculation as katpoint.Timestamp object
        @param ref_antenna: reference location for pointing calculation as katpoint.Antenna object
        @param catalogue: catalogue of targets as katpoint.Catalogue object
        @param cal_ref_list: [optional] reference targets for calibrator selection
        @param solar_sep: [optional] minimum solar separation angle

        @return: <name> <tag> <risetime UTC> <settime UTC> <Separation> <Notes>
    """
    observation_table = '\nObservation Table for {}\n'.format(timestamp)
    observation_table += '{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n'.format(
            'Sources',
            'Class',
            'Rise Time',
            'Set Time',
            'Separation',
            'Notes',
            )

    # targets are not calibrators
    target_tags = [
            '~bpcal',
            '~gaincal',
            '~fluxcal',
            '~polcal',
            '~delaycal',
            ]
    sun = katpoint.Target('Sun, special')
    for cnt, target in enumerate(catalogue.filter(target_tags)):
        note = ''
        if cnt < 1:
            note = 'separation from Sun'
        separation_angle = sun.separation(target,
                                          timestamp=timestamp,
                                          antenna=ref_antenna)
        observation_table += table_line(
                target,
                numpy.degrees(separation_angle),
                sol_limit=solar_sep,
                notes=note,
                )

    for calibrator in catalogue.filter(['bpcal', 'fluxcal', 'polcal', 'gaincal']):
        # find closest reference target
        sep_angles = [calibrator.separation(tgt, timestamp, ref_antenna)
                      for tgt in cal_ref_list]
        note = ''
        separation_angle = None
        if len(sep_angles) > 0:
            target = cal_ref_list[numpy.argmin(numpy.degrees(sep_angles))]
            separation_angle = numpy.degrees(calibrator.separation(target, timestamp, ref_antenna))
            note = 'separation from {}'.format(target.name)
        observation_table += table_line(
                calibrator,
                sep_angle=separation_angle,
                cal_limit=15,
                notes=note)

    return observation_table
# --Output observation target stats--


# --write observation catalogue--
# construct suplementary header information
def write_header(args, userheader=''):
    """
        Creates fancy header to add at the top of the calibrator catalgoue
        Adding information such as proposal ID, PI, contact details
    """
    catalogue_header = userheader
    catalogue_header += '# Observation catalogue for proposal ID {}\n'.format(
            args.prop_id)
    catalogue_header += '# PI: {}\n'.format(args.pi)
    catalogue_header += '# Contact details: {}\n'.format(args.contact)
    return catalogue_header


# write observation catalogue using katpoint functionality
def write_catalogue(filename, catalogue_header, katpoint_catalogue):
    """
        Add all katpoint.Catalogue object targets to CVS file
    """
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
    observatory = Observatory()
    location = observatory.location
    node_config_available = observatory.node_config_available
    creation_time = katpoint.Timestamp(ephem.Date(args.datetime))
    ref_antenna = katpoint.Antenna(location)
    ref_antenna.observer.date = creation_time

    caltag_dict = {
            'bp': 'bandpass',
            'delay': 'delay',
            'flux': 'flux',
            'gain': 'gain',
            'pol': 'polarisation'
            }

    # TODO: think about moving this to a separate script
    if args.view:
        # output observation stats for catalogue
        catalogue = katpoint.Catalogue(file(args.view))
        obs_summary = obs_table(creation_time,
                                ref_antenna,
                                catalogue=catalogue,
                                solar_sep=args.solar_angle,
                                )
        if args.text_only or text_only:
            print(obs_summary)
        else:
            source_elevation(
                    katpoint.Catalogue(file(args.view)),
                    ref_antenna)
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

    # constructing observational catalogue
    observation_catalogue = katpoint.Catalogue()
    observation_catalogue.antenna = ref_antenna

    # targets to obtain calibrators for
    header = ''
    cal_targets = []
    if args.target is not None:
        # input target from command line
        args.target = [target.strip() for target in args.target]
        target = ', '.join(map(str, [args.target[0], 'radec target', args.target[1], args.target[2]]))
        cal_targets = [katpoint.Target(target)]
    else:  # assume the targets are in a file
        with open(args.infile, 'r') as fin:
            # extract targets tagged to be used for calibrator selection
            for line in fin.readlines():
                if line[0] == '#':  # catch and keep header lines
                    header += line
                    continue
                if 'calref' in line:
                    target = line.strip().replace('calref', 'target')
                    cal_targets.append(katpoint.Target(target))
                else:  # add target to catalogue
                    target = line.strip().replace('radec', 'radec target')
                    observation_catalogue.add(katpoint.Target(target))
        # if not reference target for calibrator selection is specified,
        # simply select the first target listed in the catalogue
        if len(cal_targets) < 1:
            cal_targets = [observation_catalogue.targets[0]]

    for target in cal_targets:
        # read calibrator catalogues and calibrators to catalogue
        for cal_tag in args.cal_tags:
            cal_catalogue = os.path.join(
                    catalogue_path,
                    'Lband-{}-calibrators.csv'.format(caltag_dict[cal_tag]),
                    )
            if config_file_available:
                assert os.path.isfile(cal_catalogue), 'Catalogue file does not exist'
                calibrators = katpoint.Catalogue(file(cal_catalogue))
            elif node_config_available:
                calibrators = katpoint.Catalogue(
                    observatory.read_file_from_node_config(cal_catalogue))
            else:
                msg = 'Loading calibrator catalogue {} failed!\n'.format(cal_catalogue)
                msg += 'Add explicit location of catalogue folder using --cat-path <dirname>'
                raise RuntimeError(msg)

            try:
                calibrators = katpoint.Catalogue(file(cal_catalogue))
            except IOError:
                msg = bcolors.WARNING
                msg += 'Unable to open {}\n'.format(cal_catalogue)
                msg += 'Observation file will still be created, please add calibrator manually\n'
                msg += bcolors.ENDC
                print(msg)
                continue

            calibrator, separation_angle = get_cal(calibrators, target, ref_antenna)
            if observation_catalogue.__contains__(calibrator):
                observation_catalogue[calibrator.name].tags.append(cal_tag+'cal')
            observation_catalogue.add(calibrator, tags=cal_tag+'cal')
        observation_catalogue.add(target)

    # write observation catalogue
    catalogue_header = write_header(args, userheader=header)
    catalogue_data = observation_catalogue.sort()
    if args.outfile is not None:
        write_catalogue(
                args.outfile,
                catalogue_header,
                catalogue_data,
                )
        print('Observation catalogue {}'.format(args.outfile))

    # output observation stats for catalogue
    obs_summary = obs_table(
            creation_time,
            ref_antenna,
            catalogue=catalogue_data,
            cal_ref_list=cal_targets,
            solar_sep=args.solar_angle,
            )
    print(obs_summary)

    if text_only and not args.text_only:
        msg = 'Required matplotlib functionalities not available\n'
        msg += 'Cannot create elevation plot or generate report\n'
        msg += 'Only producing catalogue file and output to screen'
        print(msg)
    if not (text_only or args.text_only):
        # create elevation plot for sources
        obs_catalogue = catalogue_header
        for target in catalogue_data:
            obs_catalogue += '{}\n'.format(target)
        fig = source_elevation(observation_catalogue, ref_antenna, report=args.report)
        # PDF report for printing
        if args.report:
            if args.outfile is None:
                raise RuntimeError('Cannot generate PDF report, please specify and output filename')
            fname = os.path.splitext(args.outfile)[0]
            report_fname = '{}.pdf'.format(fname)
            with PdfPages(report_fname) as pdf:
                plt.text(0.05, 0.43,
                         obs_catalogue,
                         transform=fig.transFigure,
                         horizontalalignment='left',
                         verticalalignment='top',
                         size=12)
                pdf.savefig()
            print('Observation catalogue report {}'.format(report_fname))
        plt.show()
        plt.close()


if __name__ == '__main__':
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if (arg[0] == '-') and arg[1].isdigit():
            sys.argv[i] = ' ' + arg
    main(cli(sys.argv[0]))

# -fin-
