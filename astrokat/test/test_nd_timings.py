"""Tests Noise Diode timing."""
from __future__ import absolute_import
from __future__ import print_function

import re
import unittest

from mock import patch

from .testutils import LoggedTelescope, execute_observe_main


@patch("astrokat.observe_main.Telescope", LoggedTelescope)
class TestAstrokatYAML(unittest.TestCase):
    """Tests astrokat yaml."""

    def setUp(self):
        """Before each test is ran.

        the `user_logger_stream` (in-memory buffer) needs to be cleared.
        LoggedTelescope.reset_user_logger_stream()

        """

    def test_nd_pattern_sim(self):
        """Tests noisediode simulator."""
        execute_observe_main("test_nd/nd-pattern-sim.yaml")

        result = LoggedTelescope.user_logger_stream.getvalue()

        # extract requested timestamp to match against reported timestamp
        on_timestamp = '1573714805.0'  # default ts
        request_ref_str = 'Request: Set noise diode pattern to activate'
        for logmsg in result.split('\n'):
            if request_ref_str in logmsg:
                ts = re.compile(r'([0-9.]+) \(includes')  # has subgroup
                ts_result = ts.search(logmsg)  # match anywhere in the string
                on_timestamp = ts_result.group(1)

        self.assertIn(
            "Antennas found in subarray, setting ND: m011,m022,m033,m044",
            result
        )
        self.assertIn(
            "Repeat noise diode pattern every 16.0 sec, with 8.0 sec on",
            result
        )
        # evaluate ND on timestamp is requested timestamp
        report_ref_str = "Switch noise-diode pattern on at {}".format(on_timestamp)
        self.assertIn(report_ref_str, result)

    def test_nd_pattern_ants(self):
        """Tests noisediode simulator."""
        execute_observe_main("test_nd/nd-pattern-ants.yaml")

        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("(includes 2.0 sec lead time)", result)
        self.assertIn("setting ND: m011,m022", result)
        self.assertIn("apply pattern to ['m011', 'm022']", result)

    def test_nd_pattern_plus_off(self):
        """Tests noisediode simulator."""
        execute_observe_main("test_nd/nd-pattern-plus-off.yaml")

        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("No ND for target", result)
        self.assertIn("noise-diode off at 1573714914.0", result)
        self.assertIn("Restoring ND pattern", result)
        self.assertIn("noise diode pattern every 0.1 sec, with 0.05 sec on",
                      result)
        self.assertIn("noise-diode pattern on at 1573714803.0", result)

    def test_nd_trigger_long(self):
        """Tests noisediode simulator."""
        execute_observe_main("test_nd/nd-trigger-long.yaml")

        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Firing noise diode for 15.0s", result)
        self.assertIn("Add lead time of 5.0s", result)
        self.assertIn("noise-diode on at 1573714853.0", result)
        self.assertIn("noise-diode off at 1573714868.0", result)

    def test_nd_trigger_short(self):
        """Tests noisediode simulator."""
        execute_observe_main("test_nd/nd-trigger-short.yaml")

        result = LoggedTelescope.user_logger_stream.getvalue()
        self.assertIn("Firing noise diode for 2.0s", result)
        self.assertIn("Add lead time of 5.0s", result)
        self.assertIn("Set noise diode pattern", result)
        self.assertIn("noise-diode pattern on at 1573714853.0", result)
        self.assertIn("noise-diode off at 1573714858.0", result)
