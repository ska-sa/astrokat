"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

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
        self.assertIn("scan_1934-638 observed for 30.0 sec", result)

    def test_reference_pointing_scan_basic_sim(self):
        """Not much to do: check scan initiate log msg"""
        execute_observe_main("test_scans/reference-pointing-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Initialising Reference_pointing_scan pointingcal 1934-638 for 120.0 sec", result)
        self.assertIn("1934-638 observed for 0.0 sec", result)

    def test_get_scan_area_extents_for_setting_target(self):
        """Test of function get_scan_area_extents with setting target."""
        test_date = katpoint.Timestamp('2010/12/05 02:00:00').to_ephem_date()
        el, az_min, az_max, t_start, t_end = self.get_scan_area_extents(test_date)
        self.assertAlmostEqual(el, 0.82988305)  # In radians
        self.assertAlmostEqual(az_min, 3.67187738)  # In radians
        self.assertAlmostEqual(az_max, 4.015025139)  # In radians
        self.assertEqual(int(t_start.secs), 1291514447)
        self.assertEqual(int(t_end.secs), 1291522147)

    def test_get_scan_area_extents_for_rising_target(self):
        """Test of function get_scan_area_extents with rising target."""
        test_date = katpoint.Timestamp('2010/12/05 20:00:00').to_ephem_date()
        el, az_min, az_max, t_start, t_end = self.get_scan_area_extents(test_date)
        self.assertAlmostEqual(el, 0.39849024)  # In radians
        self.assertAlmostEqual(az_min, 2.06043911)  # In radians
        self.assertAlmostEqual(az_max, 2.25462604)  # In radians
        self.assertEqual(int(t_start.secs), 1291579227)
        self.assertEqual(int(t_end.secs), 1291585208)

    def get_scan_area_extents(self, test_date):
        # Test Antenna: 0-m dish at lat 0:00:00.0, long 0:00:00.0, alt 0.0 m
        antenna = katpoint.Antenna("Test Antenna", 0, 0, 0)
        target_list = [
            katpoint.Target("t1, radec, 05:16:00.0, -25:42:00.0", antenna=antenna),
            katpoint.Target("t2, radec, 05:16:00.0, -35:36:00.0", antenna=antenna),
            katpoint.Target("t3, radec, 06:44:00.0, -35:36:00.0", antenna=antenna),
            katpoint.Target("t4, radec, 06:44:00.0, -25:42:00.0", antenna=antenna),
        ]
        el, az_min, az_max, t_start, t_end = scans._get_scan_area_extents(target_list,
                                                                          antenna,
                                                                          test_date)
        return el, az_min, az_max, t_start, t_end

    def test_reverse_scan_basic_sim(self):
        """Test of reverse scan over an area in the sky."""
        execute_observe_main("test_scans/reverse-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        # Check that calibration tracks can be done
        self.assertIn("PictorA_r0.5", result)
        # Check scan details
        self.assertIn("scan speed is 0.13 deg/s", result)
        self.assertIn("Azimuth scan extent [-6.1, 6.1]", result)
        self.assertIn("Scan completed - 49 scan lines", result)
        self.assertEqual(result.count('Scan target: scan_azel_with_nd_trigger,'), 99)

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
