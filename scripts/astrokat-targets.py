#!/usr/bin/env python
"""MeerKAT calibrator selection tools.

Returns the closest calibrator(s) per target

"""

from __future__ import print_function

import argparse
import ephem
import katpoint
import numpy
import os
import sys

from astrokat import Observatory, read_yaml, katpoint_target_string, __version__
from astrokat.utility import datetime2timestamp, timestamp2datetime
from copy import deepcopy
from datetime import datetime, timedelta

global_text_only = False
try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.font_manager import FontProperties
except ImportError:  # not a processing node
    global_text_only = True

# hard coded globals
caltag_dict = {
    "bp": "bandpass",
    "delay": "delay",
    "flux": "flux",
    "gain": "gain",
    "pol": "polarisation",
}
cal_tags = caltag_dict.keys()


def cli(prog):
    """Define command line input arguments."""
    usage = "{} [options]".format(prog)
    description = 'calibrator selection for MeerKAT telescope'

    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=__version__)
    parser.add_argument(
        "--pi",
        type=str,
        help="name of principal investigator or designated project leader",
    )
    parser.add_argument(
        "--contact",
        type=str,
        help="PI contact details, such as email address or phone number",
    )
    parser.add_argument(
        "--prop-id",
        type=str,
        help="proposal ID")
    parser.add_argument(
        "--cal-tags",
        type=str,
        nargs="+",
        metavar="<tag>",
        choices=cal_tags,
        help="list of tags specifying types of calibrators to provide: "
             "{}".format(' '.join(sorted(cal_tags))),
    )
    parser.add_argument(
        "--cat-path",
        type=str,
        help="path to calibrator catalogue folder"
    )
    parser.add_argument(
        "--solar-angle",
        type=float,
        default=20.0,  # angle in degrees
        help="solar separation angle (in degrees) from target observation region",
    )
    parser.add_argument(
        "--datetime",
        default=datetime.utcnow(),
        help="catalogue creation or viewing date and time with string "
             "format 'YYYY-MM-DD HH:MM'",
    )
    parser.add_argument(
        "--horizon",
        type=float,
        default=20.0,  # angle in degrees
        help="minimum pointing angle (in degrees) of MeerKAT dish",
    )
    parser.add_argument(
        "--lst",
        action="store_true",
        help="display rise and set times in LST (default UTC)",
    )

    group = parser.add_argument_group(
        title="observation target specification (*required*) ",
        description="multiple targets are added using an input file, "
                    "while for a single target a quick command line "
                    "option is also available -- simultaneous use of "
                    "a catalogue and input target is not allowed.",
    )
    ex_group = group.add_mutually_exclusive_group(required=True)
    ex_group.add_argument(
        "--infile",
        type=str,
        help="observation targets listed in CSV file"
    )
    ex_group.add_argument(
        "--target",
        nargs=3,
        type=str,
        metavar=("Name", "RA", "Decl"),
        help="returns MeerKAT LST range for a celestial target "
             "with coordinates 'HH:MM:SS DD:MM:SS'",
    )
    ex_group.add_argument(
        "--body",
        type=str,
        metavar=("Name"),
        help="returns MeerKAT LST range for a solar body, "
             "assumed to be an Ephem special target",
    )
    ex_group.add_argument(
        "--xephem",
        nargs=2,
        type=str,
        metavar=("Name", "Ephemeris"),
        help="returns MeerKAT LST range for a heliocentric elliptical orbit "
             "using string in XEphem EDB database format to predict orbital position",
    )
    ex_group.add_argument(
        "--view",
        type=str,
        metavar="CATALOGUE",
        help="display catalogue sources elevation over time",
    )

    group = parser.add_argument_group(
        title="catalogue output options",
        description="options to view constructed observation catalogue",
    )
    group.add_argument(
        "--outfile",
        type=str,
        help="path and name for observation catalogue CSV file "
             "(if not provided, only target listing will be displayed)",
    )
    group.add_argument(
        "--text-only",
        action="store_true",
        help="output observation target information text only",
    )
    group.add_argument(
        "--save-fig",
        action="store_true",
        help="save elevation output fig",
    )
    group.add_argument(
        "--all-cals",
        action="store_true",
        help="show all primary calibrators in catalogue",
    )
    view_tags = ["elevation", "solarangle", "riseset"]
    group.add_argument(
        "--view-tags",
        type=str,
        nargs="+",
        metavar="<tag>",
        choices=view_tags,
        default=["elevation"],
        help="list of plot options for target visualization: "
             "elevation solarangle riseset",
    )

    return parser.parse_args()


