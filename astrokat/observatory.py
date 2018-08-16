import ephem
import numpy
import katpoint

from simulate import user_logger
from utility import katpoint_target

from datetime import datetime, timedelta
import time

# default reference position for MKAT array
ref_location = 'ref, -30:42:47.4, 21:26:38.0, 1060.0, 0.0, , , 1.15'

# Basic LST calculations using ephem
class Observatory:
    def __init__(self, location=None):
        self.location = ref_location
        if location is not None:
            self.location = location
        self.mkat = self.get_location()
        self.observer = self.get_observer()

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

##TODO: look at this again with comparison to the utility.katpoint_target function
    def get_target(self, target_item):
        target_item = katpoint_target(target_item)
        return self.set_target(target_item)


    def lst2utc(self, req_lst, date=None):
        def get_lst_range(date):
            time_range = katpoint.Timestamp(time.mktime(date.timetuple())).secs + numpy.arange(0, 24.*3600., 60)
            lst_range = katpoint.rad2deg(target.antenna.local_sidereal_time(time_range)) / 15
            return time_range, lst_range

        req_lst = float(req_lst)
        cat = katpoint.Catalogue(add_specials=True)
        cat.antenna = self.mkat
        target = cat['Zenith']
        if date is None:  # find the best UTC for today
            [time_range, lst_range] = get_lst_range(datetime.now())
            dh = req_lst - lst_range[0]
            date = datetime.now()+timedelta(hours=dh)
        [time_range, lst_range] = get_lst_range(date)
        lst_idx = numpy.abs(lst_range-req_lst).argmin()
        return datetime.utcfromtimestamp(time_range[lst_idx+1])


    def unpack_target(self, target_item):
        target_dict = {}
        for item in target_item.split(','):
            item_ = item.strip().split('=')
            target_dict[item_[0].strip()] = item_[1].strip()
        return target_dict

    def start_obs(self, target_list):
        start_lst = []
        for target in target_list:
            target_ = self.get_target(target).body
            try:
                rise_time = self.observer.next_rising(target_)
            except ephem.AlwaysUpError:
                start_lst.append(0)
            except AttributeError:
                start_lst.append(0)
            else:
                self.observer.date = rise_time
                start_lst.append(self.observer.sidereal_time())
        start_lst = start_lst[numpy.asarray(start_lst, dtype=float).argmin()]
        if start_lst > 0:
            start_lst = str(start_lst).split(':')[0]
        return start_lst

    def end_obs(self, target_list):
        end_lst = []
        for target in target_list:
            target_ = self.get_target(target).body
            try:
                rise_time = self.observer.next_rising(target_)
                set_time = self.observer.next_setting(target_, start=rise_time)
            except ephem.AlwaysUpError:
                end_lst.append(23)
            except AttributeError:
                end_lst.append(23)
            else:
                self.observer.date = set_time
                end_lst.append(self.observer.sidereal_time())
        end_lst = end_lst[numpy.asarray(end_lst, dtype=float).argmax()]
        if end_lst < 23:
            end_lst = str(end_lst).split(':')[0]
        return end_lst

# Collecting targets into katpoint catalogue
def collect_targets(kat, args):
    from_names = from_strings = from_catalogues = num_catalogues = 0
    catalogue = katpoint.Catalogue()
    catalogue.antenna = katpoint.Antenna(ref_location)
    for arg in args:
        try:
            # First assume the string is a catalogue file name
            count_before_add = len(catalogue)
            try:
                catalogue.add(open(arg))
            except ValueError:
                user_logger.warning('Catalogue {} contains bad targets'.format(arg))
            from_catalogues += len(catalogue) - count_before_add
            num_catalogues += 1
        except IOError:
            # If the file failed to load, assume it is a name or description string
            # With no comma in target string, assume it's the name of a target
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
                    user_logger.warning('Invalid target {}, skipping it [{}]'.format(
                        arg, err))
    if len(catalogue) == 0:
        raise ValueError("No known targets found in argument list")
    user_logger.info("Found {} target(s): {} from {} catalogue(s), {} from default catalogue and {} as target string(s)".format(
        len(catalogue), from_catalogues, num_catalogues, from_names, from_strings))
    return catalogue

# -fin-
