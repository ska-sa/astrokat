"""Test astrokat simulation."""
from __future__ import absolute_import
from __future__ import print_function

import unittest

from collections import namedtuple
from datetime import datetime

import ephem
import katpoint
import mock

from astrokat import simulate, observatory


class TestSimSession(unittest.TestCase):
    def setUp(self):
        start_time = datetime.strptime("2018-12-07 05:00:00", "%Y-%m-%d %H:%M:%S")
        observer = ephem.Observer()
        observer.date = ephem.Date(start_time)
        simulate.setobserver(observer)
        self.antenna = katpoint.Antenna(observatory._ref_location)
        self.mock_kat = mock.Mock()
        self.mock_kat.obs_params = {"durations": {"start_time": start_time}}
        self.DUT = simulate.SimSession(self.mock_kat)

    def azel_target(self, az, el):
        return katpoint.Target("test, azel, {}, {}".format(az, el), antenna=self.antenna)

    def test__fake_slew_first_target_takes_default_time(self):
        target = self.azel_target(32.0, 64.0)
        slew_time, _, _ = self.DUT._fake_slew_(target)
        self.assertAlmostEqual(slew_time, simulate._DEFAULT_SLEW_TIME_SEC)

    def test__fake_slew_same_target_takes_zero_time(self):
        target = self.azel_target(32.0, 64.0)
        self.DUT._fake_slew_(target)
        slew_time, _, _ = self.DUT._fake_slew_(target)
        self.assertAlmostEqual(slew_time, 0.0)

    def test__fake_slew_new_target_takes_slew_time(self):
        target1 = self.azel_target(32.0, 64.0)
        target2 = self.azel_target(48.0, 80.0)
        self.DUT._fake_slew_(target1)
        expected_slew_time = self.DUT._slew_time(48, 80)
        slew_time, _, _ = self.DUT._fake_slew_(target2)
        self.assertAlmostEqual(slew_time, expected_slew_time)

    def test__fake_slew_azel_returns_correct_az_el(self):
        target = self.azel_target(32.0, 64.0)
        _, az, el = self.DUT._fake_slew_(target)
        self.assertAlmostEqual(az, 32.0)
        self.assertAlmostEqual(el, 64.0)

    def test__slew_time(self):
        # test data generated from reference implementation in radec2azel.py
        # script - see JIRA MT-1206
        Data = namedtuple("Data", "az1 el1 az2 el2 slew_time")
        tests = [
            Data(az1=0.0, el1=40.0, az2=0.0, el2=40.0, slew_time=2.3),  # same target
            Data(az1=0.0, el1=40.0, az2=0.5, el2=40.0, slew_time=4.3),  # tiny az slew
            Data(az1=0.0, el1=40.0, az2=5.0, el2=40.0, slew_time=12.9),  # medium az slew
            Data(az1=0.0, el1=40.0, az2=20.0, el2=40.0, slew_time=20.4),  # long +az slew
            Data(az1=0.0, el1=40.0, az2=-20.0, el2=40.0, slew_time=20.4),  # long -az slew
            Data(az1=0.0, el1=40.0, az2=0.0, el2=40.5, slew_time=5.13),  # tiny el slew
            Data(az1=0.0, el1=40.0, az2=0.0, el2=45.0, slew_time=9.3),  # medium el slew
            Data(az1=0.0, el1=40.0, az2=0.0, el2=60.0, slew_time=32.4),  # long +el slew
            Data(az1=0.0, el1=40.0, az2=0.0, el2=20.0, slew_time=32.4),  # long -el slew
            Data(az1=275.0, el1=40.0, az2=-180.0, el2=40.0, slew_time=57.9),  # > 180 az
        ]
        for test in tests:
            initial_target = self.azel_target(test.az1, test.el1)
            self.DUT._fake_slew_(initial_target)
            slew_time = self.DUT._slew_time(test.az2, test.el2)
            self.assertAlmostEqual(slew_time, test.slew_time, places=2)
