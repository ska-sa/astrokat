from astropy import units as u
from astropy.coordinates import Galactic, ICRS
from astropy.coordinates import SkyCoord, AltAz
from astropy.coordinates import (solar_system_ephemeris,
                                 get_body)
from astropy.coordinates import Longitude, Latitude, EarthLocation
from astropy.time import Time

from .observatory import Observatory
from .utility import datetime2timestamp, timestamp2datetime

import numpy as np


# target description definition
tgt_desc = {
    "names": (
        # target description
        "name",
        "tags",
        "target",  # katpoint target str
        # per target observation instructions
        "duration",
        "cadence",
        "flux_model",
        "obs_type",
        "noise_diode",
        "last_observed",
        "obs_cntr",
    ),
    "formats": (
        object,
        object,
        object,
        float,
        float,
        object,
        object,
        object,
        object,
        int),
}

# coordinate types expected
# celestial targets, horizontal targets, galactic targets, solar system bodies
# where the solar system bodies are planets and moons in our solar system that
# do not follow standard celestial orbits.
coords = ["radec", "azel", "gal"]


# -- library function --
def tuple2str_(ra_float, dec_float):
    """ICRS string format HH:MM:SS.f, DD:MM:SS.f"""
    ra_str = ra_float.to_string(unit=u.hourangle,
                                sep=':',
                                precision=3,
                                pad=True)
    dec_str = dec_float.to_string(sep=':',
                                  precision=3,
                                  alwayssign=True,
                                  pad=True)
    return ra_str, dec_str


def get_radec_(pointing,
               # default output in degrees
               as_radians=False,
               as_string=False):
    """Astropy object to ICRS format as strings"""
    pnt_radec = pointing.transform_to(ICRS())
    if as_string:
        ra_hms, dec_dms = tuple2str_(pnt_radec.ra,
                                     pnt_radec.dec)
        return ra_hms, dec_dms
    elif as_radians:
        return pnt_radec.ra.rad, pnt_radec.dec.rad
    else:
        return pnt_radec.ra.deg, pnt_radec.dec.deg
# -- library function --


# -- coordinate conversion utilities --
def mkat_locale(observer):
    """Reference position is given in geodetic coordinates (lat, lon, height)

    Parameters
    ----------
    observer: `katpoint.Antenna.observer`

    Returns
    -------
    location: Geocentric location as `Astropy.EarthLocation`
    """

    location = EarthLocation.from_geodetic(Longitude(str(observer.lon),
                                                     u.degree,
                                                     wrap_angle=180. * u.degree,
                                                     copy=False),
                                           Latitude(str(observer.lat),
                                                    u.degree,
                                                    copy=False),
                                           height=u.Quantity(observer.elevation,
                                                             u.m,
                                                             copy=False))
    return location


def eq2hor(ra_hms, dec_dms, location, timestamp,
           as_radians=False):  # default output in degrees
    """Convert Equatorial to horizontal for MKAT

    Parameters
    ----------
    ra_hms: RA string HH:MM:SS.f
    dec_dms: Decl string DD:MM:SS.f
    location: Telescope geocentric position, `Astropy.EarthLocaton`
    timestamp: Unix timestamp

    Returns
    -------
    list: [alt, az] horizontal coordinates in degrees
    """

    obs_time = timestamp2datetime(timestamp)
    obs_time = obs_time.strftime("%Y-%m-%d %H:%M:%S")
    obs_time = Time(obs_time)
    observer = AltAz(location=location, obstime=obs_time)

    target = SkyCoord(ra=ra_hms, dec=dec_dms, frame='icrs')
    tgt_altaz = target.transform_to(observer)
    if as_radians:
        return tgt_altaz.alt.rad, tgt_altaz.az.rad
    else:
        return tgt_altaz.alt.deg, tgt_altaz.az.deg


def hor2eq(az_deg, el_deg, location, timestamp,
           # default output in degrees
           as_radians=False, as_string=False):
    """Convert Horizontal (az, el) to Equatorial (ra, dec)

    Parameters
    ----------
    az_deg: Azimuth angle, float degrees
    el_deg: Elevation angle, float degrees
    location: Telescope geocentric position, `Astropy.EarthLocaton`
    timestamp: Unix timestamp

    Returns
    -------
    list: [ra, dec] equatorial coordinates in degrees
    """

    obs_time = timestamp2datetime(timestamp)
    obs_time = obs_time.strftime("%Y-%m-%d %H:%M:%S")
    obs_time = Time(obs_time)

    pointing = AltAz(alt=el_deg * u.deg,
                     az=az_deg * u.deg,
                     location=location,
                     obstime=obs_time)

    return get_radec_(pointing,
                      as_radians=as_radians,
                      as_string=as_string)


