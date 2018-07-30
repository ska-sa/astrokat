import argparse
from katcorelib.observe import (standard_script_options)


# Add options for doing a beamformer observation
def beamformer_options(parser):
    description = "Dual polarisation beamforming on target. " \
                  "Note: Delay calibration observation is required for useful data."
    group = parser.add_argument_group(title="MeerKAT Tied-Array Options",
                                      description=description)
    group.add_argument('--bf-ants',
                       type=str,
                       action='append',
                       nargs='*',
                       help='List antennas to use in beamformer '
                            '(default is to use all antennas in subarray)')
    group.add_argument('--bf-weights',
                       default='normal',
                       help="Set per antenna weights for beamformer output: \
                            'normal' sets per antenna weight to 1/sqrt(N) (default), \
                            'natural' sets all antenna weights to 1, \
                            custom values will be assign equal to all antennas.")
    return parser


# Add options for doing an imaging observation
def image_options(parser):
    description = "Track a target for imaging or spectral line observations, visit " \
                  "bandpass and gain calibrators along the way. The calibrators " \
                  "are identified by tags in their description strings ('bpcal' " \
                  "and 'gaincal', respectively), while the imaging targets may " \
                  "optionally have a tag of 'target'."
    group = parser.add_argument_group(title="MeerKAT Imaging Options",
                                      description=description)
    group.add_argument('-b',
                       '--bpcal-duration',
                       type=float,
                       default=300,  # sec
                       help='Minimum duration to track bandpass calibrator [sec], '
                            '(default=%(default)s)')
    group.add_argument('-g',
                       '--gaincal-duration',
                       type=float,
                       default=60,  # sec
                       help='Minimum duration to track gain calibrator [sec], '
                            '(default=%(default)s)')
    group.add_argument('-i',
                       '--bpcal-interval',
                       type=float,
                       help='Minimum interval between bandpass calibrator visits, in seconds '
                            '(default is to observe as listed in order)')
    return parser


# Add standard observation script options from sessions
def session_options(parser,
                    x_short_opts=[],
                    x_long_opts=[]):
    # Add options from katcorelib that is valid for all observations
    parser_ = standard_script_options('','')
    # fudge parser_ class from OptionParser to Group
    group = parser.add_argument_group(
	title="Standard MeerKAT Options",
        description="Default observation script options")
    for opt in parser_.option_list:
        # Disregarding options we don't want in the group
        long_ = opt.__dict__['_long_opts'][0]
        if long_ in x_long_opts:
            continue
        args = opt.__dict__['_long_opts']
        if opt.__dict__['_short_opts']:
            short = opt.__dict__['_short_opts'][0]
            if short in x_short_opts:
                continue
            args = opt.__dict__['_short_opts'] + args

        kwargs = {'dest':opt.__dict__['dest'],
                  'type':type(opt.__dict__['default']) if type(opt.__dict__['default']) != tuple else None ,
                  'default':opt.__dict__['default'] if type(opt.__dict__['default']) != tuple else None ,
                  'nargs':opt.__dict__['nargs'] if opt.__dict__['nargs'] != 1 else None,
                  'metavar':opt.__dict__['metavar'] if not opt.__dict__['choices'] else '',
                  'choices':opt.__dict__['choices'],
                  'action':opt.__dict__['action'] if opt.__dict__['action'] != 'store_true' else None,
                  'const':opt.__dict__['const'] if opt.__dict__['action'] == 'store_const' else None,
                  'help': opt.__dict__['help'].replace("%default", "%(default)s") if long_ != '--quorum' else opt.__dict__['help'].replace("%", "%%"),
                  'required': True if '**required**' in opt.__dict__['help'] else False,
                  }

        group.add_argument(*args, **kwargs)
    return parser


def cli(prog,
        parser=None,
        x_short_opts=['-h'],
        x_long_opts=['--version']):

    if parser is None:
        # Set up standard script options
        version = "%s 0.1" % prog
        usage = "%s [options] -o <user> -t <sec> --target <target> / --catalogue <CSVfile> [<'target/catalogue'> ...]" % prog
        description = "Track one or more sources for a specified time." \
                      " At least one target must be specified." \
                      " Also note the **required** options."
        parser = argparse.ArgumentParser(usage=usage,
                                         description=description)

    # Standard track experiment options
    parser.add_argument('--version',
                        action='version', version=version)
    parser.add_argument('-t',
                        '--target-duration',
                        type=float,
                        required=True,
                        help='Minimum duration to track target [sec] (**required**)')
    parser.add_argument('--drift-scan',
                        action='store_true',
                        help='Perform drift scan across the targets instead of standard track')
    parser.add_argument('--noise-source',
                        type=float,
                        nargs=2,
                        help="Initiate a noise diode pattern on all antennas, "
                             "<cycle_length_sec> <on_fraction>")
    parser.add_argument('--noise-pattern',
                        type=str,
                        default='all',
                        help="How to apply the noise diode pattern: \
                             'all' to set the pattern to all dishes simultaneously (default), \
                             'cycle' to set the pattern so loop through the antennas in some fashion, \
                             'm0xx' to set the pattern to a single selected antenna.")
## Need to add a intertrack noise fire as session provides
    parser.add_argument('--target',
                        default=[],
                        type=str,
                        action='append',
                        nargs='+',
                        help='Target argument via name (\'Cygnus A\'), or '\
                             'description (\'azel, 20, 30\') (**required**)')
    parser.add_argument('--catalogue',
                        default=[],
                        type=str,
                        action='append',
                        nargs='+',
                        help='List of target coordinates in catalogue file, sources.csv (**required**)')

    # Add standard observation script options from sessions
    parser = session_options(parser, x_short_opts=x_short_opts, x_long_opts=x_long_opts)
    # Add options for doing an imaging observation
    parser = image_options(parser)
    # Add options for doing a beamformer observation
    parser = beamformer_options(parser)

    # Observation simulation for offline planning using actual observation script
    group = parser.add_argument_group(title="Observation Planning and Verifications",
                                      description = "Basic checks and output before starting and observation to ensure expected outcome")
    ex_group = group.add_mutually_exclusive_group()
    ex_group.add_argument('--visibility',
                          action='store_true',
                          help='Display short summary of target visibility') 
    ex_group.add_argument('--all-up',
                          action='store_true',
                          help='Ensure all target are above horizon before continuing')

    return parser.parse_known_args()


# -fin-
    
