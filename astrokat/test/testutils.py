import logging
import os
from six.moves import StringIO

from astrokat import observe_main, simulate


__all__ = ['yaml_path', 'LoggedTelescope']


def yaml_path(file_path):
    """Convenience method for finding the yaml's file absolute path.

    Args:
        file_path (str): YAML file path

    Returns:
        str: YAML file absolute path
    """
    tests_path = os.path.abspath(os.path.dirname(__file__))
    yaml_file = os.path.abspath(os.path.join(tests_path, file_path))
    assert os.path.isfile(yaml_file)
    return yaml_file


class LoggedTelescope(observe_main.Telescope):

    """
    Class to be used as class decorator for test case.
    The body of the test case class is patched with a new object.
    When the class exits the patch is undone.

    Attributes:
        user_logger_stream (_io.StringIO): Text I/O implementation using an in-memory
            buffer.
    """

    user_logger_stream = StringIO()

    def __init__(self, *args, **kwargs):
        super(LoggedTelescope, self).__init__(*args, **kwargs)
        # Add log handler AFTER init, as the user_logger is
        # replaced during init
        out_hdlr = logging.StreamHandler(self.user_logger_stream)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        formatter.formatTime = simulate.sim_time
        out_hdlr.setFormatter(formatter)
        out_hdlr.setLevel(logging.TRACE)
        user_logger = observe_main.user_logger
        user_logger.addHandler(out_hdlr)
        user_logger.setLevel(logging.INFO)
