"""Initialize astrokat."""
from __future__ import division
from __future__ import absolute_import

# Constants and defaults
_DEFAULT_LEAD_TIME = 5.0  # lead time [sec]
def max_cycle_len(band):
    if band.lower() == 'u':
        return 31.  # buffer len [sec]
    else:
        # default is L-band
        return 20.  # buffer len [sec]
# Constants and defaults

from .__main__ import cli

from . import noisediode
from . import correlator
from . import scans

from .simulate import user_logger, verify_and_connect, start_session
from .utility import (
    NoTargetsUpError,
    NotAllTargetsUpError,
    read_yaml,
    katpoint_target,
    get_lst,
    lst2utc,
    datetime2timestamp,
    timestamp2datetime,
)
from .observatory import Observatory, collect_targets


# BEGIN VERSION CHECK
# Get package version when locally imported from repo or via -e develop install
try:
    import katversion as _katversion
except ImportError:
    import time as _time

    __version__ = "0.0+unknown.{}".format(_time.strftime("%Y%m%d%H%M"))
else:
    __version__ = _katversion.get_version(__path__[0])
# END VERSION CHECK

# -fin-
