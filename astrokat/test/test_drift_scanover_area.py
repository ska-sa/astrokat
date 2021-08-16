"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

import unittest


import katpoint
from astrokat import scans
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

    def test_get_scan_area_extents(self):
        """Test of function get_scan_area_extents."""
        # Test Antenna: 0-m dish at lat 0:00:00.0, long 0:00:00.0, alt 0.0 m
        antenna = katpoint.Antenna("Test Antenna", 0, 0, 0)
        test_date = katpoint.Timestamp('2010/12/05 02:00:00').to_ephem_date()
        antenna.observer.date = test_date
        test_targets = [
            "05:16:00.0000, -25:42:00.0000",
            "05:16:00.0000, -35:36:00.0000",
            "06:44:00.0000, -35:36:00.0000",
            "06:44:00.0000, -25:42:00.0000",
        ]
        target_list = []
        for i, target in enumerate(test_targets):
            target_list.append(
                katpoint.Target(
                    't%i,radec,%s' % (i, target),
                    antenna=antenna,
                )
            )
        el, az_min, az_max, t_start, t_end = scans._get_scan_area_extents(target_list,
                                                                          antenna,
                                                                          test_date,)
        self.assertAlmostEqual(el, 0.8298830529539688)  # In radians
        self.assertAlmostEqual(az_min, 3.671877384185791)  # In radians
        self.assertAlmostEqual(az_max, 4.0150251388549805)  # In radians
        self.assertEqual(int(t_start.secs), 1291514447)
        self.assertEqual(int(t_end.secs), 1291522147)

    def test_drift_scan_basic_sim(self):
        """Test of drift scan over an area in the sky."""
        execute_observe_main("test_scans/reverse-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        # Check that calibration tracks can be done
        self.assertIn("PictorA_r0.5", result)
        # Make surethere are 48 scans
        self.assertEqual(result.count('Scan target: scan_azel_with_nd_trigger,'), 48)
        # Check that the scan has speed rounded off
        self.assertIn("scan speed is 0.13", result)
        # In the dry run and slight less in the simulate.
        self.assertIn("8.3", result)
