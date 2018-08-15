import ephem
import numpy
import katpoint


# Basic LST calculations using ephem
class LST:
    def __init__(self, ref_location=None):
        self.ref_location = 'ref, -30:42:47.4, 21:26:38.0, 1060.0, 0.0, , , 1.15'
        if ref_location is not None:
            self.ref_location = ref_location
        self.observer = self.observer()

    # default reference MeerKAT location
    def observer(self):
        observer = katpoint.Antenna(self.ref_location).observer
        observer.horizon = numpy.deg2rad(20.)
        observer.date = ephem.now()
        return observer

    def target(self, target):
        target = katpoint.Target(target)
        target.body.compute(self.observer)
        return target

    def unpack_target(self, target_item):
        # input string format: name=, radec=, tags=, duration=
        target_items = [item.strip() for item in target_item.split(',')]
        [name, coords] = target_items[:2]
        target_item = '{},{},{},{}'.format(
                name.split('=')[1].strip() if len(name.split('=')[1].strip()) > 1 else 'target',
                coords.split('=')[0].strip(),
                coords.split('=')[1].strip().split()[0],
                coords.split('=')[1].strip().split()[1],
                )
        return self.target(target_item)

    def start_obs(self, target_list):
        start_lst = []
        for target in target_list:
            target_ = self.unpack_target(target).body
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
            target_ = self.unpack_target(target).body
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

# # Collecting targets into katpoint catalogue
# def collect_targets(kat, args):
#     from_names = from_strings = from_catalogues = num_catalogues = 0
#     catalogue = katpoint.Catalogue()
#     catalogue.antenna = katpoint.Antenna(self.ref_location)
#     for arg in args:
#         try:
#             # First assume the string is a catalogue file name
#             count_before_add = len(catalogue)
#             try:
#                 catalogue.add(open(arg))
#             except ValueError:
#                 user_logger.warning('Catalogue {} contains bad targets'.format(arg))
#             from_catalogues += len(catalogue) - count_before_add
#             num_catalogues += 1
#         except IOError:
#             # If the file failed to load, assume it is a name or description string
#             # With no comma in target string, assume it's the name of a target
#             # to be looked up in standard catalogue
#             if arg.find(',') < 0:
#                 target = kat.sources[arg]
#                 if target is None:
#                     msg = 'Unknown target or catalogue {}, skipping it'.format(arg)
#                     user_logger.warning(msg)
#                 else:
#                     catalogue.add(target)
#                     from_names += 1
#             else:
#                 # Assume the argument is a target description string
#                 try:
#                     catalogue.add(arg)
#                     from_strings += 1
#                 except ValueError as err:
#                     user_logger.warning('Invalid target {}, skipping it [{}]'.format(
#                         arg, err))
#     if len(catalogue) == 0:
#         raise ValueError("No known targets found in argument list")
#     user_logger.info("Found {} target(s): {} from {} catalogue(s), {} from default catalogue and {} as target string(s)".format(
#         len(catalogue), from_catalogues, num_catalogues, from_names, from_strings))
#     return catalogue

# # -fin-