def get_filter_tags(catalogue, targets=False, calibrators=False):
    observation_tags = []
    for cat_tgt in catalogue:
        observation_tags.extend(cat_tgt.tags)
    observation_tags = list(set(observation_tags))

    # only create filter list for calibrators
    if targets:
        return ['~' + tag for tag in observation_tags if tag[-3:] == "cal"]
    # only create filter list for targets
    if calibrators:
        return [tag for tag in observation_tags if tag[-3:] == "cal"]

    # create filter lists for targets and calibrators
    calibrator_tags = []
    for tag in observation_tags:
        if tag[-3:] == "cal":
            calibrator_tags.append(tag)
    # targets are not calibrators
    if not calibrator_tags:
        calibrator_tags = cal_tags  # all targets set default
    target_tags = ['~' + tag for tag in calibrator_tags]

    return calibrator_tags, target_tags


def source_solar_angle(catalogue, ref_antenna):
    """Source solar angle.

    The solar separation angle (in degrees) from the target observation region
    as seen by the ref_ant

    Parameters
    ----------
    catalogue: list or file
        Data on the target objects to be observed
    ref_antenna: katpoint.Antenna
        A MeerKAT reference antenna

    Returns
    --------
        solar separation angle for a target wrst ref_ant at a given time

    """
    date = ref_antenna.observer.date
    horizon = numpy.degrees(ref_antenna.observer.horizon)
    date = date.datetime().replace(hour=0, minute=0, second=0, microsecond=0)
    numdays = 365
    date_list = [date - timedelta(days=x) for x in range(0, numdays)]

    sun = katpoint.Target("Sun, special")
    target_tags = get_filter_tags(catalogue, targets=True)
    katpt_targets = catalogue.filter(target_tags)

    for cnt, katpt_target in enumerate(katpt_targets):
        plt.figure(figsize=(17, 7), facecolor="white")
        ax = plt.subplot(111)
        plt.subplots_adjust(right=0.8)
        fontP = FontProperties()
        fontP.set_size("small")

        solar_angle = []
        for the_date in date_list:
            ref_antenna.observer.date = the_date
            sun.body.compute(ref_antenna.observer)
            katpt_target.body.compute(ref_antenna.observer)
            solar_angle.append(
                numpy.degrees(ephem.separation(sun.body,
                                               katpt_target.body)))

        myplot, = plt.plot_date(date_list,
                                solar_angle,
                                fmt=".",
                                linewidth=0,
                                label="{}".format(katpt_target.name))
        ax.axhspan(0.0, horizon, facecolor="k", alpha=0.2)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])
        plt.grid()
        plt.legend(loc="center left",
                   bbox_to_anchor=(1, 0.5),
                   prop={"size": 10},
                   numpoints=1)
        plt.ylabel("Solar Separation Angle (degrees)")
        ax.set_xticklabels(date_list[0::20], rotation=30, fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(
                                   bymonthday=range(30),
                                   interval=10))
        ax.set_xlabel("Date")


def source_rise_set(catalogue, ref_antenna):
    """Set source rise time.

    display rise and set times in LST (default UTC)

    Parameters
    ----------
    catalogue: list or file
        Data on the target objects to be observed
    ref_antenna: katpoint.Antenna objec
        A MeerKAT reference antenna

    Returns
    -------
        The UTC time on the day when the source will be above the prescribed horizon

    """
    date = ref_antenna.observer.date
    date = date.datetime().replace(hour=0, minute=0, second=0, microsecond=0)
    numdays = 365
    date_list = [date - timedelta(days=x) for x in range(0, numdays)]

    target_tags = get_filter_tags(catalogue, targets=True)
    katpt_targets = catalogue.filter(target_tags)

    for cnt, katpt_target in enumerate(katpt_targets):
        plt.figure(figsize=(17, 7), facecolor="white")
        ax = plt.subplot(111)
        plt.subplots_adjust(right=0.8)
        fontP = FontProperties()
        fontP.set_size("small")
        rise_times = []
        set_times = []
        for the_date in date_list:
            ref_antenna.observer.date = the_date
            risetime = ref_antenna.observer.next_rising(katpt_target.body)
            settime = ref_antenna.observer.next_setting(katpt_target.body,
                                                        risetime)
            risetime = risetime.datetime().time()
            rise_times.append(risetime.hour + risetime.minute / 60.0)
            settime = settime.datetime().time()
            set_times.append(settime.hour + settime.minute / 60.0)

        myplot, = plt.plot_date(date_list,
                                rise_times,
                                fmt=".",
                                linewidth=0,
                                label="{} rising".format(katpt_target.name))
        myplot, = plt.plot_date(date_list,
                                set_times,
                                fmt=".",
                                linewidth=0,
                                label="{} setting".format(katpt_target.name))
        ax.axhspan(7.25, 17.5, facecolor="k", alpha=0.2)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.95, box.height])
        plt.grid()
        plt.legend(loc='center left',
                   bbox_to_anchor=(1, 0.5),
                   prop={'size': 10},
                   numpoints=1)
        plt.ylabel("Time UTC (hour)")
        plt.yticks(numpy.arange(0.0, 24.0, 1.0), fontsize=10)
        ax.set_xticklabels(date_list[0::20], rotation=30, fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=range(30),
                                                     interval=10))
        ax.set_xlabel("Date")


