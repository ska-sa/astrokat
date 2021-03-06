"""Add standard observation script options from sessions."""
import argparse
import astrokat


live_system = True
try:
    from katcorelib.observe import standard_script_options
except ImportError:
    live_system = False
    pass


# Add standard observation script options from sessions
def session_options(parser, short_opts_to_remove=[], long_opts_to_remove=[]):
    """Add options from katcorelib that are valid for all observations.

    Parameters
    ----------
    parser: `optparse.OptionParser`
        Parser populated with standard script options
    short_opts_to_remove: list
        Previous short observation command line options to discard
    long_opts_to_remove: list
        Previous long observation command line options to discard

    Returns
    -------
    parser: `optparse.OptionParser`
        Parser populated with standard script options

    """
    dryrun = False
    group = parser.add_argument_group(
        title="Standard MeerKAT options",
        description="Default observation script options",
    )
    if live_system:
        parser_ = standard_script_options("", "")
        # fudge parser_ class from OptionParser to Group
        for opt in parser_.option_list:
            # Disregarding options we don't want in the group
            long_ = opt.__dict__["_long_opts"][0]
            if "dry-run" in long_:
                dryrun = True
                continue
            if long_ in long_opts_to_remove:
                continue
            args = opt.__dict__["_long_opts"]
            if opt.__dict__["_short_opts"]:
                short = opt.__dict__["_short_opts"][0]
                if short in short_opts_to_remove:
                    continue
                args = opt.__dict__["_short_opts"] + args

            kwargs = {
                "dest": opt.__dict__["dest"],
                "type": type(opt.__dict__["default"])
                if not isinstance(opt.__dict__["default"], tuple)
                else None,
                "default": opt.__dict__["default"]
                if not isinstance(opt.__dict__["default"], tuple)
                else None,
                "nargs": opt.__dict__["nargs"] if opt.__dict__["nargs"] != 1 else None,
                "metavar": opt.__dict__["metavar"]
                if not opt.__dict__["choices"]
                else "",
                "choices": opt.__dict__["choices"],
                "action": opt.__dict__["action"]
                if opt.__dict__["action"] != "store_true"
                else None,
                "const": opt.__dict__["const"]
                if opt.__dict__["action"] == "store_const"
                else None,
                "help": opt.__dict__["help"].replace("%default", "%(default)s")
                if long_ != "--quorum"
                else opt.__dict__["help"].replace("%", "%%"),
                "required": True if "**required**" in opt.__dict__["help"] else False,
            }

            group.add_argument(*args, **kwargs)

    # something goes wrong in this conversion for opts to args
    # adding this manually
    if dryrun:
        group.add_argument("--dry-run", action="store_true")
    return parser


def cli(
    prog,
    parser=None,
    short_opts_to_remove=["-h"],
    long_opts_to_remove=["--version"],
    args=None,
):
    """Specify initial implementation of observation input parameter using json.

    Parameters
    ----------

    parser: `optparse.OptionParser`
        Parser populated with standard script options
    short_opts_to_remove: list
        Previous short observation command line options to discard
    long_opts_to_remove: list
        Previous long observation command line options to discard

    Returns
    -------
    parser: `optparse.OptionParser`
        Parser populated with standard script options

    """
    if parser is None:
        # Set up standard script options
        # TODO: more complex usage string in separate function
        usage = "%s [options]  --yaml <YAMLfile>" % prog
        description = """"Sources are specified either as part of an observation profile.
                          Track one or more sources for a specified time.
                          At least one target must be specified.
                          Also note the **required** options."""
        parser = argparse.ArgumentParser(
            usage=usage,
            description=description,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )

    # Standard track experiment options
    parser.add_argument("--version", action="version", version=astrokat.__version__)
    parser.add_argument(
        "--yaml",
        type=str,
        required=True,
        help="Observation file, obs_plan.yaml (**required**)",
    )

    # Add standard observation script options from sessions
    parser = session_options(
        parser,
        short_opts_to_remove=short_opts_to_remove,
        long_opts_to_remove=long_opts_to_remove,
    )

    # Observation simulation for planning using observation script
    title = "Observation planning and verifications"
    description = "Basic output of observation to verify expected outcome"
    group = parser.add_argument_group(title=title, description=description)
    ex_group = group.add_mutually_exclusive_group()
    ex_group.add_argument(
        "--visibility",
        action="store_true",
        help="Display short summary of target visibility",
    )
    ex_group.add_argument(
        "--all-up",
        action="store_true",
        help="Ensure all target horizon before continuing",
    )
    group.add_argument(
        "--debug", action="store_true", help="verbose logger output for debugging"
    )
    group.add_argument(
        "--trace", action="store_true", help="Debug trace logger output for debugging"
    )

    return parser.parse_known_args(args=args)


if __name__ == "__main__":
    import sys

    cli(sys.argv[0])

# -fin-
