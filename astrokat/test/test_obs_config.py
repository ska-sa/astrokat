"""Test astrokat dictionary construction for observation file."""
from __future__ import absolute_import
from __future__ import print_function

import argparse
import unittest
from astrokat import obs_dict, obs_yaml

target_list = [
'name=J1939-6342 | 1934-638, radec=19:39:25.05 -63:42:43.6, tags=bpcal fluxcal, duration=180.0, cadence=1800.0, model=(408.0 8640.0 -30.77 26.49 -7.098 0.6053)',
'name=3C138, radec=05:21:09.90 +16:38:22.1, tags=bpcal, duration=180.0, cadence=1800.0',
'name=J0155-4048 | 0153-410, radec=1:55:37.06 -40:48:42.4, tags=gaincal, duration=65.0',
'name=NGC641_02D02, radec=1:39:25.01 -42:14:49.2, tags=target, duration=300.0',
'name=Moon, special=special',
]

class TestAstrokatDict(unittest.TestCase):
    """Test astrokat dict definitions"""

    def setUp(self):
        """Before each test is ran"""
        pass

    # if instrument dict is given, check against base instrument dict defined
    def test_instrument_dict(self):
        args = argparse.Namespace()
        args.product = 'c856M4k'
        args.band = 'l'
        args.integration_period = '8'
        instrument = vars(args) 
        for key in instrument.keys():
            self.assertIn(key, obs_dict.instrument_.keys())

    # if durations dict is given, check against base durations dict defined
    def test_durations_dict(self):
        args = argparse.Namespace()
        args.obs_duration = '35400'
        args.start_time = '2019-02-11 02:10:47'
        durations = vars(args)
        for key in durations.keys():
            self.assertIn(key, obs_dict.durations_.keys())

    # if targets are given, see if you can unpack them
    def test_target_str(self):
        for target in target_list:
            target_dict = obs_dict.unpack_target(target)
            for key in target_dict.keys():
                self.assertIn(key, obs_dict.target_.keys())

# -fin-
