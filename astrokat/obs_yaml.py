# global definition of string formats for YAML file


def target_str(target_dict):
    """Construct YAML target string from dictionary"""
    target_spec = "name={}, {}={}, tags={}, duration={}"
    cadence = ", cadence={}"
    flux_model = ", model={}"

    if 'special' in target_dict['coord'][0]:
        target_dict['coord'][1] = 'special'

    target_= [target_dict['name'],
              target_dict['coord'][0], 
              target_dict['coord'][1], 
              target_dict['tags'],
              target_dict['duration'],
              ]
    if target_dict['cadence'] is not None:
        target_spec += cadence
        target_.append(target_dict['cadence'])
    if target_dict['flux_model']  is not None:
        target_spec += flux_model
        target_.append(target_dict['flux_model'])

    try:
        target = target_spec.format(*target_)
    except IndexError:
        msg = "Incorrect target definition\n"
        msg += "Verify line: {}".format(line.strip())
        raise RuntimeError(msg)

    return target


def dict_str(name, dict_):
    """YAML section from dictionary"""
    str_ = "{}:\n".format(name)
    for key in dict_.keys():
        if dict_[key] is not None:
            str_ += "  {}: {}\n".format(key, dict_[key])
    return str_


def obs_dict_str(lst, dict_list_):
    """Observation loop in YAML from list of dictionaries"""
    str_ = "{}:\n".format("observation_loop")
    str_ += "  - LST: {}\n".format(lst)
    str_ += "    target_list:\n"
    for dict_ in dict_list_:
        target = target_str(dict_)
        str_ += "      - {}\n".format(target)
    return str_


def obs_str(instrument_dict,
            durations_dict,
            lst,
            target_dict_list,
            horizon=20.,
            ):
    """Build the content of the YAML observation script"""

    obs_plan_str = ""
    # subarray specific setup options
    if len(instrument_dict) > 0:
        obs_plan_str += dict_str("instrument", instrument_dict)
    # observation duration settings
    if len(durations_dict) > 0:
        obs_plan_str += dict_str("durations", durations_dict)

    # target observation sections
    obs_plan_str += "horizon: {}\n".format(horizon)
    obs_plan_str += obs_dict_str(lst, target_dict_list)

    return obs_plan_str


# -fin-
