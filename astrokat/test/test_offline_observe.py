from __future__ import print_function
import unittest2 as unittest

from astrokat import observe_main, simulate

import logging
from io import StringIO


class test_strokat_yaml(unittest.TestCase):

    def setUp(self):
        user_logger = logging.getLogger('astrokat.simulate')

        # remove current handlers
        for handler in user_logger.handlers:
            user_logger.removeHandler(handler)

        self.string_stream = StringIO()
        out_hdlr = logging.StreamHandler(self.string_stream)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        formatter.formatTime = simulate.sim_time
        out_hdlr.setFormatter(formatter)
        out_hdlr.setLevel(logging.TRACE)
        user_logger.addHandler(out_hdlr)
        user_logger.setLevel(logging.INFO)

    def test_targets_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_obs/{}.yaml'.format('targets-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('target0_radec observed for 10.0 sec',
                      result, 'target0_radec observed for 10.0 sec')
        self.assertIn('target1_azel observed for 10.0 sec',
                      result, 'target1_azel observed for 10.0 sec')
        self.assertIn('target2_gal observed for 10.0 sec',
                      result, 'target2_gal observed for 10.0 sec')

    def test_two_calib_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_obs/{}.yaml'.format('two-calib-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('Bandpass calibrators are [\'1934-638\', \'0408-65\']', result,
                      'two Bandpass calibrators')
        self.assertIn('0408-65 observed', result, '0408-65 observed')
        self.assertIn('0408-65 observed', result, '0408-65 observed')

    def test_drift_targets_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_obs/{}.yaml'.format('drift-targets-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('0408-65 observed', result, '0408-65 observed')
        self.assertIn('1934-638 observed', result, '1934-638 observed')
        self.assertEqual(result.count('Drift_scan observation for'), 2, 'two drift scans')

    # def test_raster_scans_sim(self):
    #     observe_main.main(['--yaml',
    #                        'astrokat/test/test_obs/{}.yaml'.format('raster-scans-sim')])
    #
    #     # get result and make sure everything ran properly
    #     result = self.string_stream.getvalue()
    #     self.assertIn('Single run through observation target list', result, 'Single run')
    #     self.assertIn('0408-65 observed', result, '0408-65 observed')
    #     self.assertIn('1934-638 observed', result, '1934-638 observed')
    #     self.assertEqual(result.count('Drift_scan observation for'), 2, 'two drift scans')

    def test_image_single_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_obs/{}.yaml'.format('image-single-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')

        self.assertIn(
            ("Imaging targets are ['T3R04C06', 'T4R00C02', 'T4R00C04', 'T4R00C06',"
             " 'T4R01C01', 'T4R01C03', 'T4R01C05', 'T4R02C02', 'T4R02C04']"),
            result, 'Nine imaging targets'
        )

        self.assertIn("Bandpass calibrators are ['1934-638', '3C286']",
                      result, 'two bandpass calibrators')

        self.assertIn("Gain calibrators are ['1827-360']",
                      result, 'one gain calibrator')

        self.assertIn('1827-360 observed for 30.0 sec',
                      result, '1827-360 observed for 30.0 sec')
        self.assertIn('1934-638 observed for 120.0 sec',
                      result, '1934-638 observed for 120.0 sec')
        self.assertIn('3C286 observed for 100.0 sec',
                      result, '3C286 observed for 100.0 sec')
        self.assertIn('T3R04C06 observed for 180.0 sec',
                      result, 'T3R04C06 observed for 180.0 sec')
        self.assertIn('T4R00C02 observed for 180.0 sec',
                      result, 'T4R00C02 observed for 180.0 sec')
        self.assertIn('T4R00C04 observed for 180.0 sec',
                      result, 'T4R00C04 observed for 180.0 sec')
        self.assertIn('T4R00C06 observed for 180.0 sec',
                      result, 'T4R00C06 observed for 180.0 sec')
        self.assertIn('T4R01C01 observed for 180.0 sec',
                      result, 'T4R01C01 observed for 180.0 sec')
        self.assertIn('T4R01C03 observed for 180.0 sec',
                      result, 'T4R01C03 observed for 180.0 sec')
        self.assertIn('T4R01C05 observed for 180.0 sec',
                      result, 'T4R01C05 observed for 180.0 sec')
        self.assertIn('T4R02C02 observed for 180.0 sec',
                      result, 'T4R02C02 observed for 180.0 sec')
        self.assertIn('T4R02C04 observed for 180.0 sec',
                      result, 'T4R02C04 observed for 180.0 sec')

    def test_image_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_obs/{}.yaml'.format('image-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Scheduled observation time lapsed - ending observation',
                      result, 'observation time lapsed')

        self.assertIn(
            ("Imaging targets are ['T3R04C06', 'T4R00C02', 'T4R00C04', 'T4R00C06',"
             " 'T4R01C01', 'T4R01C03', 'T4R01C05', 'T4R02C02', 'T4R02C04']"),
            result, 'Nine imaging targets'
        )

        self.assertIn("Bandpass calibrators are ['1934-638', '3C286']",
                      result, 'two bandpass calibrators')

        self.assertIn("Gain calibrators are ['1827-360']",
                      result, 'one gain calibrator')

        self.assertIn('1827-360 observed for 30.0 sec',
                      result, '1827-360 observed for 30.0 sec')
        self.assertIn('1934-638 observed for 120.0 sec',
                      result, '1934-638 observed for 120.0 sec')
        self.assertIn('3C286 observed for 160.0 sec',
                      result, '3C286 observed for 160.0 sec')
        self.assertIn('T3R04C06 observed for 360.0 sec',
                      result, 'T3R04C06 observed for 360.0 sec')
        self.assertIn('T4R00C02 observed for 360.0 sec',
                      result, 'T4R00C02 observed for 360.0 sec')
        self.assertIn('T4R00C04 observed for 360.0 sec',
                      result, 'T4R00C04 observed for 360.0 sec')
        self.assertIn('T4R00C06 observed for 360.0 sec',
                      result, 'T4R00C06 observed for 360.0 sec')
        self.assertIn('T4R01C01 observed for 360.0 sec',
                      result, 'T4R01C01 observed for 360.0 sec')
        self.assertIn('T4R01C03 observed for 360.0 sec',
                      result, 'T4R01C03 observed for 360.0 sec')
        self.assertIn('T4R01C05 observed for 180.0 sec',
                      result, 'T4R01C05 observed for 180.0 sec')
        self.assertIn('T4R02C02 observed for 180.0 sec',
                      result, 'T4R02C02 observed for 180.0 sec')
        self.assertIn('T4R02C04 observed for 180.0 sec',
                      result, 'T4R02C04 observed for 180.0 sec')
