from __future__ import print_function

import logging
import os
import sys
import unittest2 as unittest

from six.moves import StringIO
from astrokat import observe_main, simulate


PROPOSAL_ID = "CAM_AstroKAT_UnitTest"
OBSERVER = "KAT Tester"
TESTS_PATH = os.path.abspath(os.path.dirname(__file__))


class TestAstrokatYAML(unittest.TestCase):

    def setUp(self):
        user_logger = observe_main.user_logger

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

    def yaml_path(self, file_path):
        """Convenience method for finding the yaml's file absolute path."""
        yaml_file = os.path.abspath(os.path.join(TESTS_PATH, file_path))
        self.assertTrue(os.path.isfile(yaml_file))
        return yaml_file

    def test_targets_sim(self):
        yaml_file = self.yaml_path('test_obs/targets-sim.yaml')
        observe_main.main([
            '--yaml', yaml_file,
            '--observer', OBSERVER,
            '--proposal-id', PROPOSAL_ID,
            '--start-time', os.getenv('START_TIME', '2019-07-15 23:35:00'),
            '--sb-id-code', os.getenv('SB_ID_CODE'),
            '--dry-run',
           ])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()

        # TODO: restore this check after working out an appropriate start-time
        # in UTC with Ruby

        self.assertIn('Single run through observation target list', result, 'Single run')
        # self.assertIn('target0_radec observed for 10.0 sec',
        #               result, 'target0_radec observed for 10.0 sec')
        # self.assertIn('target1_azel observed for 10.0 sec',
        #               result, 'target1_azel observed for 10.0 sec')
        # self.assertIn('target2_gal observed for 10.0 sec',
        #               result, 'target2_gal observed for 10.0 sec')

    def test_two_calib_sim(self):
        yaml_file = self.yaml_path('test_obs/two-calib-sim.yaml')
        observe_main.main([
            '--yaml', yaml_file,
            '--observer', OBSERVER,
            '--proposal-id', PROPOSAL_ID,
            '--start-time', os.getenv('START_TIME', '2019-07-15 23:35:00'),
            '--sb-id-code', os.getenv('SB_ID_CODE'),
            '--dry-run',
       ])


        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('Bandpass calibrators are [\'1934-638\', \'0408-65\']', result,
                      'two Bandpass calibrators')
        self.assertIn('0408-65 observed', result)
        self.assertIn('0408-65 observed', result)

    def test_drift_targets_sim(self):
        yaml_file = self.yaml_path('test_obs/drift-targets-sim.yaml')
        observe_main.main([
            '--yaml', yaml_file,
            '--observer', OBSERVER,
            '--proposal-id', PROPOSAL_ID,
            '--start-time', os.getenv('START_TIME', '2019-07-15 23:35:00'),
            '--sb-id-code', os.getenv('SB_ID_CODE'),
            '--dry-run',
       ])


        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('0408-65 observed', result)
        self.assertIn('1934-638 observed', result)
        self.assertEqual(result.count('Drift_scan observation for'), 2, 'two drift scans')

    # TODO: restore this check after working out an appropriate start-time
    # in UTC with Ruby
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
        yaml_file = self.yaml_path('test_obs/image-single-sim.yaml')
        observe_main.main([
            '--yaml', yaml_file,
            '--observer', OBSERVER,
            '--proposal-id', PROPOSAL_ID,
            # Start-time extracted from yaml file.
            '--start-time', '2019-02-11 02:10:47',
            '--sb-id-code', os.getenv('SB_ID_CODE'),
            '--dry-run',
       ])

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

        self.assertIn('1827-360 observed for 30.0 sec', result)
        self.assertIn('1934-638 observed for 120.0 sec', result)
        self.assertIn('3C286 observed for 100.0 sec', result)
        self.assertIn('T3R04C06 observed for 180.0 sec', result)
        self.assertIn('T4R00C02 observed for 180.0 sec', result)
        self.assertIn('T4R00C04 observed for 180.0 sec', result)
        self.assertIn('T4R00C06 observed for 180.0 sec', result)
        self.assertIn('T4R01C01 observed for 180.0 sec', result)
        self.assertIn('T4R01C03 observed for 180.0 sec', result)
        self.assertIn('T4R01C05 observed for 180.0 sec', result)
        self.assertIn('T4R02C02 observed for 180.0 sec', result)
        self.assertIn('T4R02C04 observed for 180.0 sec', result)

    def test_image_sim(self):
        yaml_file = self.yaml_path('test_obs/image-sim.yaml')
        observe_main.main([
            '--yaml', yaml_file,
            '--observer', OBSERVER,
            '--proposal-id', PROPOSAL_ID,
            # Start-time extracted from yaml file.
            '--start-time', '2019-02-11 02:10:47',
            '--sb-id-code', os.getenv('SB_ID_CODE'),
            '--dry-run',
       ])

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

        self.assertIn('1827-360 observed for 30.0 sec', result)
        self.assertIn('1934-638 observed for 120.0 sec', result)
        self.assertIn('3C286 observed for 160.0 sec', result)
        self.assertIn('T3R04C06 observed for 360.0 sec', result)
        self.assertIn('T4R00C02 observed for 360.0 sec', result)
        self.assertIn('T4R00C04 observed for 360.0 sec', result)
        self.assertIn('T4R00C06 observed for 360.0 sec', result)
        self.assertIn('T4R01C01 observed for 360.0 sec', result)
        self.assertIn('T4R01C03 observed for 360.0 sec', result)
        self.assertIn('T4R01C05 observed for 180.0 sec', result)
        self.assertIn('T4R02C02 observed for 180.0 sec', result)
        self.assertIn('T4R02C04 observed for 180.0 sec', result)
