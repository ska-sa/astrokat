
from __future__ import print_function
from testconfig import config
import unittest2 as unittest

from astrokat import observe_main

class test_astrokat(unittest.TestCase):
    def print_all_tests(self):
        import sys
        for test in config['yaml_test_list']:
            status = observe_main.main(['--observer', 'jenkins','--yaml', 'astrokat/test/test_obs/{}.yaml'.format(test)])
