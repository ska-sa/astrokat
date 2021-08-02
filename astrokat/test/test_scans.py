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
        target_string = "Az: -172:57:37.1 El: 56:27:26.4"
        self.assert_started_target_track(target_string, 180.0, result)
        self.assert_completed_target_track(target_string, 180.0, result)

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

    def assert_started_target_track(self, target_string, duration, result):
        simulate_message = "Slewed to {} at azel".format(target_string)
        katcorelib_message = "Initiating {:g}-second track on target {!r}".format(
            duration, target_string)
        simulated_message_found = simulate_message in result
        katcorelib_message_found = katcorelib_message in result
        self.assertTrue(
            simulated_message_found or katcorelib_message_found,
            "Neither simulate {!r} nor katcorelib {!r} message found.".format(
                simulate_message, katcorelib_message)
        )

    def assert_completed_target_track(self, target_string, duration, result):
        simulate_message = "Tracked {} for {:g} seconds".format(target_string, duration)
        katcorelib_message = "target tracked for {:g} seconds".format(duration)
        simulated_message_found = simulate_message in result
        katcorelib_message_found = katcorelib_message in result
        self.assertTrue(
            simulated_message_found or katcorelib_message_found,
            "Neither simulate {!r} nor katcorelib {!r} message found.".format(
                simulate_message, katcorelib_message)
        )
