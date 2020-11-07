#!/usr/bin/env python
"""Take a catalogue file and construct a observation configuration file."""

from __future__ import print_function

from astrokat import Observatory, __version__
import argparse
import sys

from astrokat import obs_dict, obs_yaml

from contextlib import contextmanager


@contextmanager
def smart_open(filename):
    """Open catalogue file."""
    if filename and filename != "-":
        with open(filename, "w") as fout:
            yield fout
    else:
        yield sys.stdout


def cli(prog):
    """Parse command line options.

    Returns
    -------
    option arguments

    """
    usage = "{} [options] --infile <full_path/cat_file.csv>".format(prog)
    description = ("sources are specified as a catalogue of targets,"
                   "with optional timing information"
                   )
    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__)
    parser.add_argument(
        "--infile",
        type=str,
        required=True,
        help="filename of the CSV catalogue to convert (**required**)")
    parser.add_argument(
        "--outfile",
        type=str,
        help="filename for output observation file (default outputs to screen)")
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Verbose output for debug and verification')

    description = "instrument setup requirements"
    group = parser.add_argument_group(
        title="observation instrument setup", description=description
    )
    group.add_argument(
        "--product",
        type=str,
        help="observation instrument product configuration")
    group.add_argument(
        "--band",
        type=str,
        help="observation band: L, UHF, X, S")
    group.add_argument(
        "--integration-period",
        type=float,
        help="averaging time per dump [sec]")

    description = (
        "track a target for imaging or spectral line observations,"
        "may optionally have a tag of 'target'."
    )
    group = parser.add_argument_group(
        title="target observation strategy", description=description
    )
    group.add_argument(
        "--lst",
        type=str,
        help="observation start LST or LST range")
    group.add_argument(
        "--target-duration",
        type=float,
        default=300,  # sec
        help="default target track duration [sec]")
    group.add_argument(
        "--max-duration",
        type=float,
        help="maximum duration of observation [sec]")

    description = (
        "calibrators are identified by tags in their description strings"
        "'bpcal', 'gaincal', 'fluxcal' and 'polcal' respectively"
    )
    group = parser.add_argument_group(
        title="calibrator observation strategy", description=description
    )
    group.add_argument(
        "--primary-cal-duration",
        type=float,
        default=300,  # sec
        help="minimum duration to track primary calibrators tagged as "
        "'bpcal', 'fluxcal' or 'polcal' [sec]")
    group.add_argument(
        "--primary-cal-cadence",
        type=float,
        help="minimum observation interval between primary calibrators [sec]")
    group.add_argument(
        "--secondary-cal-duration",
        type=float,
        default=60,  # sec
        help="minimum duration to track gain calibrator, 'gaincal' [sec]")
    return parser


class UnpackCatalogue(object):
    """Unpack catalogue, assuming comma-separated values.

    Parameters
    ----------
    filename: file with no header lines are allowed, only target information
          Input format: name, tags, ra, dec

    Returns
    --------
        Target list with parameter header

    """

    def __init__(self, filename):
        self.infile = filename

    def tidy_tags(self, tags):
        """Cleanup catalogue tags and construct expected tag format."""
        tags = tags.split()
        # add target tag if not a calibrator
        if not any("cal" in tag for tag in tags):
            if "target" not in tags:
                tags.append("target")
        return " ".join(tags)

    def read_catalogue(self,
                       target_duration="",
                       gaincal_duration="",
                       bpcal_duration="",
                       bpcal_interval=None,
                       ):
        """Unpack all targets from catalogue files into list.

        Parameters
        ----------
        target_duration: float
            Duration on target
        gaincal_duration: float
            Duration on gain calibrator
        bpcal_duration: float
            Duration on bandpass calibrator
        bpcal_interval: float
            How frequent to visit the bandpass calibrator

        """
        target_dict_list = []
        header = ""
        with open(self.infile, "r") as fin:
            info = fin.readlines()
        for idx, line in enumerate(info):
            target_dict = obs_dict.get_target_dict()
            # keep header information
            if line[0] == "#":
                header += line
                continue
            # skip blank lines
            if len(line) < 2:
                continue
            try:
                # unpack data columns
                data_columns = [each.strip() for each in line.strip().split(",")]
            except ValueError:
                print("Could not unpack line:{}".format(line))
                continue
            else:
                if len(data_columns) < 4:
                    [name, tags] = data_columns
                    if 'special' not in tags:
                        raise RuntimeError('Unknown target type')
                    x_coord = ''
                    y_coord = ''
                else:
                    [name, tags, x_coord, y_coord] = data_columns[:4]
                flux = None
                if len(data_columns) > 4:
                    flux = " ".join(data_columns[4:])
                    # skip empty brackets it means nothing
                    if len(flux[1:-1]) < 1:
                        flux = None

            tags = self.tidy_tags(tags.strip())
            if tags.startswith("azel"):
                prefix = "azel"
            elif tags.startswith("gal"):
                prefix = "gal"
            elif tags.startswith("special"):
                prefix = "special"
            else:
                prefix = "radec"
            if len(name) < 1:
                name = "target{}_{}".format(idx, prefix)

            target_dict['name'] = name
            target_dict['coord'] = [prefix, " ".join([x_coord, y_coord])]
            target_dict['tags'] = tags[len(prefix):].strip()
            target_dict['duration'] = target_duration
            if 'cal' in target_dict['tags']:
                if 'gaincal' in target_dict['tags']:
                    target_dict['duration'] = gaincal_duration
                else:
                    target_dict['duration'] = bpcal_duration
                    if bpcal_interval is not None:
                        target_dict['cadence'] = bpcal_interval
            if flux is not None:
                target_dict['flux_model'] = flux
            target_dict_list.append(target_dict)

        return header, target_dict_list


