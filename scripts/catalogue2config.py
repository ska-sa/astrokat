# Take a catalogue file and construct a basic observation configuration file
import argparse
import os
import sys
from astrokat import Observatory


## TODO: need to move to utility
from contextlib import contextmanager
@contextmanager
def smart_open(filename):
    if filename and filename != '-':
        with open(filename, 'w') as fout:
            yield fout
    else:
        yield sys.stdout

## parsing command line options and return arguments
def cli(prog):
    version = "{} 0.1".format(prog)
    usage = "{} [options] --catalogue <full_path/cat_file.csv>".format(prog)
    description = "Sources are specified either as a catalogue of targets." \
            " Each source is tracked for a specified time." \
            " At least one target must be specified."
    parser = argparse.ArgumentParser(
        usage=usage,
        description=description)
    parser.add_argument(
        '--version',
        action='version',
        version=version)
    parser.add_argument(
        '--catalogue',
        type=str,
        required=True,
        help='Full path and name of catalogue file to convert (**required**)')
    parser.add_argument(
        '--obsfile',
        type=str,
        help='Filename for output observation layout file (default outputs to screen)')

    description = "Instrument setup requirements.\n" \
            "Leave options out if unsure, system will default to available setup at execution."
    group = parser.add_argument_group(title="Observation Instrument Setup",
                                      description=description)
    group.add_argument(
        '--product',
        type=str,
        help='Observation instrument product configuration')
    group.add_argument(
        '--band',
        type=str,
        help='Observation band: L, UHF, X, S')
    group.add_argument(
        '--dump-rate',
        type=int,
        help='Averaging time per dump [sec]')
    group.add_argument(
        '--antennas',
        type=str,
        nargs='+',
        help="List of antennas required for this observation to run.")
    group.add_argument(
        '--ptuse',
        action='store_true',
        help='Beamformer pipeline')
    group.add_argument(
        '--noise-source',
        type=float,
        nargs=2,
        metavar=('CYCLE_LEN', 'ON_FRAC'),
        help="Initiate a noise diode pattern on all antennas, "
             "<cycle_length_sec> <on_fraction>")
    group.add_argument(
        '--noise-pattern',
        type=str,
        default='all',
        help="How to apply the noise diode pattern: \
             'all' to set the pattern to all dishes simultaneously (default), \
             'cycle' to set the pattern so loop through the antennas in some fashion, \
             'm0xx' to set the pattern to a single selected antenna.")

    description = "Track a target for imaging or spectral line observations, visit " \
                  "bandpass and gain calibrators along the way. The calibrators " \
                  "are identified by tags in their description strings ('bpcal' " \
                  "'gaincal', 'fluxcal' and 'polcal', respectively), while the imaging targets may " \
                  "optionally have a tag of 'target'."
    group = parser.add_argument_group(title="Target Observation Strategy",
                                      description=description)
    group.add_argument(
        '--lst',
        type=str,
        help='Observation LST range (ex. 0-23 for anytime)')
    group.add_argument(
        '--target-duration',
        type=float,
        default=300,  # sec
        required=True,
        help='Default target track duration [sec] (default = %(default)ss)')
    group.add_argument(
        '--drift-scan',
        action='store_true',
        help='Perform drift scan across the targets instead of standard track')

    group = parser.add_argument_group(title="Calibrator Observation Strategy")
    group.add_argument(
        '--bpcal-duration',
        type=float,
        default=60,  # sec
        help='Minimum duration to track bandpass calibrator [sec] (default = %(default)ss)')
    group.add_argument(
        '--bpcal-interval',
        type=float,
        help='Minimum interval between bandpass calibrators [sec]')
    group.add_argument(
        '--gaincal-duration',
        type=float,
        default=60,  # sec
        help='Minimum duration to track gain calibrator [sec] (default=%(default)ss)')
    group.add_argument(
        '--gaincal-interval',
        type=float,
        help='Minimum interval between bandpass calibrators [sec]')

    return parser.parse_args()


## Assume comma separated values
#  No header lines are allowed, only target information
#  Input format: name, tags, ra, dec
class unpack_catalogue:
    def __init__(self, filename):
        self.infile = filename

    # cleanup catalogue tags and construct expected tag format
    def tidy_tags(self, tags):
        tags = tags.split()
        # add target tag if not a calibrator
        if not any('cal' in tag for tag in tags):
            if not 'target' in tags:
                tags.append('target')
        return ' '.join(tags)

    # unpack all targets from catalogue files into list
    def read_catalogue(self,
            target_duration='',
            gaincal_duration='',
            gaincal_interval=None,
            bpcal_duration='',
            bpcal_interval=None,
            ):
        target_list = []
        with open(self.infile, 'r') as fin:
            for idx, line in enumerate(fin.readlines()):
                try:
                    [name, tags, ra, dec] = line.strip().split(',')
                except ValueError:
                    print 'Could not unpack line:{}'.format(line)
                    continue

                tags = self.tidy_tags(tags.strip())
                if tags.startswith('azel'):
                    prefix = 'azel'
                elif tags.startswith('gal'):
                    prefix = 'gal'
                else:
                    prefix = 'radec'
                if len(name) < 1:
                    name = 'target{}_{}'.format(idx, prefix)
                target_items = [
                        name.strip(),
                        prefix,
                        ' '.join([ra.strip(), dec.strip()]),
                        tags[len(prefix):].strip(),
                        ]

                target_spec = 'name={}, {}={}, tags={}, duration={}'
                cadence = ', cadence={}'
                if 'target' in tags:
                    target_items.append(target_duration)
                elif 'bpcal' in tags:
                    target_items.append(bpcal_duration)
                    if bpcal_interval is not None:
                        target_spec += cadence
                        target_items.append(bpcal_interval)
                else:
                    target_items.append(gaincal_duration)
                    if gaincal_interval is not None:
                        target_spec += cadence
                        target_items.append(gaincal_interval)

                target = target_spec.format(*target_items)
                target_list.append(target)
        return target_list


