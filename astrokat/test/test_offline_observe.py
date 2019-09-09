"""Test astrokat observe.py script in a simulated environment."""
from __future__ import absolute_import
from __future__ import print_function

import unittest2 as unittest
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

    def test_targets_sim(self):
        """Test targets sim."""
        execute_observe_main("test_obs/targets-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Single run through observation target list", result)
        self.assertIn("target0_radec observed for 10.0 sec", result)
        self.assertIn("target1_azel observed for 10.0 sec", result)
        self.assertIn("target2_gal observed for 10.0 sec", result)

    def test_two_calib_sim(self):
        """Tests two calibrators sim."""
        execute_observe_main("test_obs/two-calib-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Single run through observation target list", result)
        self.assertIn("BP calibrators are ['1934-638', '0408-65']", result,
                      "two Bandpass calibrators")

        cal1 = result.count("0408-65 observed for 30.0 sec")
        cal2 = result.count("1934-638 observed for 30.0 sec")

        self.assertGreaterEqual(cal1 + cal2, 1, "At least one bpcal was observed")
        self.assertLessEqual(cal1 + cal2, 2, "At most 2 bpcals were observed")

    def test_drift_targets_sim(self):
        """Test drift scan sim."""
        execute_observe_main("test_obs/drift-targets-sim.yaml")

        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Single run through observation target list", result, "Single run")
        self.assertIn("0408-65 observed for 180.0 sec", result)
        self.assertIn("1934-638 observed for 180.0 sec", result)
        self.assertEqual(result.count("Drift_scan observation for"), 2, "two drift scans")

    # TODO: not sure how raster scan works. Will work out correct test with Ruby
    # def test_raster_scans_sim(self):
    #     observe_main.main(["--yaml",
    #                        "astrokat/test/test_obs/{}.yaml".format("raster-scans-sim")])
    #
    #     # get result and make sure everything ran properly
    #     result = LoggedTelescope.user_logger_stream.getvalue()
    #     self.assertIn("Single run through observation target list",
    #     result, "Single run") self.assertIn("0408-65 observed", result,
    #     "0408-65 observed") self.assertIn("1934-638 observed", result,
    #     "1934-638 observed") self.assertEqual(result.count(
    #     "Drift_scan observation for"), 2, "two drift scans")

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

        self.assertIn("BP calibrators are ['1934-638', '3C286']", result,
                      "two bandpass calibrators")
        self.assertIn("GAIN calibrators are ['1827-360']", result, "one gain calibrator")
        self.assertIn("POL calibrators are ['3C286']", result, "one pol calibrator")
        self.assertIn(
            "DELAY calibrators are ['1934-638']", result, "one delay calibrator")

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
            result, "observation time lapsed",
        )

        expected_results = (
            "Observation targets are ['T3R04C06', 'T4R00C02', 'T4R00C04', 'T4R00C06', "
            "'T4R01C01', 'T4R01C03', 'T4R01C05', 'T4R02C02', 'T4R02C04']"
        )
        self.assertIn(expected_results, result, "Nine imaging targets")

        self.assertIn("GAIN calibrators are ['1827-360']", result, "one gain calibrator")
        self.assertIn("BP calibrators are ['1934-638', '3C286']", result,
                      "two BP calibrator")
        self.assertIn(
            "DELAY calibrators are ['1934-638']", result, "one dealy calibrator")
        self.assertIn("POL calibrators are ['3C286']", result, "one pol calibrator")
        self.assertIn("1827-360 observed for 30.0 sec", result)
        self.assertIn("1934-638 observed for 120.0 sec", result)
        self.assertIn("3C286 observed for 80.0 sec", result)
        self.assertIn("T3R04C06 observed for 360.0 sec", result)
        self.assertIn("T4R00C02 observed for 360.0 sec", result)
        self.assertIn("T4R00C04 observed for 360.0 sec", result)
        self.assertIn("T4R00C06 observed for 360.0 sec", result)
        self.assertIn("T4R01C01 observed for 360.0 sec", result)
        self.assertIn("T4R01C03 observed for 360.0 sec", result)
        self.assertIn("T4R01C05 observed for 360.0 sec", result)
        # do no need to super acurate with this target to allow
        # for slew time discrepancies
        self.assertIn("T4R02C02 observed", result)
        self.assertIn("T4R02C04 observed for 180.0 sec", result)
