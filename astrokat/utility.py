import ConfigParser
import ephem
import numpy
import yaml

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

# Read config .yaml file
def read_yaml(filename):
    with open(filename, 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except:
            raise
    return data


# Basic LST calculations using ephem
class LST:
    def __init__(self,
            latitude=None,
            longitude=None,
            elevation=None):
        self.observer = self.observer(
                lat=latitude,
                lon=longitude,
                elev=elevation)
    # default reference MeerKAT location
    def observer(self,
            lat=None,
            lon=None,
            elev=None):
        observer = ephem.Observer()
        observer.lon = lon if lon is not None else '21:24:38.5'
        observer.lat = lat if lat is not None else '-30:43:17.3'
        observer.elevation = elev if elev is not None else 1038.0
        observer.horizon = numpy.deg2rad(20.)
        observer.date = ephem.now()
        return observer

    def body(self, ra, dec, name=None):
        target = ephem.FixedBody()
        target.name = name
        target._ra = ra
        target._dec = dec
        target.compute(self.observer)
        return target

    def ephem_target(self, target_item):
        for item in target_item.split(','):
            item_ = item.strip()
            prefix = 'name='
            if item_.startswith(prefix):
                name = item_[len(prefix):]
            prefix = 'radec='
            if item_.startswith(prefix):
                ra = item_[len(prefix):].split()[0].strip()
                dec = item_[len(prefix):].split()[1].strip()
        return self.body(ra, dec, name=name)

    def start_obs(self, target_list):
        start_lst = []
        for target in target_list:
            rise_time = self.observer.next_rising(self.ephem_target(target))
            self.observer.date = rise_time
            start_lst.append(self.observer.sidereal_time())
        start_lst = start_lst[numpy.asarray(start_lst, dtype=float).argmin()]
        return str(start_lst).split(':')[0]

    def end_obs(self, target_list):
        end_lst = []
        for target in target_list:
            rise_time = self.observer.next_rising(self.ephem_target(target))
            set_time = self.observer.next_setting(self.ephem_target(target), start=rise_time)
            self.observer.date = set_time
            end_lst.append(self.observer.sidereal_time())
        end_lst = end_lst[numpy.asarray(end_lst, dtype=float).argmax()]
        return str(end_lst).split(':')[0]

# -fin-