## Create a default observation config file
#  Assume the format of a target in the list:
#  'name=<name>, radec=<HH:MM:SS.f>,<DD:MM:SS.f>, tags=<tags>, duration=<sec>'
class build_observation:
    def __init__(self, target_list):
        self.target_list = target_list
        self.configuration = None

    def configure(self,
            instrument={},
            noisediode={},
            lst=None,
            driftscan=False,
            ):
        obs_plan = {}
        # subarray specific setup options
        if len(instrument) > 0:
            obs_plan['instrument'] = instrument
        # noise diode setup
        if len(noisediode) > 0:
            obs_plan['noise_diode'] = noisediode
        start_lst = Observatory().start_obs(self.target_list)
        end_lst = Observatory().end_obs(self.target_list)
        # rounding errors can cause 24 LST, which will lead to an inf loop
        if float(end_lst) >= 24.0:
            end_lst = 23.9
        if (float(end_lst)-float(start_lst))< 0.:  # targets cover 24 hrs
            start_lst = 0.0
            end_lst = 23.9
        if lst is None:
            lst = '{}-{}'.format(start_lst, end_lst)
        # observational setup
        target_list = []
        calibrator_list = []
        for target in self.target_list:
            if 'cal' in target:
                # find and list calibrator targets
                calibrator_list.append(target)
            else:
                # set target observation type
                if driftscan:
                    target = ', '.join([target, 'type=drift_scan'])
                # list source targets
                target_list.append(target)
        obs_plan['observation_loop'] = [{
                'lst': lst,
                'target_list': target_list,
                'calibration_standards': calibrator_list,
                }]
        self.configuration = obs_plan
        return obs_plan


    def write_yaml(self,
            configuration=None,
            outfile='obs_config.yaml'):
        if configuration is not None:
            self.configuration = configuration
        if self.configuration is None:
            raise RuntimeError('No observation configuration to output')
        init_str = ''
        if 'instrument' in self.configuration.keys():
            init_str += 'instrument:\n'
            instrument = self.configuration['instrument']
            for key in instrument.keys():
                if instrument[key] is not None:
                    init_str += "  {}: {}\n".format(key, instrument[key])
        if 'noise_diode' in self.configuration.keys():
            init_str += 'noise_diode:\n'
            noise_diode= self.configuration['noise_diode']
            for key in noise_diode.keys():
                if noise_diode[key] is not None:
                    init_str += "  {}: {}\n".format(key, noise_diode[key])

        obs_loop = self.configuration['observation_loop'][0]
        init_str += '{}:\n'.format('observation_loop')
        init_str += "  - LST: {}\n".format(obs_loop['lst'])

        target_list = ''
        for target in obs_loop['target_list']:
            target_list += '      - {}\n'.format(target)
        try:
            calibrator_list = ''
            for target in obs_loop['calibration_standards']:
                calibrator_list += '      - {}\n'.format(target)
        except KeyError:
            pass  # option not available in this observation type

        with smart_open(outfile) as fout:
            fout.write(init_str)
            if len(target_list) > 0:
                fout.write('    target_list:\n{}'.format(target_list))
            if len(calibrator_list) > 0:
                fout.write('    calibration_standards:\n{}'.format(calibrator_list))

if __name__ == '__main__':
    args = cli(sys.argv[0])
    # read targets from catalogue file
    cat_obj = unpack_catalogue(args.catalogue)
    catalogue = cat_obj.read_catalogue(
            target_duration=args.target_duration,
            gaincal_duration=args.gaincal_duration,
            gaincal_interval=args.gaincal_interval,
            bpcal_duration=args.bpcal_duration,
            bpcal_interval=args.bpcal_interval,
            )
    obs_plan = build_observation(catalogue)
    # read instrument requirements if provided
    instrument = {}
    instrument['product'] = args.product
    instrument['band'] = args.band
    instrument['dump_rate'] = args.dump_rate
    instrument['pool_resources'] = args.antennas
    if args.ptuse:
        instrument['pool_resources'] += 'ptuse'
    # add noise diode usage
    noise_diode = {}
    if args.noise_source is not None:
        noise_diode = {'cycle_len': args.noise_source[0],
                       'on_fraction': args.noise_source[1],
                       'pattern': args.noise_pattern}
    # create observation configuration file
    obs_plan.configure(
            instrument=instrument,
            noisediode=noise_diode,
            lst=args.lst,
            driftscan=args.drift_scan)
    obs_plan.write_yaml(outfile=args.obsfile)

# -fin-