def gal2eq(l_deg, b_deg,
           # default output in degrees
           as_radians=False, as_string=False):
    """Convert Galactic (l, b) to Equatorial (ra, dec)

    Parameters
    ----------
    l_deg: Galactic latitude, float degrees
    b_deg: Galactic Longitude, float degrees

    Returns
    -------
    list: [ra, dec] equatorial coordinates in degrees
    """
    gal_coord = SkyCoord(l=l_deg * u.degree,  # noqa
                         b=b_deg * u.degree,  # noqa
                         frame=Galactic)
    return get_radec_(gal_coord,
                      as_radians=as_radians,
                      as_string=as_string)


def solar2eq(body, location, timestamp,
             # default output in degrees
             as_radians=False, as_string=False):
    """Calculate equatorial (ra, dec) for solar body ephemerides

    Parameters
    ----------
    body: Name of solar body, Astropy convention
    location: Telescope geocentric position, `Astropy.EarthLocaton`
    timestamp: Unix timestamp

    Returns
    -------
    list: [ra, dec] equatorial coordinates in degrees
    """
    obs_time = timestamp2datetime(timestamp)
    obs_time = obs_time.strftime("%Y-%m-%d %H:%M:%S")
    obs_time = Time(obs_time)

    with solar_system_ephemeris.set('builtin'):
        solar_gcrs = get_body(body, obs_time, location)
    return get_radec_(solar_gcrs,
                      as_radians=as_radians,
                      as_string=as_string)


def get_radec_coords(target_str, timestamp=None, convert_azel=False):
    """If celestial target is not (Ra, Dec) convert and return (Ra, Dec)"""
    mkat = Observatory().get_location()  # return a katpoint.Antenna object
    location = mkat_locale(mkat.observer)
    if timestamp is None:
        timestamp = datetime2timestamp(mkat.observer.date.datetime())

    type_, coord_ = target_str.split('=')
    tgt_type = type_.strip()
    tgt_coord = coord_.strip()

    # a fundamental assumption will be that the user will give coordinates
    # in degrees, thus all input and output are in degrees
    if tgt_type == 'radec':
        try:
            ra_deg, dec_deg = np.array(tgt_coord.split(), dtype=float)
            pointing = SkyCoord(ra=ra_deg * u.degree,
                                dec=dec_deg * u.degree,
                                frame='icrs')
        except ValueError:
            ra_, dec_ = tgt_coord.split()
            pointing = SkyCoord(ra=ra_.strip(),
                                dec=dec_.strip(),
                                unit=(u.hourangle, u.deg),
                                frame='icrs')
        # ra_deg, dec_deg = np.array(tgt_coord.split(), dtype=float)
        # pointing = SkyCoord(ra=ra_deg * u.degree,
        #                     dec=dec_deg * u.degree,
        #                     frame='icrs')
        ra_hms, dec_dms = tuple2str_(pointing.ra, pointing.dec)
        tgt_coord = '{} {}'.format(str(ra_hms), str(dec_dms))
    elif tgt_type == 'gal':
        l_deg, b_deg = np.array(tgt_coord.split(), dtype=float)
        ra_hms, dec_dms = gal2eq(l_deg,
                                 b_deg,
                                 as_string=True)
        tgt_type = "radec"
        tgt_coord = '{} {}'.format(str(ra_hms), str(dec_dms))
    elif tgt_type == 'azel' and convert_azel:
        az_deg, el_deg = np.array(tgt_coord.split(), dtype=float)
        ra_hms, dec_dms = hor2eq(az_deg,
                                 el_deg,
                                 location,
                                 timestamp,
                                 as_string=True)
        tgt_type = "radec"
        tgt_coord = '{} {}'.format(str(ra_hms), str(dec_dms))
    else:
        pass  # do nothing just pass the target along

    return [tgt_type, tgt_coord]

# -- coordinate conversion utilities --


