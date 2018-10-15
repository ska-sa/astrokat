import ephem
import numpy
import katpoint

from datetime import datetime
from simulate import user_logger, setobserver
from utility import katpoint_target, lst2utc

# default reference position for MKAT array
ref_location = 'ref, -30:42:47.4, 21:26:38.0, 1060.0, 0.0, , , 1.15'


# Basic LST calculations using ephem
class Observatory(object):
    def __init__(self, location=None):
        self.location = ref_location
        if location is not None:
            self.location = location
        self.mkat = self.get_location()
        self.observer = self.get_observer()

    def _ephem_risetime_(self, ephem_target, lst=True):
        try:
            rise_time = self.observer.next_rising(ephem_target)
        except ephem.AlwaysUpError:
            return ephem.hours('0:0:01.0')
        except AttributeError:
            return ephem.hours('0:0:01.0')

        if not lst:
            return rise_time
        self.observer.date = rise_time
        return self.observer.sidereal_time()

    def _ephem_settime_(self, ephem_target, lst=True):
        try:
            rise_time = self.observer.next_rising(ephem_target)
            set_time = self.observer.next_setting(ephem_target,
                                                  start=rise_time)
        except ephem.AlwaysUpError:
            return ephem.hours('23:59:59.0')
        except AttributeError:
            return ephem.hours('23:59:59.0')

        if not lst:
            return set_time
        self.observer.date = set_time
        return self.observer.sidereal_time()

    # default reference location
    def get_location(self):
        return katpoint.Antenna(self.location)

    # MeerKAT observer
    def get_observer(self, horizon=20.):
        observer = self.mkat.observer
        observer.horizon = numpy.deg2rad(horizon)
        observer.date = ephem.now()
        return observer

    def set_target(self, target):
        target = katpoint.Target(target)
        target.body.compute(self.observer)
        return target

    def get_target(self, target_item):
        name, target_item = katpoint_target(target_item)
        return self.set_target(target_item)

    def unpack_target(self, target_item):
        target_dict = {}
        for item in target_item.split(','):
            item_ = item.strip().split('=')
            target_dict[item_[0].strip()] = item_[1].strip()
        return target_dict

    def lst2hours(self, ephem_lst):
        time_ = datetime.strptime('{}'.format(ephem_lst), '%H:%M:%S.%f').time()
        time_ = time_.hour + \
            (time_.minute/60.) + \
            (time_.second+time_.microsecond/1e6)/3600.
        return '%.3f' % time_

    def start_obs(self, target_list):
        start_lst = []
        for target in target_list:
            target_ = self.get_target(target).body
            start_lst.append(self._ephem_risetime_(target_))
        start_lst = start_lst[numpy.asarray(start_lst, dtype=float).argmin()]
        return self.lst2hours(start_lst)

    def end_obs(self, target_list):
        end_lst = []
        for target in target_list:
            target_ = self.get_target(target).body
            end_lst.append(self._ephem_settime_(target_))
        end_lst = end_lst[numpy.asarray(end_lst, dtype=float).argmax()]
        return self.lst2hours(end_lst)


# Collecting targets into katpoint catalogue
def collect_targets(kat, args):
    from_names = from_strings = from_catalogues = num_catalogues = 0
    catalogue = katpoint.Catalogue()
    catalogue.antenna = katpoint.Antenna(ref_location)
    catalogue.antenna.observer.date = lst2utc(kat._lst, ref_location)

    setobserver(catalogue.antenna.observer)

    for arg in args:
        try:
            # First assume the string is a catalogue file name
            count_before_add = len(catalogue)
            try:
                catalogue.add(open(arg))
            except ValueError:
                msg = 'Catalogue {} contains bad targets'.format(arg)
                user_logger.warning(msg)
            from_catalogues += len(catalogue) - count_before_add
            num_catalogues += 1
        except IOError:
            # If the file failed to load,
            # assume it is a name or description string
            # With no comma in target string,
            # assume it's the name of a target
            # to be looked up in standard catalogue
            if arg.find(',') < 0:
                target = kat.sources[arg]
                if target is None:
                    msg = 'Unknown target or catalogue {}, skipping it'.format(arg)
                    user_logger.warning(msg)
                else:
                    catalogue.add(target)
                    from_names += 1
            else:
                # Assume the argument is a target description string
                try:
                    catalogue.add(arg)
                    from_strings += 1
                except ValueError as err:
                    msg = 'Invalid target {}, skipping it [{}]'.format(
                        arg, err)
                    user_logger.warning(msg)
    if len(catalogue) == 0:
        raise ValueError("No known targets found in argument list")
    msg = "Found {} target(s): {} from {} catalogue(s), {} from default catalogue and {} as target string(s)".format(
            len(catalogue),
            from_catalogues,
            num_catalogues,
            from_names,
            from_strings)
    user_logger.info(msg)
    return catalogue

# -fin-
