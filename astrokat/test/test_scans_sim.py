"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

import os
import unittest

import katpoint

from mock import patch

from astrokat import scans
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

        # use running session to determine suitable target values
        if os.getenv("SESSION_TYPE") == "mkat_session":
            target_string = "Az: -159:01:46.8 El: 52:05:00.6"
        else:
            target_string = "Az: -158:55:32.5 El: 52:01:18.0"

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

    def test_reference_pointing_scan_basic_sim(self):
        """Not much to do: check scan initiate log msg"""
        execute_observe_main("test_scans/reference-pointing-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Initialising Reference_pointing_scan pointingcal "
                      "1934-638 for 144.0 sec", result)
        self.assertIn("1934-638 observed for 288.0 sec", result)
        self.assertIn("Adjust pointing selected", result)

    def test_reverse_scan_basic_sim(self):
        """Test of reverse scan over an area in the sky."""
        execute_observe_main("test_scans/reverse-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        # Check that calibration tracks can be done
        self.assertIn("PictorA_r0.5", result)
        # Check scan details
        self.assertIn("scan speed is 0.14 degrees per second", result)
        self.assertIn("Azimuth scan extent [-8.3, 8.3]", result)
        self.assertIn("Scan completed - 48 scan lines", result)
        # Check the an radec target is fixed and been scanned across
        self.assertEqual(result.count('Scan target: scan_azel_with_nd_trigger,'), 48)
        self.assertEqual(result.count('Scanning across CBF target : '), 48)