# source elevation over time (24H) plot
def source_elevation(catalogue, ref_antenna):
    """Generate a plot of elevation over time for 24 hour period.

    For all sources in provided catalogue at a specific location

    Parameters
    ----------
    catalogue: katpoint.Catalogue
    ref_antenna: katpoint.Antenna
        A MeerKAT reference antenna

    Returns
    -------
        matplotlib figure handle

    """
    catalogue.antenna = ref_antenna
    horizon = numpy.degrees(ref_antenna.observer.horizon)
    # All times and timestamps assumed UTC, no special conversion to
    # accommodate SAST allowed to prevent confusion
    creation_date = catalogue.antenna.observer.date
    creation_timestamp = datetime2timestamp(creation_date.datetime())
    time_range = creation_timestamp + numpy.arange(0, 24.0 * 60.0 * 60.0, 360.0)
    timestamps = [timestamp2datetime(ts) for ts in time_range]

    fig = plt.figure(figsize=(15, 7), facecolor="white")
    ax = plt.subplot(111)
    plt.subplots_adjust(right=0.8)
    fontP = FontProperties()
    fontP.set_size("small")

    for cnt, target in enumerate(catalogue.targets):
        elev = []
        for idx, timestamp in enumerate(timestamps):
            catalogue.antenna.observer.date = ephem.Date(timestamp)
            target.body.compute(catalogue.antenna.observer)
            elev.append(numpy.degrees(target.body.alt))

        label = "{} ".format(target.name)
        rm_tags = ["radec", "special", "target"]
        for rm_tag in rm_tags:
            if rm_tag in target.tags:
                target.tags.remove(rm_tag)
        label += ", ".join(target.tags)

        myplot, = plt.plot_date(timestamps,
                                elev,
                                fmt='.',
                                linewidth=0,
                                label=label)
    ax.axhspan(15, horizon, facecolor="k", alpha=0.1)
    plt.grid()
    plt.legend(loc='center left',
               bbox_to_anchor=(1, 0.5),
               prop={'size': 10},
               numpoints=1)
    plt.ylabel("Elevation (deg)")
    plt.ylim(15, 90)
    plt.yticks(fontsize=10)

    # fix tick positions for proper time axis display
    utc_hrs = [timestamps[0] + timedelta(hours=hr) for hr in range(0, 25, 1)]
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax.set_xlim(utc_hrs[0], utc_hrs[-1])
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(24),
                                                  interval=1))
    locs = ax.get_xticks()
    locs_labels = matplotlib.dates.num2date(locs)
    locator = matplotlib.ticker.FixedLocator(locs)
    ax.xaxis.set_major_locator(locator)
    utc_timestamps = [locs_lbl.strftime("%H:%M") for locs_lbl in locs_labels]

    lst_timestamps = []
    for locs_ts in locs_labels:
        catalogue.antenna.observer.date = ephem.Date(locs_ts)
        lst_time = "{}".format(catalogue.antenna.observer.sidereal_time())
        lst_time_str = datetime.strptime(lst_time,
                                         "%H:%M:%S.%f").strftime("%H:%M")
        lst_timestamps.append(lst_time_str)

    ax.set_xticklabels(lst_timestamps,
                       rotation=30,
                       fontsize=10)
    ax.set_xlabel("Local Sidereal Time")

    ax2 = ax.twiny()
    box = ax2.get_position()
    ax2.set_position([box.x0, box.y0, box.width * 0.9, box.height])
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(ax.get_xticks())
    ax2.xaxis.set_major_locator(locator)
    ax2.set_xticklabels(utc_timestamps,
                        rotation=30,
                        fontsize=10)
    ax2.set_xlabel('Time (UTC) starting from {}'.format(datetime.utcfromtimestamp(
        creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')))

    return fig


class bcolors:
    """Output observation target stats.

    Helper class for command line color output

    """

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def table_line(datetime,
               target,
               horizon,
               sep_angle=None,
               cal_limit=None,
               sol_limit=None,
               lst=False,
               notes="",
               ):
    """Construct a line of target information to display on command line output.

    Parameters
    ----------
    datetime: ephem.Date
        ephem date and time object
    target: katpoint.Catalogue
        target from katpoint.Catalogue object
    horizon: float
        minimum pointing angle in degrees
    sep_angle: float
        separation angle in degrees [optional param]
    cal_limit: float
        maximum separation angle between target and calibrator [optional]
    sol_limit: float
        minimum separation angle between target and Sun [optional]
    lst: str
        display times in LST rather than UTC
    notes: str
        user provided extra information

    Returns
    -------
        <name> <risetime UTC> <settime UTC> <Separation> <Notes>

    """
    observatory = Observatory(horizon=horizon, datetime=datetime)
    [rise_time,
     set_time] = observatory.target_rise_and_set_times(target.body,
                                                       lst=lst)

    if type(rise_time) is ephem.Angle:
        rise_time = str(rise_time)
        set_time = str(set_time)
    elif type(rise_time) is ephem.Date:
        rise_time = rise_time.datetime().strftime("%H:%M:%S")
        set_time = set_time.datetime().strftime("%H:%M:%S")
    else:
        rise_time = None
        set_time = None

    clo_clr = bcolors.ENDC
    sep_note = ""
    if sep_angle is not None:
        sep_note = "%.2f" % sep_angle
        if cal_limit is not None:
            if sep_angle > cal_limit:
                clo_clr = bcolors.WARNING
                sep_note += " ***"
        if sol_limit is not None:
            if sep_angle < sol_limit:
                clo_clr = bcolors.FAIL
                sep_note += " ***"

    # ephem has difference between defining astrometric coordinates
    # for FixedBody vs Body objects
    try:
        RA = target.body._ra
        DECL = target.body._dec
    except AttributeError:
        RA = target.body.a_ra
        DECL = target.body.a_dec
    table_info = "{: <16}{: <32}{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n".format(
        target.name,
        " ".join(target.tags),
        str(RA),
        str(DECL),
        rise_time,
        set_time,
        sep_note,
        notes,
    )
    return clo_clr + table_info + bcolors.ENDC


# Create observation table
def obs_table(ref_antenna,
              catalogue,
              ref_tgt_list=[],
              solar_sep=90.,
              lst=False,
              ):
    """Construct a command line table to displaying catalogue target information.

    Parameters
    ----------
    ref_antenna: katpoint Antenna object
        reference location of antenna for pointing calculation
    catalogue: katpoint.Catalogue
        catalogue of targets
    ref_tgt_list: list
        reference targets for calibrator selection [optional]
    solar_sep: float
        minimum solar separation angle [optional]
    lst: datetime
        LST

    Returns
    -------
    observation_table:
        Observation table file in the form
        <name> <tag> <risetime> <settime> <Separation> <Notes>

    """
    creation_time = ref_antenna.observer.date
    horizon = numpy.degrees(ref_antenna.observer.horizon)
    observation_table = "\nObservation Table for {} (UTC)\n".format(
        creation_time)
    date_str = "UTC"
    if lst:
        date_str = "LST"
    observation_table += "Times listed in {} for target rise and set times\n".format(
        date_str)
    observation_table += "Target visible when above {} degrees\n".format(
        horizon)
    _table = "{: <16}{: <32}{: <16}{: <16}{: <16}{: <16}{: <16}{: <16}\n".format(
        "Sources", "Class", "RA", "Decl", "Rise Time", "Set Time", "Separation", "Notes"
    )
    observation_table += _table

    sun = katpoint.Target("Sun, special")
    sun.body.compute(ref_antenna.observer)

    calibrator_tags, target_tags = get_filter_tags(catalogue)
    katpt_targets = catalogue.filter(target_tags)
    katpt_calibrators = catalogue.filter(calibrator_tags)

    for cnt, target in enumerate(katpt_targets):
        note = ""
        if cnt < 1:
            note = "Separation from Sun"
        target.body.compute(ref_antenna.observer)
        try:
            separation_angle = ephem.separation(sun.body, target.body)
            sol_sep_angle = numpy.degrees(separation_angle)
        except TypeError:
            # not a Body or Observer object, ignore separation calculation
            sol_sep_angle = None
        observation_table += table_line(ref_antenna.observer.date,
                                        target,
                                        horizon,
                                        sep_angle=sol_sep_angle,
                                        sol_limit=solar_sep,
                                        lst=lst,
                                        notes=note,
                                        )

    current_target = ""
    for calibrator in katpt_calibrators:
        # find closest reference target
        calibrator.body.compute(ref_antenna.observer)
        if len(ref_tgt_list) < 1:
            ref_tgt_list = katpt_targets.targets
        sep_angles = []
        for tgt in ref_tgt_list:
            # ignore some special targets
            if sol_sep_angle is None:
                continue
            tgt.body.compute(ref_antenna.observer)
            sep_angles.append(ephem.separation(calibrator.body, tgt.body))
        note = ""
        separation_angle = None
        if len(sep_angles) > 0:
            tgt_idx = numpy.argmin(sep_angles)
            target = ref_tgt_list[tgt_idx]
            separation_angle = numpy.degrees(sep_angles[tgt_idx])
            if current_target != target.name:
                note = "Separation from {}".format(target.name)
                current_target = target.name
        observation_table += table_line(ref_antenna.observer.date,
                                        calibrator,
                                        horizon,
                                        sep_angle=separation_angle,
                                        cal_limit=15,
                                        lst=lst,
                                        notes=note)

    return observation_table

# --Output observation target stats--


# --write observation catalogue--
# construct supplementary header information
def write_header(header_info, userheader=""):
    """Create fancy header to add at the top of the calibrator catalogue.

    Adding information such as proposal ID, PI, contact details

    """
    catalogue_header = userheader
    if header_info is not None:
        catalogue_header += "# Observation catalogue for proposal ID {}\n".format(
            header_info['proposal_id'])
        catalogue_header += "# PI: {}\n".format(
            header_info['pi_name'])
        catalogue_header += "# Contact details: {}\n".format(
            header_info['pi_contact'])
    return catalogue_header


# write observation catalogue using katpoint functionality
def write_catalogue(filename, catalogue_header, katpoint_catalogue):
    """Add all katpoint.Catalogue object targets to CVS file.

    Parameters
    ----------
    filename: str
        The file which contains the targets and calibrators
    catalogue_header: str
        Header information for targets and calibrators
    katpoint_catalogue: katpoint.Catalogue
        All katpoint.Catalogue objects to be added to observation csv

    Returns
    -------
        A csv file catalogue with header descriptions columns and rows as various targets
        and calibrators

    """
    katpoint_catalogue.save(filename)
    with open(filename, "r+") as fcat:
        sources = fcat.readlines()
        fcat.seek(0)
        fcat.write(catalogue_header)
        for target in sources:
            fcat.write(target)

# --write observation catalogue--


# --utility functions to replace katpoint calculations--
def _separation_angles(katpt_catalogue, target, observer):
    """Calculate the separation angle between a target.

    and all the calibrators in the provided catalogue

    Parameters
    ----------
    katpt_catalogue: katpoint.Catalogue
    target: ephem.FixedBody
    observer: ephem.Observer

    Returns
    -------
    separation_angles: list
        List of separation angles in radians

    """
    target.compute(observer)
    separation_angles = []
    for calib in katpt_catalogue:
        calib.body.compute(observer)
        separation_angles.append(ephem.separation(target, calib.body))
    return separation_angles


def _closest_calibrator_(katpt_catalogue, target, observer):
    """Find the closest calibrator to a target.

    Parameters
    ----------
    katpt_catalogue: katpoint.Catalogue
    target: ephem.FixedBody
    observer: ephem.Observer

    Returns
    -------
    katpoint.Target: katpoint.Target object
        closest calibrator
    separation_angle: float
        separation_angle in degrees

    """
    separation_angles = _separation_angles(katpt_catalogue, target, observer)
    closest_idx = numpy.argmin(separation_angles)
    separation = numpy.degrees(separation_angles[closest_idx])
    calibrator = katpt_catalogue.targets[closest_idx]
    return calibrator, separation


# --utility functions to replace katpoint calculations--


# Find closest calibrator to target from catalogue of calibrators
def get_cal(catalogue, katpt_target, ref_antenna):
    """Find closest calibrator to target from catalogue of calibrators.

    Parameters
    ----------
    catalogue: katpoint.Catalogue
    katpt_target: katpoint.Target
    ref_antenna: katpoint.Antenna

    Returns:
    ------
    calibrator: katpoint.Target
        closest calibrator
    separation_angle: float
        separation angle in degrees

    """
    calibrator, separation = _closest_calibrator_(
        catalogue, katpt_target.body, ref_antenna.observer
    )
    return calibrator, separation


# Find calibrator with best coverage (>80%) of target visibility period
# else return 2 calibrators to cover the whole target visibility period
def best_cal_cover(catalogue, katpt_target, ref_antenna):
    """Find calibrator with best coverage (>80%) of target visibility period.

    else return 2 calibrators to cover the whole target visibility period

    Parameters
    ----------
    catalogue: katpoint.Catalogue
    katpt_target: katpoint.Target
    ref_antenna: katpoint.Antenna

    Returns
    -------
    calibrator: katpoint.Target object
        closest calibrator
    separation_angle: float
        separation angle in degrees
    buffer_calibrator: katpoint.Target object
        additional calibrator for LST coverage
    buffer_separation: float
        additional separation_angle in degrees

    """
    calibrator, separation = _closest_calibrator_(
        catalogue, katpt_target.body, ref_antenna.observer
    )
    buffer_calibrator = None
    buffer_separation = 180.0
    horizon = numpy.degrees(ref_antenna.observer.horizon)
    if separation > 20.0:  # calibrator rises some time after target
        # add another calibrator preceding the target
        observatory = Observatory(horizon=horizon,
                                  datetime=ref_antenna.observer.date)
        [tgt_rise_time,
         tgt_set_time] = observatory.target_rise_and_set_times(katpt_target.body,
                                                               lst=False)
        closest_cals = []
        for each_cal in catalogue:
            try:
                [cal_rise_time,
                 cal_set_time] = observatory.target_rise_and_set_times(each_cal.body,
                                                                       lst=False)
            except ephem.NeverUpError:
                continue
            except ephem.AlwaysUpError:
                continue
            delta_time_to_cal_rise = cal_set_time - tgt_rise_time
            if delta_time_to_cal_rise > 0:
                # calc that rise before the target
                closest_cals.append([each_cal.name, delta_time_to_cal_rise])
            delta_time_to_cal_set = tgt_set_time - cal_rise_time
            if delta_time_to_cal_set > 0:
                # calc that sets after the target
                closest_cals.append([each_cal.name, delta_time_to_cal_set])
        if len(closest_cals) > 0:
            buffer_cal_idx = numpy.array(closest_cals)[:, 1].astype(float).argmin()
            buffer_calibrator = catalogue[closest_cals[buffer_cal_idx][0]]
            buffer_separation = ephem.separation(katpt_target.body,
                                                 buffer_calibrator.body)
            buffer_separation = numpy.degrees(buffer_separation)
    return calibrator, separation, buffer_calibrator, buffer_separation


def add_target(target, catalogue, tag=""):
    """Add target to catalogue.

    Parameters
    ----------
    target: katpoint.Target object
    catalogue: katpoint.Catalogue object
    tag: str
        target tag

    Returns
    -------
    catalogue: katpoint.Catalogue

    """
    if catalogue.__contains__(target.name):
        if tag not in catalogue[target.name].tags:
            catalogue[target.name].tags.append(tag)
    else:
        catalogue.add(target, tags=tag)
    return catalogue


def main(creation_time,
         horizon=20.,
         solar_angle=20.,
         cal_tags=None,
         target=None,
         header_info=None,
         view_tags=None,
         mkat_catalogues=False,
         lst=False,
         all_cals=False,
         user_text_only=False,
         save_fig=False,
         infile=None,
         viewfile=None,
         outfile=None,
         **kwargs):
    """Run calibration observation."""

    # set defaults
    if cal_tags is None:
        cal_tags = ['gain']
    if view_tags is None:
        view_tags = ['elevation']

    observatory = Observatory()
    location = observatory.location
    node_config_available = observatory.node_config_available
    ref_antenna = katpoint.Antenna(location)
    ref_antenna.observer.date = ephem.Date(creation_time)
    ref_antenna.observer.horizon = ephem.degrees(str(horizon))

    text_only = (user_text_only or global_text_only)

    if viewfile is not None:
        # check if view file in CSV or YAML
        data_dict = read_yaml(viewfile)
        if data_dict:
            catalogue = katpoint.Catalogue()
            catalogue.antenna = ref_antenna
            for observation_cycle in data_dict["observation_loop"]:
                for target_item in observation_cycle["target_list"]:
                    name, target = katpoint_target_string(target_item)
                    catalogue.add(katpoint.Target(target))
        else:  # assume CSV
            # output observation stats for catalogue
            with open(viewfile, 'r') as fin:
                catalogue = katpoint.Catalogue(fin)
        obs_summary = obs_table(
            ref_antenna,
            catalogue=catalogue,
            solar_sep=solar_angle,
            lst=lst,
        )
        print(obs_summary)

        if not text_only:
            for view_option in view_tags:
                cp_cat = deepcopy(catalogue)
                if "elevation" in view_option:
                    plot_func = source_elevation
                if "solarangle" in view_option:
                    plot_func = source_solar_angle
                if "riseset" in view_option:
                    plot_func = source_rise_set
                plot_func(cp_cat, ref_antenna)
            plt.show()
        return

    if mkat_catalogues and os.path.isdir(mkat_catalogues):
        catalogue_path = mkat_catalogues
        config_file_available = True
    else:
        catalogue_path = "katconfig/user/catalogues"
        config_file_available = False

    # before doing anything, verify that calibrator catalogues can be accessed
    if not os.path.isdir(catalogue_path) and not node_config_available:
        msg = "Could not access calibrator catalogue default location\n"
        msg += "add explicit location of catalogue folder using --cat-path <dirname>"
        raise RuntimeError(msg)

    # constructing observational catalogue
    observation_catalogue = katpoint.Catalogue()
    observation_catalogue.antenna = ref_antenna

    # targets to obtain calibrators for
    header = ""
    cal_targets = []
    if target is not None:
        if len(target) > 2:
            # input target from command line
            target = [tgt.strip() for tgt in target]
            target = ", ".join(
                map(str, [target[0], "radec target", target[1], target[2]])
            )
            cal_targets = [katpoint.Target(target)]
        elif len(target) < 2:
            # input solar body from command line
            solar_body = target[0].capitalize()
            katpt_target = katpoint.Target("{}, special".format(solar_body))
            cal_targets = [katpt_target]
        else:  # if len(target) == 2
            # input target from command line
            target = [tgt.strip() for tgt in target]
            target = ", ".join(
                map(str, [target[0], "xephem target", target[1]]))
            cal_targets = [katpoint.Target(target)]
    else:  # assume the targets are in a file
        if infile is None:
            raise RuntimeError('Specify --target or CSV catalogue --infile')
        with open(infile, "r") as fin:
            # extract targets tagged to be used for calibrator selection
            for line in fin.readlines():
                if line[0] == "#":  # catch and keep header lines
                    header += line
                    continue
                if len(line) < 1:  # ignore empty lines
                    continue
                if "calref" in line:
                    target = line.strip().replace("calref", "target")
                    cal_targets.append(katpoint.Target(target))
                else:  # add target to catalogue
                    target = line.strip().replace("radec", "radec target")
                    observation_catalogue.add(katpoint.Target(target))
        # if not reference target for calibrator selection is specified,
        # simply select the first target listed in the catalogue
        if len(cal_targets) < 1:
            cal_targets = [observation_catalogue.targets[0]]

    for target in cal_targets:
        # add calibrator catalogues and calibrators to catalogue
        for cal_tag in cal_tags:
            cal_catalogue = os.path.join(
                catalogue_path,
                "Lband-{}-calibrators.csv".format(caltag_dict[cal_tag])
            )
            try:
                fin = open(cal_catalogue, 'r')
                if config_file_available:
                    calibrators = katpoint.Catalogue(fin)
                elif node_config_available:
                    calibrators = katpoint.Catalogue(
                        observatory.read_file_from_node_config(cal_catalogue)
                    )
                else:  # user specified calibrator file
                    calibrators = katpoint.Catalogue(fin)
            except (AssertionError, IOError):
                msg = bcolors.WARNING
                msg += "Unable to open {}\n".format(cal_catalogue)
                msg += "Observation file will still be created,"
                "please add calibrator manually\n"
                msg += bcolors.ENDC
                print(msg)
                continue
            if "gain" in cal_tag or "delay" in cal_tag:
                # for secondary calibrators such as gain:
                # find the closest calibrator
                calibrator, separation_angle = get_cal(calibrators, target, ref_antenna)
                observation_catalogue = add_target(
                    calibrator, observation_catalogue, tag=cal_tag + "cal"
                )
            else:
                # for primary calibrators:
                if all_cals:
                    # show all calibrators
                    for calibrator in calibrators:
                        observation_catalogue = add_target(
                            calibrator, observation_catalogue, tag=cal_tag + "cal"
                        )
                else:
                    # find the best coverage over the target visibility period
                    [calibrator,
                     separation_angle,
                     buffer_calibrator,
                     buffer_calibrator_separation_angle] = best_cal_cover(
                        calibrators, target, ref_antenna
                    )
                    if (
                        buffer_calibrator is not None
                        and buffer_calibrator_separation_angle < 90.0
                    ):
                        observation_catalogue = add_target(
                            buffer_calibrator,
                            observation_catalogue,
                            tag=cal_tag + "cal",
                        )
                    observation_catalogue = add_target(
                        calibrator, observation_catalogue, tag=cal_tag + "cal"
                    )
        observation_catalogue = add_target(target, observation_catalogue)

    # write observation catalogue
    catalogue_header = write_header(header_info, userheader=header)
    catalogue_data = observation_catalogue.sort()
    if outfile is not None:
        filename = os.path.splitext(os.path.basename(outfile))[0] + ".csv"
        outfile = os.path.join(os.path.dirname(outfile), filename)
        write_catalogue(outfile, catalogue_header, catalogue_data)
        print("Observation catalogue {}".format(outfile))

    # output observation stats for catalogue
    obs_summary = obs_table(
        ref_antenna,
        catalogue=catalogue_data,
        ref_tgt_list=cal_targets,
        solar_sep=solar_angle,
        lst=lst,
    )
    print(obs_summary)

    if global_text_only and not user_text_only:
        msg = "Required matplotlib functionalities not available\n"
        msg += "Cannot create elevation plot\n"
        msg += "Only producing catalogue file and output to screen"
        print(msg)

    if not text_only:
        # create elevation plot for sources
        obs_catalogue = catalogue_header
        for target in catalogue_data:
            obs_catalogue += "{}\n".format(target)
        source_elevation(observation_catalogue,
                         ref_antenna)
        if save_fig:
            imfile = "elevation_utc_lst.png"
            print("Elevation plot {}".format(imfile))
            plt.savefig(imfile, dpi=300)
        plt.show()
        plt.close()


if __name__ == "__main__":
    # This code will take care of negative values for declination
    for i, arg in enumerate(sys.argv):
        if len(arg) < 2:
            continue
        if (arg[0] == "-") and arg[1].isdigit():
            sys.argv[i] = " " + arg

    args = cli(sys.argv[0])
    header_info = {'proposal_id': args.prop_id,
                   'pi_name': args.pi,
                   'pi_contact': args.contact}
    if args.target is not None:
        target = args.target
    elif args.body is not None:
        target = [args.body]
    elif args.xephem is not None:
        target = args.xephem
    else:
        target = None

    # check that files exists before continuing
    if args.infile is not None:
        if not os.path.isfile(args.infile):
            raise RuntimeError('Input file {} does not exist'.format(args.infile))
    if args.view is not None:
        if not os.path.isfile(args.view):
            raise RuntimeError('Catalogue file {} does not exist'.format(args.view))

    main(creation_time=args.datetime,
         horizon=args.horizon,
         solar_angle=args.solar_angle,
         cal_tags=args.cal_tags,
         target=target,
         header_info=header_info,
         view_tags=args.view_tags,
         mkat_catalogues=args.cat_path,
         lst=args.lst,
         all_cals=args.all_cals,
         user_text_only=args.text_only,
         save_fig=args.save_fig,
         infile=args.infile,
         viewfile=args.view,
         outfile=args.outfile)

# -fin-
