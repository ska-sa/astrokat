import argparse
live_system = True
try:
    from katcorelib.observe import (standard_script_options)
except ImportError:
    live_system = False
    pass


# Add standard observation script options from sessions
def session_options(parser,
                    x_short_opts=[],
                    x_long_opts=[]):
    # Add options from katcorelib that is valid for all observations
    group = parser.add_argument_group(
        title="\
standard MeerKAT options",
        description="\
default observation script options")
    if live_system:
        parser_ = standard_script_options('', '')
        # fudge parser_ class from OptionParser to Group
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

            kwargs = {'dest':
                      opt.__dict__['dest'],
                      'type':
                      type(opt.__dict__['default'])
                      if type(opt.__dict__['default']) != tuple else None,
                      'default':
                      opt.__dict__['default']
                      if type(opt.__dict__['default']) != tuple else None,
                      'nargs':
                      opt.__dict__['nargs']
                      if opt.__dict__['nargs'] != 1 else None,
                      'metavar':
                      opt.__dict__['metavar']
                      if not opt.__dict__['choices'] else '',
                      'choices':
                      opt.__dict__['choices'],
                      'action':
                      opt.__dict__['action']
                      if opt.__dict__['action'] != 'store_true' else None,
                      'const':
                      opt.__dict__['const']
                      if opt.__dict__['action'] == 'store_const' else None,
                      'help':
                      opt.__dict__['help'].replace("%default", "%(default)s")
                      if long_ != '--quorum' else opt.__dict__['help'].replace("%", "%%"),
                      'required':
                      True
                      if '**required**' in opt.__dict__['help'] else False,
                      }

            group.add_argument(*args, **kwargs)
    else:
        group.add_argument('-o',
                           '--observer',
                           required=True,
                           type=str,
                           help='\
name of person responsible for the observation (**required**)')
        group.add_argument('--horizon',
                           type=float,
                           default=20,
                           help='\
lowest elevation limit in degrees')
    return parser


def cli(prog,
        parser=None,
        x_short_opts=['-h'],
        x_long_opts=['--version'],
        args=None):

    if parser is None:
        # Set up standard script options
        version = "%s 0.1" % prog
        # TODO: more complex usage string in separate function
        usage = "%s [options] -o <observer>" \
                " --yaml <YAMLfile>" \
                " [<'YAMLfile'> ...]" % prog
        description = \
            "Sources are specified either as part of an observation profile." \
            " Track one or more sources for a specified time." \
            " At least one target must be specified." \
            " Also note the **required** options."
        parser = argparse.ArgumentParser(usage=usage,
                                         description=description,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         )

    # Standard track experiment options
    parser.add_argument('--version',
                        action='version', version=version)
    parser.add_argument('--yaml',
                        default=[],
                        type=str,
                        required=True,
                        help='\
observation planning file, obs_plan.yaml (**required**)')

    # Add standard observation script options from sessions
    parser = session_options(parser,
                             x_short_opts=x_short_opts,
                             x_long_opts=x_long_opts,
                             )

    # Observation simulation for planning using observation script
    title = "\
observation planning and verifications"
    description = "\
basic output of observation to verify expected outcome"
    group = parser.add_argument_group(title=title,
                                      description=description)
    ex_group = group.add_mutually_exclusive_group()
    ex_group.add_argument('--visibility',
                          action='store_true',
                          help='\
display short summary of target visibility')
    ex_group.add_argument('--all-up',
                          action='store_true',
                          help='\
ensure all target are above horizon before continuing')
    group.add_argument('--debug',
                       action='store_true',
                       help='\
verbose logger output for debugging')
    group.add_argument('--trace',
                       action='store_true',
                       help='\
debug trace logger output for debugging')

    return parser.parse_known_args(args=args)


if __name__ == '__main__':
    import sys
    cli(sys.argv[0])

# -fin-