def unpack_target(target_str, timestamp=None):
    """Unpack target string
       Input string format: name=, radec=, tags=, duration=, ...
    """
    target = {}
    target_items = [item.strip() for item in target_str.split(",")]

    # find observation type if specified
    obs_type = next((item_ for item_ in target_items if 'type' in item_), None)
    convert_azel = False
    if obs_type is not None:
        _, type_ = obs_type.split('=')
        # if azel coord are scan observation, convert to (ra, dec)
        convert_azel = 'scan' in type_

    target_keys = tgt_desc["names"]
    for item_ in target_items:
        key, value = item_.split('=')
        for coord in coords:
            if key.strip().startswith(coord):
                # get target celestial (ra, dec) coordinates
                target["coord"] = get_radec_coords(item_,
                                                   timestamp=timestamp,
                                                   convert_azel=convert_azel)
                break
        if key.strip() in target_keys:
            target[key.strip()] = value.strip()
        if 'model' in key.strip():
            target['flux_model'] = value.strip()
        else:
            target['flux_model'] = ()
        if 'type' in key.strip():
            target['obs_type'] = value.strip()
    if "coord" not in target.keys():
        raise RuntimeError("Target \'{}\' not currently supported by default".
                           format(target_str))
    return target


def katpoint_target(target_str=None,
                    name='source',
                    ctag='radec',
                    x=None,
                    y=None,
                    tags=None,
                    flux_model=(),
                    ):
    """Construct an expected katpoint target from a target_item string."""
    if target_str is not None:
        # input string format: name=, radec=, tags=, duration=, ...
        target_dict = unpack_target(target_str)
        name = target_dict["name"]
        ctag = target_dict["coord"][0]
        x = target_dict["coord"][1].split()[0].strip()
        y = target_dict["coord"][1].split()[1].strip()
        tags = target_dict["tags"]
        flux_model = target_dict["flux_model"]
    else:
        if (x is None or y is None):
            raise RuntimeError('Ill defined target, require: x and y')

    target = "{}, {} {}, {}, {}, {}".format(name,
                                            ctag,
                                            tags,
                                            x, y,
                                            flux_model)
    return name, target


def build_target(target_dict, timestamp=None):
    """Restructure dictionary into target defined recarray for observation"""
    # When unpacking, katpoint's naming convention will be to use the first
    # name, or the name with the '*' if given. This unpacking mimics that
    # expected behaviour to ensure the target can be easily called by name
    ctag = target_dict["coord"][0].strip()
    x = target_dict["coord"][1].split()[0].strip()
    y = target_dict["coord"][1].split()[1].strip()
    [name_list, katpoint_tgt] = katpoint_target(name=target_dict["name"],
                                                ctag=ctag,
                                                x=x, y=y,
                                                tags=target_dict["tags"],
                                                flux_model=target_dict["flux_model"],
                                                )
    name_list = [name.strip() for name in name_list.split("|")]
    prefered_name = list(filter(lambda x: x.startswith("*"), name_list))
    if prefered_name:
        target_name = prefered_name[0][1:]
    else:
        target_name = name_list[0]

    # process observation keywords from YAML input
    if "duration" in target_dict.keys():
        duration = float(target_dict["duration"])
    else:
        duration = np.nan
    if "cadence" in target_dict.keys():
        cadence = float(target_dict["cadence"])
    else:
        cadence = -1  # default is to observe without cadence
    if "obs_type" in target_dict.keys():
        obs_type = target_dict["obs_type"]
    else:
        obs_type = "track"  # assume tracking a target
    if "noise_diode" in target_dict.keys():
        nd = target_dict["noise_diode"]
    else:
        nd = None
    if "last_observed" in target_dict.keys():
        last_observed = target_dict["last_observed"]
    else:
        last_observed = None
    if "obs_cntr" in target_dict.keys():
        obs_cntr = target_dict["obs_cntr"]
    else:
        obs_cntr = 0

    return (target_name,
            target_dict["tags"],
            katpoint_tgt,
            duration,
            cadence,
            target_dict["flux_model"],
            obs_type,
            nd,
            last_observed,
            obs_cntr
            )


def read(target_items, timestamp=None):
    """Read targets info.

    Unpack targets target items to a katpoint compatible format
    Update all targets to have celestial (Ra, Dec) coordinates

    """
    ntargets = len(target_items)
    target_list = np.recarray(ntargets, dtype=tgt_desc)
    for cnt, target_item in enumerate(target_items):
        # build astrokat target info from dict definition
        target_dict = unpack_target(target_item, timestamp=timestamp)
        # pack target dictionary in observation ready target rec-array
        target_ = build_target(target_dict,
                               timestamp=timestamp)
        target_list[cnt] = target_
    return target_list


# -fin-
