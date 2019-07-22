###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2019 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
import logging
import os
from six.moves import StringIO

from astrokat import observe_main, simulate


__all__ = ['yaml_path', 'LoggedTelescope']


def yaml_path(file_path):
    tests_path = os.path.abspath(os.path.dirname(__file__))
    """Convenience method for finding the yaml's file absolute path."""
    yaml_file = os.path.abspath(os.path.join(tests_path, file_path))
    assert os.path.isfile(yaml_file)
    return yaml_file


class LoggedTelescope(observe_main.Telescope):

    string_stream = StringIO()

    def __init__(self, *args, **kwargs):
        super(LoggedTelescope, self).__init__(*args, **kwargs)
        # Add log handler AFTER init, as the user_logger is
        # replaced during init
        out_hdlr = logging.StreamHandler(self.string_stream)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        formatter.formatTime = simulate.sim_time
        out_hdlr.setFormatter(formatter)
        out_hdlr.setLevel(logging.TRACE)
        user_logger = observe_main.user_logger
        user_logger.addHandler(out_hdlr)
        user_logger.setLevel(logging.INFO)
