from __future__ import print_function
from testconfig import config
import unittest2 as unittest

from astrokat import observe_main


class test_astrokat_yaml(unittest.TestCase):
    def run_all_tests(self):
        test_config = config['yaml_test_list']
        nd_config= test_config['test_nd_timing']
        for test in nd_config:
            print('Running test: {}'.format(test))
            observe_main.main(['--yaml',
                               'astrokat/test/test_nd/{}.yaml'.format(test)])