class BuildObservation(object):
    """Create a default observation config file.

    Parameters
    ----------
    target_list: list
        A list of targets with the format
        'name=<name>, radec=<HH:MM:SS.f>,<DD:MM:SS.f>, tags=<tags>, duration=<sec>'
        'name=<name>, special=<ephem>, tags=<tags>, duration=<sec>'

    """

    def __init__(self, target_dict_list):
        self.target_dict_list = target_dict_list
        self.target_list = []
        for target_dict in target_dict_list:
            target = obs_yaml.target_str(target_dict)
            self.target_list.append(target)
        self.configuration = None
        # list of targets with ra, dec for LST calculation
        self.lst_list = [tgt
                         for tgt in self.target_list if "radec" in tgt]

    def configure(self,
                  instrument={},
                  obs_duration=None,
                  lst=None):
        """Set up of the MeerKAT telescope for running observation.

        Parameters
        ----------
        instrument: dict
            Correlator configuration
        obs_duration: dict
            Duration of observation
        lst: datetime
            Local Sidereal Time at telescope location

        """
        # LST times only HH:MM in OPT
        start_lst = Observatory().start_obs(self.lst_list, str_flag=True)
        start_lst = ":".join(start_lst.split(":")[:-1])
        end_lst = Observatory().end_obs(self.lst_list, str_flag=True)
        end_lst = ":".join(end_lst.split(":")[:-1])
        if lst is None:
            lst = "{}-{}".format(start_lst, end_lst)

        # observational setup
        self.configuration = obs_yaml.obs_str(instrument,
                                              obs_duration,
                                              lst,
                                              self.target_dict_list)

    def write_yaml(self,
                   header=None,
                   configuration=None,
                   outfile=None):
        """Write the yaml observation file.

        Returns
        -------
        Configuration file for the observation

        """
        if configuration is not None:
            self.configuration = configuration
        if self.configuration is None:
            raise RuntimeError("No observation configuration to output")

        init_str = ""
        if header is not None:
            init_str = header
        init_str += self.configuration

        with smart_open(outfile) as fout:
            fout.write(init_str)


def ext_instrument(args):
    """Correlator setup instructions"""
    instrument = obs_dict.get_instrument_dict()
    if args.product is not None:
        instrument['product'] = args.product 
    if args.band is not None:
        instrument['band'] = args.band
    if args.integration_period is not None:
        instrument['integration_period'] = args.integration_period
    return obs_dict.remove_none_inputs_(instrument)


def ext_duration(args):
    """Total duration of observation"""
    durations = obs_dict.get_durations_dict()
    if args.max_duration is not None:
        durations["obs_duration"] = args.max_duration
    return obs_dict.remove_none_inputs_(durations)
    

if __name__ == "__main__":
    parser = cli(sys.argv[0])
    args = parser.parse_args()

    # read instrument requirements if provided
    instrument = ext_instrument(args)
    if args.debug:
        print('instrument\n', instrument)

    # set observation duration if specified
    duration = ext_duration(args)
    if args.debug:
        print('duration\n', duration)

    # read targets from catalogue file
    cat_obj = UnpackCatalogue(args.infile)
    header, catalogue = cat_obj.read_catalogue(
        target_duration=args.target_duration,
        gaincal_duration=args.secondary_cal_duration,
        bpcal_duration=args.primary_cal_duration,
        bpcal_interval=args.primary_cal_cadence,
    )
    if args.debug:
        print('header\n', header)
        print('catalogue\n', catalogue)

    obs_plan = BuildObservation(catalogue)
    if args.debug:
        print('target_str\n', obs_plan.target_list)
    # create observation configuration file
    obs_plan.configure(instrument=instrument,
                       obs_duration=duration,
                       lst=args.lst
                       )
    if args.debug:
        print('output\n', obs_plan.configuration)
    obs_plan.write_yaml(header=header, outfile=args.outfile)

# -fin-
