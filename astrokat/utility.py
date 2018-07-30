import ConfigParser

class NotAllTargetsUpError(Exception):
    """Not all targets are above the horizon at the start of the observation."""


class NoTargetsUpError(Exception):
    """No targets are above the horizon at the start of the observation."""


# Read config .ini file
def read_config(filename):
    config_params = {}
    config = ConfigParser.SafeConfigParser()
    config.read(filename)
    for section in config.sections():
        config_params[section] = {}
        for option in config.options(section):
            try: config_params[section][option] = float(config.get(section,option))
            except: config_params[section][option] = config.get(section,option)
    return config_params
