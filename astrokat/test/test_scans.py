"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

import unittest

from mock import patch

from .testutils import LoggedTelescope, execute_observe_main


@patch("astrokat.observe_main.Telescope", LoggedTelescope)
class TestAstrokatYAML(unittest.TestCase):
    """Tests astrokat yaml."""

    def setUp(self):
        """Before each test is ran.

        The `user_logger_stream` (in-memory buffer) needs to be cleared.
        LoggedTelescope.reset_user_logger_stream()

        """
        LoggedTelescope.reset_user_logger_stream()

    def test_drift_scan_basic_sim(self):
        """Check (az, el) target from (ra, dec) for drift scan"""
        execute_observe_main("test_scans/drift-scan-sim-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Initialising Drift_scan target 1934-638 for 180.0 sec", result)
        self.assertIn("Drift_scan observation for 180.0 sec", result)
        self.assertIn("Slewed to Az: -172:57:37.1 El: 56:27:26.4 at azel "
                      "(-173.0, 56.5) deg",
                      result)
        self.assertIn("Tracked Az: -172:57:37.1 El: 56:27:26.4 for 180 seconds", result)

    def test_raster_scan_basic_sim(self):
        """Not much to do: check scan initiate log msg"""
        execute_observe_main("test_scans/raster-scan-sim-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Initialising Raster_scan target raster_1934-638 for 90.0 sec",
                      result)

    def test_scan_basic_sim(self):
        """Not much to do: check scan initiate log msg"""
        execute_observe_main("test_scans/scan-sim-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Initialising Scan target scan_1934-638 for 30.0 sec", result)
        self.assertIn("scan_1934-638 observed for 60.0 sec", result)
