# MeerKAT calibrator selection tools
#  Returns the closest calibrator(s) for per target

from __future__ import print_function

import argparse
import ephem
import katpoint
import numpy
import os
import sys
import time

from astrokat import Observatory, read_yaml, katpoint_target
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
            help='\
path to calibrator catalogue folder')
    parser.add_argument(
            '--solar-angle',
            type=float,
            default=20.,  # angle in degrees
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
    # All times and timestamps assumed UTC, no special conversion to
    # accommodate SAST allowed to prevent confusion
    creation_date = catalogue.antenna.observer.date
    utc_timestamp = time.mktime(creation_date.datetime().timetuple())
    time_range = utc_timestamp + numpy.arange(0, 24. * 60. * 60., 360.)
    timestamps = [datetime.fromtimestamp(ts) for ts in time_range]

    lst_timestamps = []
    for timestamp in timestamps:
        catalogue.antenna.observer.date = ephem.Date(timestamp)
        lst_time = '{}'.format(catalogue.antenna.observer.sidereal_time())
        lst_time_str = datetime.strptime(lst_time, '%H:%M:%S.%f').strftime('%H:%M')
        lst_timestamps.append(lst_time_str)

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
        # elev = katpoint.rad2deg(target.azel(time_range)[1])
        # elev = numpy.degrees(target.azel(time_range-time.timezone)[1])
        elev = []
        for timestamp in timestamps:
            catalogue.antenna.observer.date = ephem.Date(timestamp)
            target.body.compute(catalogue.antenna.observer)
            elev.append(numpy.degrees(target.body.alt))

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
    ax.set_xlabel('Time (UTC) starting from {}'.format(datetime.fromtimestamp(utc_timestamp)))

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
        datetime,  # ephem.Date object
        target,  # katpoint target
        sep_angle=None,  # degrees
        cal_limit=None,  # degrees
        sol_limit=None,  # degrees
        notes='',
        ):
    """
        Construct a line of target information to display on command line output

        @param datetime: date and time (ephem.Date object) for calculating target information
        @param target: target from katpoint.Catalogue object
        @param sep_angle: [optional] separation angle in degrees as float
        @param cal_limit: [optional] maximum separation angle between target and calibrator
        @param sol_limit: [optional] minimum separation angle between target and Sun
        @param notes: [optional] user provided extra information

        @return: <name> <risetime UTC> <settime UTC> <Separation> <Notes>
    """
    observatory = Observatory(datetime=datetime)
    rise_time = observatory._ephem_risetime_(target.body, lst=False)
    set_time = observatory._ephem_settime_(target.body, lst=False)

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

    table_info = '{: <16}{: <32}{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n'.format(
            target.name,
            ' '.join(target.tags),
            str(target.body._ra),
            str(target.body._dec),
            rise_time.datetime().strftime("%H:%M:%S"),
            set_time.datetime().strftime("%H:%M:%S"),
            sep_note,
            notes,
            )
    return clo_clr + table_info + bcolors.ENDC


