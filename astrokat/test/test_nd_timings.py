"""Tests Noise Diode timing."""
from __future__ import absolute_import
from __future__ import print_function

import unittest2 as unittest
from mock import patch

from .testutils import LoggedTelescope, execute_observe_main

# - nd-pattern-sim
# - nd-pattern-ants
# - nd-pattern-cycle
# - nd-pattern-plus-off
# - nd-trigger


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

        # TODO: restore this check after working out an appropriate start-time
        # in UTC with Ruby

        result = LoggedTelescope.user_logger_stream.getvalue()
        # self.assertIn('Single run through observation target list',
        # result, 'Single run')
        # self.assertIn('azel observed for 300.0 sec',
        #               result, 'azel observed for 300.0 sec')
