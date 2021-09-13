"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

import unittest
import katpoint

from mock import patch

from astrokat import utility
from .testutils import (
    LoggedTelescope,
    execute_observe_main,
    extract_start_time,
    yaml_path,
)


@patch("astrokat.observe_main.Telescope", LoggedTelescope)
class TestAstrokatYAML(unittest.TestCase):
    """Tests astrokat yaml."""

    def setUp(self):
        """Before each test is ran.

        The `user_logger_stream` (in-memory buffer) needs to be cleared.
        LoggedTelescope.reset_user_logger_stream()

        """
        LoggedTelescope.reset_user_logger_stream()

    def test_targets_sim(self):
        """Test targets sim."""
        execute_observe_main("test_obs/targets-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("target4_azel, tags=radec target", result)
        self.assertIn("Single run through observation target list", result)
        self.assertIn("Moon observed for 10.0 sec", result)
        self.assertIn("target0_radec observed for 10.0 sec", result)
        self.assertIn("target1_radec observed for 10.0 sec", result)
        self.assertIn("target2_gal observed for 10.0 sec", result)
        self.assertIn("target3_azel observed for 10.0 sec", result)
        self.assertIn("target4_azel observed for 10.0 sec", result)

    def test_two_calib_sim(self):
        """Tests two calibrators sim."""
        execute_observe_main("test_obs/two-calib-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Single run through observation target list", result)
        self.assertIn(
            "BP calibrators are ['1934-638', '0408-65']",
            result,
            "two Bandpass calibrators",
        )

        cal1 = result.count("0408-65 observed for 30.0 sec")
        cal2 = result.count("1934-638 observed for 30.0 sec")

        self.assertGreaterEqual(cal1 + cal2, 1, "At least one bpcal was observed")
        self.assertLessEqual(cal1 + cal2, 2, "At most 2 bpcals were observed")

    def test_image_single_sim(self):
        """Test image single sim."""
        execute_observe_main("test_obs/image-single-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Single run through observation target list", result)
        expected_results = (
            "Observation targets are ['T3R04C06', 'T4R00C02', 'T4R00C04', 'T4R00C06', "
            "'T4R01C01', 'T4R01C03', 'T4R01C05', 'T4R02C02', 'T4R02C04']"
        )
        self.assertIn(expected_results, result, "Nine imaging targets")

        self.assertIn(
            "BP calibrators are ['1934-638', '3C286']",
            result,
            "two bandpass calibrators",
        )
        self.assertIn(
            "GAIN calibrators are ['1827-360']", result, "one gain calibrator"
        )
        self.assertIn("POL calibrators are ['3C286']", result, "one pol calibrator")
        self.assertIn(
            "DELAY calibrators are ['1934-638']", result, "one delay calibrator"
        )

        self.assertIn("1827-360 observed for 30.0 sec", result)
        self.assertIn("1934-638 observed for 120.0 sec", result)
        self.assertIn("3C286 observed for 40.0 sec", result)
        self.assertIn("T3R04C06 observed for 180.0 sec", result)
        self.assertIn("T4R00C02 observed for 180.0 sec", result)
        self.assertIn("T4R00C04 observed for 180.0 sec", result)
        self.assertIn("T4R00C06 observed for 180.0 sec", result)
        self.assertIn("T4R01C01 observed for 180.0 sec", result)
        self.assertIn("T4R01C03 observed for 180.0 sec", result)
        self.assertIn("T4R01C05 observed for 180.0 sec", result)
        self.assertIn("T4R02C02 observed for 180.0 sec", result)
        self.assertIn("T4R02C04 observed for 180.0 sec", result)

    def test_image_sim(self):
        """Test image sim."""
        execute_observe_main("test_obs/image-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn(
            "Scheduled observation time lapsed - ending observation",
            result,
            "observation time lapsed",
        )

        expected_results = (
            "Observation targets are ['T3R04C06', 'T4R00C02', 'T4R00C04', 'T4R00C06', "
            "'T4R01C01', 'T4R01C03', 'T4R01C05', 'T4R02C02', 'T4R02C04']"
        )
        self.assertIn(expected_results, result, "Nine imaging targets")

        self.assertIn(
            "GAIN calibrators are ['1827-360']", result, "one gain calibrator"
        )
        self.assertIn(
            "BP calibrators are ['1934-638', '3C286']", result, "two BP calibrator"
        )
        self.assertIn(
            "DELAY calibrators are ['1934-638']", result, "one dealy calibrator"
        )
        self.assertIn("POL calibrators are ['3C286']", result, "one pol calibrator")
        self.assertIn("1827-360 observed for 30.0 sec", result)
        self.assertIn("1934-638 observed for 180.0 sec", result)
        self.assertIn("3C286 observed for 80.0 sec", result)
        self.assertIn("T3R04C06 observed for 360.0 sec", result)
        self.assertIn("T4R00C02 observed for 360.0 sec", result)
        self.assertIn("T4R00C04 observed for 360.0 sec", result)
        self.assertIn("T4R00C06 observed for 360.0 sec", result)
        self.assertIn("T4R01C01 observed for 360.0 sec", result)
        self.assertIn("T4R01C03 observed for 360.0 sec", result)
        self.assertIn("T4R01C05 observed for 360.0 sec", result)
        # do no need to be super accurate with this target to allow
        # for slew time discrepancies
        self.assertIn("T4R02C02 observed", result)
        self.assertIn("T4R02C04 observed for 360.0 sec", result)

    def test_solar_body(self):
        """Special target observation of solar system body"""
        execute_observe_main("test_obs/solar-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()

        self.assertIn("Observation targets are ['Jupiter', 'Moon']", result)
        self.assertIn("Jupiter observed for 60.0 sec", result)
        self.assertIn("Moon observed for 40.0 sec", result)

    def test_below_horizon(self):
        """Below horizon test."""
        execute_observe_main("test_obs/below-horizon-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn(
            "Observation list completed - ending observation",
            result,
            "Observation list completed",
        )

        expected_results = 'J1733-1304 observed for 600.0 sec'
        self.assertIn(expected_results, result, "J1733-1304 observed for 600.0 sec")

        # MAXIJ1810-22 started off above horizon, but at end of the duration,
        # it would be below horizon
        expected_results = 'Target MAXIJ1810-22 below 20.0 deg horizon, continuing'
        self.assertIn(
            expected_results, result, "MAXIJ1810-22 skipped"
        )

        # J1833-2103 with cadence started off above horizon, but at end of the duration,
        # it would be below horizon
        expected_results = 'Target J1833-2103 below 20.0 deg horizon, continuing'
        self.assertIn(
            expected_results, result, "J1833-2103 skipped"
        )

    def test_time_conversion_symmetry(self):
        """Test katpoint and astrokat time conversion methods match and are symmetrical"""
        test_files = [
            "test_obs/below-horizon-sim.yaml",
            "test_obs/image-cals-sim.yaml",
            "test_obs/image-sim.yaml",
            "test_obs/image-single-sim.yaml",
            "test_obs/targets-sim.yaml",
            "test_obs/two-calib-sim.yaml",
        ]
        for test_file in test_files:
            file_path = yaml_path(test_file)
            yaml_start_time = extract_start_time(file_path)
            yaml_start_time_str = str(yaml_start_time)

            astrokat_sec_since_epoch = utility.datetime2timestamp(yaml_start_time)
            katpoint_sec_since_epoch = katpoint.Timestamp(yaml_start_time_str).secs
            self.assertAlmostEqual(
                astrokat_sec_since_epoch,
                katpoint_sec_since_epoch,
                places=6,
                msg="timestamp conversion mismatch {}".format(test_file)
            )

            astrokat_datetime = utility.timestamp2datetime(astrokat_sec_since_epoch)
            katpoint_timestamp = katpoint.Timestamp(katpoint_sec_since_epoch)
            self.assertEqual(
                str(astrokat_datetime),
                yaml_start_time_str,
                msg="astrokat str time conversion mismatch for {}".format(test_file)
            )
            self.assertEqual(
                str(katpoint_timestamp),
                yaml_start_time_str,
                msg="katpoint str time conversion mismatch for {}".format(test_file)
            )
