"""."""
import logging
import os
from six.moves import StringIO

from astrokat import observe_main, simulate, utility


def yaml_path(file_path):
    """Find the yaml file absolute path.

    Args:
        file_path (str): YAML file path

    Returns:
        str: YAML file absolute path

    """
    tests_path = os.path.abspath(os.path.dirname(__file__))
    yaml_file = os.path.abspath(os.path.join(tests_path, file_path))
    assert os.path.isfile(yaml_file)
    return yaml_file


def extract_start_time(yaml_file):
    """Extract start_time from yaml.

    :param yaml_file: full path file name to yaml file
    :return: start_time if it exists in yaml file

    """
    yaml = utility.read_yaml(yaml_file)
    if yaml and yaml.get("durations") and yaml.get(
            "durations").get("start_time"):
        return yaml["durations"]["start_time"]


def execute_observe_main(file_name):
    """Run observer_main with correct parameters.

    :param file_name: relative path to yaml file

    """
    yaml_file = yaml_path(file_name)
    start_time = extract_start_time(yaml_file)

    params = [
        "--yaml", yaml_file,
        "--observer", "KAT Tester",
        "--proposal-id", "CAM_AstroKAT_UnitTest",
        "--dry-run",
    ]

    sb_id_code = os.getenv("SB_ID_CODE")
    if sb_id_code:
        params.append("--sb-id-code")
        params.append(sb_id_code)

    if start_time:
        params.append("--start-time")
        params.append(str(start_time))

    observe_main.main(params)


class LoggedTelescope(observe_main.Telescope):
    """Use as class decorator for test case.

    The body of the test case class is patched with a new object.

    Note: that when the class exits the patch is undone.

    Attributes:
        user_logger_stream (_io.StringIO): Text I/O implementation using an in-memory
            buffer.

    """

    user_logger_stream = StringIO()

    def __init__(self, *args, **kwargs):
        """Add log handler AFTER init.

        as the user_logger is replaced during init.

        """
        super(LoggedTelescope, self).__init__(*args, **kwargs)

        out_hdlr = logging.StreamHandler(self.user_logger_stream)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        formatter.formatTime = simulate.sim_time
        out_hdlr.setFormatter(formatter)
        out_hdlr.setLevel(logging.TRACE)
        user_logger = observe_main.user_logger
        user_logger.addHandler(out_hdlr)
        user_logger.setLevel(logging.INFO)

    @staticmethod
    def reset_user_logger_stream():
        """Reset an in-memory buffer.

        See: https://stackoverflow.com/a/4330829/6165344
        """
        LoggedTelescope.user_logger_stream = StringIO()
