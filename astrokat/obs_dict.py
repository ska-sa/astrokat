# global definition of mkat instrument for observation file
instrument_ = {'product': None,
               'band': None,
               'integration_period': None,
               }
def get_instrument_dict():
    return dict(instrument_)

# global definition of mkat obs duration options for observation file
durations_ = {'obs_duration': None,
              'start_time': None,
              }
def get_durations_dict():
    return dict(durations_)


# global definition of target source for observation file
target_ = {'name':'',
           'coord': ['', ''],
           'tags': '',
           'duration': 0.,
           'cadence': None,
           'flux_model': None,
           }
def get_target_dict():
    return dict(target_)


# utility function to clean None default inputs
def remove_none_inputs_(args_dict_):
    clean_args_dict_ = {}
    for key in args_dict_.keys():
        if args_dict_[key] is not None:
            clean_args_dict_[key] = args_dict_[key]
    return clean_args_dict_


def unpack_target(target_str):
    """Unpack target string
       Input string format: name=, radec=, tags=, duration=, ...
    """
    coords = ["radec", "azel", "gal", "special"]
    target = get_target_dict()
    target_items = [item.strip() for item in target_str.split(",")]
    for item_ in target_items:
        key, value = item_.split('=')
        for coord in coords:
            if key.strip().startswith(coord):
                target['coord'] = [key.strip(), value.strip()]
                break
        if key.strip() in target.keys():
            target[key.strip()] = value.strip()
        if 'model' in key.strip():
            target['flux_model'] = value.strip()
    return target

# -fin-
