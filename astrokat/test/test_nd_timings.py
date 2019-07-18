from __future__ import print_function

import logging
import os
import sys

import unittest2 as unittest
from astrokat import observe_main, simulate

if sys.version_info[0] == 3:
    from io import StringIO
else:
    from StringIO import StringIO


# - nd-pattern-sim
# - nd-pattern-ants
# - nd-pattern-cycle
# - nd-pattern-plus-off
# - nd-trigger

PROPOSAL_ID = "CAM_AstroKAT_UnitTest"
OBSERVER = "KAT Tester"

TESTS_PATH = os.path.abspath(os.path.dirname(__file__))


class test_astrokat_yaml(unittest.TestCase):
    def setUp(self):
        user_logger = logging.getLogger("astrokat.simulate")

        # remove current handlers
        for handler in user_logger.handlers:
            user_logger.removeHandler(handler)

        self.string_stream = StringIO()
        out_hdlr = logging.StreamHandler(self.string_stream)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        formatter.formatTime = simulate.sim_time
        out_hdlr.setFormatter(formatter)
        out_hdlr.setLevel(logging.TRACE)
        user_logger.addHandler(out_hdlr)
        user_logger.setLevel(logging.INFO)

    def yaml_path(self, file_path):
        yaml_file = os.path.abspath(os.path.join(TESTS_PATH, file_path))
        self.assertTrue(os.path.isfile(yaml_file))
        return yaml_file

    def test_nd_pattern_sim(self):
        yaml_file = self.yaml_path('test_nd/nd-pattern-sim.yaml')
        observe_main.main([
            "--yaml", yaml_file,
            "--observer", OBSERVER,
            "--proposal-id", PROPOSAL_ID,
            "--start-time", os.getenv("START_TIME", "2019-07-15 23:35:00"),
            "--sb-id-code", os.getenv("SB_ID_CODE", "20190718-0001"),
            "--dry-run",
        ])

        # TODO: restore this check after working out an appropriate start-time
        # in UTC with Ruby

        result = self.string_stream.getvalue()
        # self.assertIn('Single run through observation target list', result, 'Single run')
        # self.assertIn('azel observed for 300.0 sec',
        #               result, 'azel observed for 300.0 sec')