# Create observation table
def obs_table(ref_antenna,
              catalogue,
              ref_tgt_list=[],
              solar_sep=90.,
              ):
    """
        Construct a command line table to displaying catalogue target information

        @param ref_antenna: reference location for pointing calculation as katpoint.Antenna object
        @param catalogue: catalogue of targets as katpoint.Catalogue object
        @param ref_tgt_list: [optional] reference targets for calibrator selection
        @param solar_sep: [optional] minimum solar separation angle

        @return: <name> <tag> <risetime UTC> <settime UTC> <Separation> <Notes>
    """
    creation_time = ref_antenna.observer.date
    observation_table = '\nObservation Table for {} (UTC)\n'.format(creation_time)
    observation_table += 'Times listed in UTC for target above the default horizon = 20 degrees\n'
    observation_table += '{: <16}{: <32}{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n'.format(
            'Sources',
            'Class',
            'RA',
            'Decl',
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
    sun.body.compute(ref_antenna.observer)
    katpt_targets = catalogue.filter(target_tags)
    calibrator_tags = ['bpcal', 'fluxcal', 'polcal', 'gaincal']
    katpt_calibrators = catalogue.filter(calibrator_tags)
    for cnt, target in enumerate(katpt_targets):
        note = ''
        if cnt < 1:
            note = 'separation from Sun'
        target.body.compute(ref_antenna.observer)
        separation_angle = ephem.separation(sun.body, target.body)
        observation_table += table_line(
                ref_antenna.observer.date,
                target,
                numpy.degrees(separation_angle),
                sol_limit=solar_sep,
                notes=note,
                )

    current_target = ''
    for calibrator in katpt_calibrators:
        # find closest reference target
        calibrator.body.compute(ref_antenna.observer)
        if len(ref_tgt_list) < 1:
            ref_tgt_list = katpt_targets.targets
        sep_angles = []
        for tgt in ref_tgt_list:
            tgt.body.compute(ref_antenna.observer)
            sep_angles.append(ephem.separation(calibrator.body, tgt.body))
        note = ''
        tgt_idx = numpy.argmin(sep_angles)
        target = ref_tgt_list[tgt_idx]
        separation_angle = numpy.degrees(sep_angles[tgt_idx])
        if current_target != target.name:
            note = 'separation from {}'.format(target.name)
            current_target = target.name
        observation_table += table_line(
                ref_antenna.observer.date,
                calibrator,
                sep_angle=separation_angle,
                cal_limit=15,
                notes=note)

    return observation_table
# --Output observation target stats--


# --write observation catalogue--
# construct supplementary header information
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


# --utility functions to replace katpoint calculations--
# # katpoint.Time object changes the timestamps from UTC by -time.timezone,
# # this has be taken into account, else the date will be 4 hours behind SAST
# timestamp = time.mktime(ref_antenna.observer.date.datetime().timetuple())
# calibrator, separation = catalogue.closest_to(target, timestamp=(timestamp-time.timezone), antenna=ref_antenna)
def _separation_angles(katpt_catalogue, target, observer):
    """
        Utility function to calculate the separation angle between a target
        and all the calibrators in the provided catalgoue

        @param katpt_catalogue: katpoint.Catalogue object
        @param target: ephem.FixedBody object
        @param observer: ephem.Observer object

        @return: List of separation angles in radians
    """
    target.compute(observer)
    separation_angles = []
    for calib in katpt_catalogue:
        calib.body.compute(observer)
        separation_angles.append(ephem.separation(target, calib.body))
    return separation_angles


def _closest_calibrator_(katpt_catalogue, target, observer):
    """
        Utility function to find the closest calibrator to a target

        @param katpt_catalogue: katpoint.Catalogue object
        @param target: ephem.FixedBody object
        @param observer: ephem.Observer object

        @return: katpoint.Target closest calibrator
        @return: separation angle in degrees
    """
    separation_angles = _separation_angles(katpt_catalogue, target, observer)
    closest_idx = numpy.argmin(separation_angles)
    separation = numpy.degrees(separation_angles[closest_idx])
    calibrator = katpt_catalogue.targets[closest_idx]
    return calibrator, separation
# --utility functions to replace katpoint calculations--


# Find closest calibrator to target from catalogue of calibrators
def get_cal(catalogue, katpt_target, ref_antenna):
    """
        Find closest calibrator to target from catalogue of calibrators

        @param catalogue: katpoint.Catalogue object
        @param katpt_target: katpoint.Target object
        @param ref_antenna: katpoint.Antenna object

        @return: katpoint.Target closest calibrator
        @return: separation angle in degrees
    """
    calibrator, separation = _closest_calibrator_(catalogue,
                                                  katpt_target.body,
                                                  ref_antenna.observer)
    return calibrator, separation


# Find calibrator with best coverage (>80%) of target visibility period
# else return 2 calibrators to cover the whole target visibility period
def best_cal_cover(catalogue, katpt_target, ref_antenna):
    """
        Find calibrator with best coverage (>80%) of target visibility period
        else return 2 calibrators to cover the whole target visibility period

        @param catalogue: katpoint.Catalogue object
        @param katpt_target: katpoint.Target object
        @param ref_antenna: katpoint.Antenna object

        @return: katpoint.Target closest calibrator
        @return: separation angle in degrees
        @return: katpoint.Target additional calibrator for LST coverage
        @return: additional separation angle in degrees
    """
    calibrator, separation = _closest_calibrator_(catalogue,
                                                  katpt_target.body,
                                                  ref_antenna.observer)
    pred_calibrator = None
    pred_separation = 180.
    if separation > 20.:  # calibrator rises some time after target
        # add another calibrator preceding the target
        observatory = Observatory(datetime=ref_antenna.observer.date)
        tgt_rise_time = observatory._ephem_risetime_(katpt_target.body, lst=False)
        preceding_cals = []
        for each_cal in catalogue:
            cal_set_time = observatory._ephem_settime_(each_cal.body, lst=False)
            delta_time_to_cal_rise = cal_set_time - tgt_rise_time
            if (delta_time_to_cal_rise) > 0:
                preceding_cals.append([each_cal.name, delta_time_to_cal_rise])
        pred_cal_idx = numpy.array(preceding_cals)[:, 1].astype(float).argmin()
        pred_calibrator = catalogue[preceding_cals[pred_cal_idx][0]]
        pred_separation = ephem.separation(katpt_target.body, pred_calibrator.body)
        pred_separation = numpy.degrees(pred_separation)
    return calibrator, separation, pred_calibrator, pred_separation


def add_target(target, catalogue, tag=''):
    """
        Add target to catalogue

        @param target: katpoint.Target object
        @param catalogue: katpoint.Catalogue object
        @param tag: target tag as string

        @return: katpoint.Catalogue
    """
    if catalogue.__contains__(target.name):
        if tag not in catalogue[target.name].tags:
            catalogue[target.name].tags.append(tag)
    else:
        catalogue.add(target, tags=tag)
    return catalogue


def main(args):
    observatory = Observatory()
    location = observatory.location
    node_config_available = observatory.node_config_available
    creation_time = args.datetime
    ref_antenna = katpoint.Antenna(location)
    ref_antenna.observer.date = ephem.Date(creation_time)

    caltag_dict = {
            'bp': 'bandpass',
            'delay': 'delay',
            'flux': 'flux',
            'gain': 'gain',
            'pol': 'polarisation'
            }

    # TODO: think about moving this to a separate script
    if args.view:
        # check if view file in CSV or YAML
        data_dict = read_yaml(args.view)
        if isinstance(data_dict, dict):
            catalogue = katpoint.Catalogue()
            catalogue.antenna = ref_antenna
            for observation_cycle in data_dict['observation_loop']:
                for target_item in observation_cycle['target_list']:
                    name, target = katpoint_target(target_item)
                    catalogue.add(katpoint.Target(target))
        else:  # assume CSV
            # output observation stats for catalogue
            catalogue = katpoint.Catalogue(file(args.view))
        obs_summary = obs_table(
                                ref_antenna,
                                catalogue=catalogue,
                                solar_sep=args.solar_angle,
                                )
        print(obs_summary)
        if not(args.text_only or text_only):
            source_elevation(
                    catalogue,
                    ref_antenna)
            plt.show()
        quit()

    if args.cat_path and os.path.isdir(args.cat_path):
        catalogue_path = args.cat_path
        config_file_available = True
    else:
        catalogue_path = 'katconfig/user/catalogues'
        config_file_available = False

    # before doing anything, verify that calibrator catalogues can be accessed
    if not os.path.isdir(catalogue_path) and not node_config_available:
        msg = 'Could not access calibrator catalogue default location\n'
        msg += 'add explicit location of catalogue folder using --cat-path <dirname>'
        raise RuntimeError(msg)

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
                if len(line) < 1:  # ignore empty lines
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
            try:
                if config_file_available:
                    # assert os.path.isfile(cal_catalogue), 'Catalogue file does not exist'
                    calibrators = katpoint.Catalogue(file(cal_catalogue))
                elif node_config_available:
                    calibrators = katpoint.Catalogue(
                        observatory.read_file_from_node_config(cal_catalogue))
                else:  # user specified calibrator file
                    calibrators = katpoint.Catalogue(file(cal_catalogue))
            except (AssertionError, IOError):
                msg = bcolors.WARNING
                msg += 'Unable to open {}\n'.format(cal_catalogue)
                msg += 'Observation file will still be created, please add calibrator manually\n'
                msg += bcolors.ENDC
                print(msg)
                continue
            if 'gain' in cal_tag or 'delay' in cal_tag:
                # for secondary calibrators such as gain, find the closest calibrator
                calibrator, separation_angle = get_cal(calibrators,
                                                       target,
                                                       ref_antenna)
            else:
                # for primary calibrators, find the best coverage over the target
                # visibility period
                calibrator, \
                    separation_angle, \
                    preceding_calibrator, \
                    preceding_calibrator_separation_angle = best_cal_cover(calibrators,
                                                                           target,
                                                                           ref_antenna)
                if preceding_calibrator is not None \
                        and preceding_calibrator_separation_angle < 90.:
                    observation_catalogue = add_target(preceding_calibrator, observation_catalogue, tag=cal_tag+'cal')
            observation_catalogue = add_target(calibrator, observation_catalogue, tag=cal_tag+'cal')
        observation_catalogue = add_target(target, observation_catalogue)

    # write observation catalogue
    catalogue_header = write_header(args, userheader=header)
    catalogue_data = observation_catalogue.sort()
    if args.outfile is not None:
        filename = os.path.splitext(os.path.basename(args.outfile))[0]+'.csv'
        args.outfile = os.path.join(os.path.dirname(args.outfile), filename)
        write_catalogue(
                args.outfile,
                catalogue_header,
                catalogue_data,
                )
        print('Observation catalogue {}'.format(args.outfile))

    # output observation stats for catalogue
    obs_summary = obs_table(
            ref_antenna,
            catalogue=catalogue_data,
            ref_tgt_list=cal_targets,
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
