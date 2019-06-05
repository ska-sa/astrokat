from __future__ import print_function
import unittest2 as unittest

from astrokat import observe_main, simulate

import logging
from io import StringIO


# - nd-pattern-sim
# - nd-pattern-ants
# - nd-pattern-cycle
# - nd-pattern-plus-off
# - nd-trigger

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

    def test_nd_pattern_sim(self):
        observe_main.main(['--yaml',
                           'astrokat/test/test_nd/{}.yaml'.format('nd-pattern-sim')])

        # get result and make sure everything ran properly
        result = self.string_stream.getvalue()
        self.assertIn('Single run through observation target list', result, 'Single run')
        self.assertIn('azel observed for 300.0 sec',
                      result, 'azel observed for 300.0 sec')

