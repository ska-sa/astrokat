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
        """Test of drift scan over an area in the sky."""
        execute_observe_main("test_scans/reverse-scan-test.yaml")
        # get result and make sure everything ran properly
        result = LoggedTelescope.user_logger_stream.getvalue()
        # Check that calibration tracks can be done
        self.assertIn("PictorA_r0.5", result)
        # Check that the scan has duration rounded off
        self.assertIn("Scan duration is 122.0", result)
        # Check that the scan has speed rounded off
        self.assertIn("scan speed is 0.13", result)
        # scan over section of sky truncated to the degree
        self.assertIn("-101:", result)
        self.assertIn("52:", result)
        # Scan extent =  -8.381748602251188 , 8.381748602251188
        # In the dry run and slight less in the simulate.
        self.assertIn("8.3", result)
