from __future__ import absolute_import
from __future__ import print_function

import os
import unittest2 as unittest
from mock import patch

from astrokat import observe_main
from .testutils import yaml_path, LoggedTelescope

# - nd-pattern-sim
# - nd-pattern-ants
# - nd-pattern-cycle
# - nd-pattern-plus-off
# - nd-trigger

PROPOSAL_ID = "CAM_AstroKAT_UnitTest"
OBSERVER = "KAT Tester"


@patch('astrokat.observe_main.Telescope', LoggedTelescope)
class test_astrokat_yaml(unittest.TestCase):

    def test_nd_pattern_sim(self):
        yaml_file = yaml_path('test_nd/nd-pattern-sim.yaml')
        observe_main.main([
            "--yaml", yaml_file,
            "--observer", OBSERVER,
            "--proposal-id", PROPOSAL_ID,
            "--start-time", os.getenv("START_TIME", "2019-07-15 23:35:00"),
            "--sb-id-code", os.getenv("SB_ID_CODE"),
            "--dry-run",
        ])

        # TODO: restore this check after working out an appropriate start-time
        # in UTC with Ruby

        result = LoggedTelescope.user_logger_stream.getvalue()
        # self.assertIn('Single run through observation target list', result, 'Single run')
        # self.assertIn('azel observed for 300.0 sec',
        #               result, 'azel observed for 300.0 sec')
