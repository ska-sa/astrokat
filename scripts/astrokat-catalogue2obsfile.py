#!/usr/bin/env python
"""Take a catalogue file and construct a basic observation configuration file."""

from __future__ import print_function

from astrokat import Observatory
import argparse
import sys


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
    version = "{} 0.1".format(prog)
    usage = "{} [options] --infile <full_path/cat_file.csv>".format(prog)
    description = (
        "sources are specified as a catalogue of targets,"
        "with optional timing information"
    )
    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=version)
    parser.add_argument(
        "--infile",
        type=str,
        required=True,
        help="filename of the CSV catalogue to convert (**required**)",
    )
    parser.add_argument(
        "--outfile",
        type=str,
        help="filename for output observation file (default outputs to screen)",
    )

    description = "instrument setup requirements"
    group = parser.add_argument_group(
        title="observation instrument setup", description=description
    )
    group.add_argument(
        "--product", type=str, help="observation instrument product configuration"
    )
    group.add_argument("--band", type=str, help="observation band: L, UHF, X, S")
    group.add_argument(
        "--integration-period", type=float, help="averaging time per dump [sec]"
    )

    description = (
        "track a target for imaging or spectral line observations,"
        "may optionally have a tag of 'target'."
    )
    group = parser.add_argument_group(
        title="target observation strategy", description=description
    )
    group.add_argument("--lst", type=str, help="observation start LST or LST range")
    group.add_argument(
        "--target-duration",
        type=float,
        default=300,  # sec
        help="default target track duration [sec]",
    )
    group.add_argument(
        "--max-duration", type=float, help="maximum duration of observation [sec]"
    )

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
        "'bpcal', 'fluxcal' or 'polcal' [sec]",
    )
    group.add_argument(
        "--primary-cal-cadence",
        type=float,
        help="minimum observation interval between primary calibrators [sec]",
    )
    group.add_argument(
        "--secondary-cal-duration",
        type=float,
        default=60,  # sec
        help="minimum duration to track gain calibrator, 'gaincal' [sec]",
    )
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

    def read_catalogue(
        self,
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
        bpcal_interval: flat
            How frequent to visit the bandpass calibrator

        """
        target_list = []
        header = ""
        with open(self.infile, "r") as fin:
            for idx, line in enumerate(fin.readlines()):
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
                    [name, tags, ra, dec] = data_columns[:4]
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
                else:
                    prefix = "radec"
                if len(name) < 1:
                    name = "target{}_{}".format(idx, prefix)
                target_items = [
                    name,
                    prefix,
                    " ".join([ra, dec]),
                    tags[len(prefix):].strip(),
                ]

                target_spec = "name={}, {}={}, tags={}, duration={}"
                cadence = ", cadence={}"
                flux_model = ", model={}"
                if "target" in tags:
                    target_items.append(target_duration)
                elif "gaincal" in tags:
                    target_items.append(gaincal_duration)
                else:
                    target_items.append(bpcal_duration)
                    if bpcal_interval is not None:
                        target_spec += cadence
                        target_items.append(bpcal_interval)
                if flux is not None:
                    target_spec += flux_model
                    target_items.append(flux)
                try:
                    target = target_spec.format(*target_items)
                except IndexError:
                    msg = "Incorrect target definition\n"
                    msg += "Verify line: {}".format(line.strip())
                    raise RuntimeError(msg)
                target_list.append(target)
        return header, target_list


class BuildObservation(object):
    """Create a default observation config file.

    Parameters
    ----------
    target_list: list
        A list of targets with the format
        'name=<name>, radec=<HH:MM:SS.f>,<DD:MM:SS.f>, tags=<tags>, duration=<sec>'

    """

    def __init__(self, target_list):
        self.target_list = target_list
        self.configuration = None

    def configure(self, instrument={}, obs_duration=None, lst=None):
        """Set up of the MeerKAT telescope for running observation.

        Parameters
        ----------
        instrument: dict
            Correlator configuration
        obs_duration: float
            Duration of observation
        lst: datetime
            Local Sidereal Time at telescope location

        """
        obs_plan = {}
        # subarray specific setup options
        if len(instrument) > 0:
            obs_plan["instrument"] = instrument
        # set observation duration if specified
        if obs_duration is not None:
            obs_plan["durations"] = {"obs_duration": obs_duration}
        # LST times only HH:MM in OPT
        start_lst = Observatory().start_obs(self.target_list, str_flag=True)
        start_lst = ":".join(start_lst.split(":")[:-1])
        end_lst = Observatory().end_obs(self.target_list, str_flag=True)
        end_lst = ":".join(end_lst.split(":")[:-1])
        if lst is None:
            lst = "{}-{}".format(start_lst, end_lst)
        # observational setup
        obs_plan["observation_loop"] = [{"lst": lst, "target_list": self.target_list}]
        self.configuration = obs_plan
        return obs_plan

    def write_yaml(self, header=None, configuration=None, outfile="obs_config.yaml"):
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

        for each in self.configuration.keys():
            if each == "observation_loop":
                continue
            init_str += "{}:\n".format(each)
            values = self.configuration[each]
            for key in values.keys():
                if values[key] is not None:
                    init_str += "  {}: {}\n".format(key, values[key])

        obs_loop = self.configuration["observation_loop"][0]
        init_str += "{}:\n".format("observation_loop")
        init_str += "  - LST: {}\n".format(obs_loop["lst"])

        target_list = ""
        for target in obs_loop["target_list"]:
            target_list += "      - {}\n".format(target)

        with smart_open(outfile) as fout:
            fout.write(init_str)
            if len(target_list) > 0:
                fout.write("    target_list:\n{}".format(target_list))


if __name__ == "__main__":
    parser = cli(sys.argv[0])
    args = parser.parse_args()

    # read instrument requirements if provided
    instrument = {}
    for group in parser._action_groups:
        if "instrument setup" in group.title:
            group_dict = {
                a.dest: getattr(args, a.dest, None) for a in group._group_actions
            }
            instrument = vars(argparse.Namespace(**group_dict))
            break
    for key in instrument.keys():
        if instrument[key] is None:
            del instrument[key]

    # read targets from catalogue file
    cat_obj = UnpackCatalogue(args.infile)
    header, catalogue = cat_obj.read_catalogue(
        target_duration=args.target_duration,
        gaincal_duration=args.secondary_cal_duration,
        bpcal_duration=args.primary_cal_duration,
        bpcal_interval=args.primary_cal_cadence,
    )
    obs_plan = BuildObservation(catalogue)

    # create observation configuration file
    obs_plan.configure(
        instrument=instrument, obs_duration=args.max_duration, lst=args.lst
    )
    obs_plan.write_yaml(header=header, outfile=args.outfile)

# -fin-
