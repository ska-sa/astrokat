"""Scan observations."""
from __future__ import division
from __future__ import absolute_import

import copy
import time

import katpoint
import numpy as np

from .noisediode import trigger

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger


_MIN_HORIZON_EL_FOR_SCAN_DEG = 15.0
_HORIZON_ANGLE_OFFSET_DEG = 2.0
_MAX_POINTS_IN_SCAN_AREA_POLYGON = 10
_DEFAULT_SCAN_SPEED_ARCMIN_PER_SEC = 5.0


def drift_pointing_offset(ref_antenna, target, duration=60.0):
    """Drift pointing offset observation.

    Parameters
    ----------
    target: katpoint.Target
    duration: float

    """
    obs_start_ts = ref_antenna.observer.date
    transit_time = (katpoint.Timestamp(obs_start_ts) + duration / 2.0).to_ephem_date()
    # Stationary transit point becomes new target
    az, el = target.azel(timestamp=transit_time, antenna=ref_antenna)
    target = katpoint.construct_azel_target(katpoint.wrap_angle(az), el)
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    target.antenna = ref_antenna
    target.antenna.observer.date = obs_start_ts
    return target


def drift_scan(session,
               ref_antenna,
               target,
               duration=60.0,
               nd_period=None,
               lead_time=None):
    """Drift scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    ref_antenna: katpoint.Antenna
    target: katpoint.Target
    duration: float
        scan duration
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    target = drift_pointing_offset(ref_antenna, target, duration=duration)
    user_logger.info("Drift_scan observation for {} sec".format(duration))
    return session.track(target, duration=duration)


def raster_scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Raster scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    # TODO: ignoring raster_scan, not currently working robustly
    # TODO: there are errors in raster scan calculations, need some review
    #     session.raster_scan(target,num_scans=2,
    #                             scan_duration=120,
    #                             scan_extent=10,
    #                             scan_spacing=0.5,
    #                             scan_in_azimuth=True,
    #                             projection='plate-carree')
    return session.raster_scan(target, **kwargs)


def scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Run basic scan observation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    try:
        timestamp = session.time
    except AttributeError:
        timestamp = time.time()
    user_logger.debug("DEBUG: Starting scan across target: {}".format(timestamp))
    user_logger.info("Scan target: {}".format(target))
    return session.scan(target, **kwargs)


def scan_const_el(session, target, nd_period=None, lead_time=None, **kwargs):
    """Run a scan at a constant elevation.

    This is achieved by defining the scan in horizontal (azimuth-elevation)
    coordinates. The center of the scan is the azimuth and elevation of the
    celestial target at the start of the scan. This function reuses the
    generic `scan()` function to perform the telescope movement.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
        The celestial target (e.g., in RA/Dec) to center the scan on.
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time
    **kwargs: dict
        Must contain 'scan_width_radec' (in degrees) and
        'scan_speed_radec' (in arcmin/sec).
    """
    required_params = ['scan_width_radec', 'scan_speed_radec']
    if not all(k in kwargs for k in required_params):
        raise ValueError("Constant elevation scan requires {} in YAML config".format(required_params))

    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)

    scan_width_radec = float(kwargs['scan_width_radec'])  # degrees in RA/Dec
    scan_speed_radec = float(kwargs['scan_speed_radec'])  # arcmin/sec in RA/Dec
    
    # Calculate scan duration in seconds (no elevation conversion needed)
    scan_duration = scan_width_radec / scan_speed_radec * 60

    # Get current time from session if available, else use real time
    try:
        timestamp = session.time
    except AttributeError:
        timestamp = time.time()

    # Try to figure out the target position in az, el
    # Add buffer to account for scan setup delays before telescope starts scanning
    scan_start_buffer = 3.0  # seconds
    scan_mid_ts = timestamp + scan_start_buffer + scan_duration / 2.0
    az_rad, el_rad = target.azel(timestamp=scan_mid_ts)
        
    # Convert RA/Dec width to azimuth width for initial positioning (rough estimate)
    scan_width_az_initial = scan_width_radec / np.cos(el_rad)
    
    # Calculate scan start position (offset from center)
    start_az_offset = -scan_width_az_initial / 2.0
    start_az_rad = katpoint.wrap_angle(az_rad + np.radians(start_az_offset))
    
    # Create target at scan start position for pre-positioning
    scan_start_target = katpoint.construct_azel_target(start_az_rad, el_rad)
    scan_start_target.name = target.name
    scan_start_target.antenna = target.antenna
    
    user_logger.info("Pre-positioning to scan start (Az, El): ({:.2f}, {:.2f}) deg".format(
        np.degrees(start_az_rad), np.degrees(el_rad)))
    
    # Pre-position telescope to scan start with minimal slewing during scan
    target_visible = session.track(scan_start_target, duration=0.0, announce=False)
    if not target_visible:
        user_logger.warning("Scan start position not visible")
        return False
    
    # After slewing, recalculate target position at scan center for actual scan
    try:
        current_timestamp = session.time
    except AttributeError:
        current_timestamp = time.time()
    
    scan_mid_ts = current_timestamp + scan_start_buffer + scan_duration / 2.0
    az_rad, el_rad = target.azel(timestamp=scan_mid_ts)

    # Convert RA/Dec parameters to azimuth using accurate elevation
    scan_width_az = scan_width_radec / np.cos(el_rad)
    scan_speed_az = (scan_speed_radec / 60.0) / np.cos(el_rad)  # Convert arcmin/sec to deg/s

    # Create a new, temporary target fixed in Az/El for the scan.
    azel_target = katpoint.construct_azel_target(az_rad, el_rad)
    azel_target.name = target.name  # Keep the original name for logging
    azel_target.antenna = target.antenna  # Ensure observer is consistent

    user_logger.info("Scan center (Az, El): ({:.2f}, {:.2f}) deg".format(
        np.degrees(az_rad), np.degrees(el_rad)))

    # Calculate scan parameters for the session.scan() call using accurate azimuth width
    start_az_offset = -scan_width_az / 2.0
    end_az_offset = scan_width_az / 2.0

    # Log scan parameters for debugging and testing
    user_logger.info("Scan duration is %.2f s and scan speed is %.2f deg/s", 
                     scan_duration, scan_speed_az)
    user_logger.info("Azimuth scan extent [%.1f, %.1f]", 
                     start_az_offset, end_az_offset)

    # Construct arguments for the underlying scan function.
    # Start with a copy of the input kwargs to preserve other scan options
    # like 'projection' from the YAML file.
    scan_kwargs = kwargs.copy()
    scan_kwargs['duration'] = scan_duration
    scan_kwargs['start'] = (start_az_offset, 0.0)  # (az_offset, el_offset)
    scan_kwargs['end'] = (end_az_offset, 0.0)
    # Clean up keys that are not meant for the core scan function
    for param in required_params:
        scan_kwargs.pop(param, None)
    user_logger.debug("DEBUG: Passing to session.scan: {}".format(scan_kwargs))

    # Call the generic scan function with the new Az/El target and calculated parameters
    return scan(session, azel_target, nd_period=nd_period, lead_time=lead_time, **scan_kwargs)


def multi_scan_target_el(session, target, nd_period=None, lead_time=None, **kwargs):
    """Run multiple scan lines through a target.

    This function performs multiple back-and-forth scan lines, with each scan line
    going through the target position as it moves across the sky. Unlike multi_scan_const_el,
    each scan line will be at a different elevation as the target moves.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
        The celestial target (in RA/Dec) to observe.
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time
    **kwargs: dict
        Must contain 'scan_width_radec' (in degrees), 'scan_speed_radec' (in arcmin/sec),
        and 'num_scan_lines' (integer).
    """
    required_params = ['scan_width_radec', 'scan_speed_radec', 'num_scan_lines']
    if not all(k in kwargs for k in required_params):
        raise ValueError("Multi-scan target elevation requires {} in YAML config".format(required_params))

    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)

    # Extract parameters
    scan_width_radec = float(kwargs['scan_width_radec'])  # degrees in RA/Dec
    scan_speed_radec = float(kwargs['scan_speed_radec'])  # arcmin/sec in RA/Dec
    num_scan_lines = int(kwargs['num_scan_lines'])
    
    # Basic validation
    if num_scan_lines == 0:
        user_logger.warning("Number of scan lines is zero")
        return False

    # Calculate scan duration in seconds (no elevation conversion needed)
    scan_duration = scan_width_radec / scan_speed_radec * 60

    user_logger.info("Planning {} scan lines through target".format(num_scan_lines))
    user_logger.info("Individual scan line duration: {:.2f} s".format(scan_duration))

    # Get current time for initial positioning
    try:
        initial_timestamp = session.time
    except AttributeError:
        initial_timestamp = time.time()

    # Calculate initial target position for first scan pre-positioning
    scan_start_buffer = 3.0  # seconds
    initial_scan_mid_ts = initial_timestamp + scan_start_buffer + scan_duration / 2.0
    az_rad_initial, el_rad_initial = target.azel(timestamp=initial_scan_mid_ts)
    
    # Convert RA/Dec width to azimuth width for initial positioning
    scan_width_az_initial = scan_width_radec / np.cos(el_rad_initial)
    
    # Pre-position telescope to first scan line start position
    start_az_offset_initial = -scan_width_az_initial / 2.0  # Always start west->east
    start_az_rad_initial = katpoint.wrap_angle(az_rad_initial + np.radians(start_az_offset_initial))
    
    scan_start_target = katpoint.construct_azel_target(start_az_rad_initial, el_rad_initial)
    scan_start_target.name = target.name
    scan_start_target.antenna = target.antenna
    
    user_logger.info("Pre-positioning to first scan start (Az, El): ({:.2f}, {:.2f}) deg".format(
        np.degrees(start_az_rad_initial), np.degrees(el_rad_initial)))
    
    target_visible = session.track(scan_start_target, duration=0.0, announce=False)
    if not target_visible:
        user_logger.warning("First scan start position not visible")
        return False

    # Start multi-scan observation
    scan_direction = False  # Start with west->east
    completed_scans = 0

    while completed_scans < num_scan_lines:
        # Recalculate target position for this scan line (target is moving!)
        try:
            current_timestamp = session.time
        except AttributeError:
            current_timestamp = time.time()
        
        # Calculate target position at this scan's middle time
        scan_mid_ts = current_timestamp + scan_start_buffer + scan_duration / 2.0
        az_rad, el_rad = target.azel(timestamp=scan_mid_ts)

        # Convert RA/Dec parameters to azimuth using current elevation
        scan_width_az = scan_width_radec / np.cos(el_rad)

        # Create fixed Az/El target for this scan line
        azel_target = katpoint.construct_azel_target(az_rad, el_rad)
        azel_target.name = target.name
        azel_target.antenna = target.antenna

        # Calculate scan direction for this line
        start_az_offset = -scan_width_az / 2.0 if not scan_direction else scan_width_az / 2.0
        end_az_offset = scan_width_az / 2.0 if not scan_direction else -scan_width_az / 2.0

        # Log scan line info
        direction_str = "East->West" if scan_direction else "West->East"
        user_logger.info("Scan line {}: {} at (Az, El): ({:.2f}, {:.2f}) deg".format(
            completed_scans + 1, direction_str, np.degrees(az_rad), np.degrees(el_rad)))
        user_logger.info("Azimuth scan extent [%.1f, %.1f]", start_az_offset, end_az_offset)

        # Prepare scan parameters
        scan_kwargs = kwargs.copy()
        scan_kwargs['duration'] = scan_duration
        scan_kwargs['start'] = (start_az_offset, 0.0)
        scan_kwargs['end'] = (end_az_offset, 0.0)
        
        # Clean up parameters not meant for core scan function
        for param in required_params:
            scan_kwargs.pop(param, None)

        # Execute the scan line
        line_success = scan(session, azel_target, nd_period=nd_period, lead_time=lead_time, **scan_kwargs)
        
        if line_success:
            completed_scans += 1
            scan_direction = not scan_direction  # Alternate direction for next scan
        else:
            user_logger.warning("Scan line {} failed".format(completed_scans + 1))
            break

    user_logger.info("Multi-scan target completed - {} scan lines executed".format(completed_scans))
    return completed_scans > 0


def multi_scan_const_el(session, target, nd_period=None, lead_time=None, **kwargs):
    """Run multiple scan lines at a constant elevation.

    This function performs multiple back-and-forth scan lines at the same elevation
    while the target naturally drifts through the scan pattern due to sky rotation.
    The target will cross the scan line once when its elevation matches the scan elevation.

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
        The celestial target (in RA/Dec) to observe.
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time
    **kwargs: dict
        Must contain 'obs_duration' (in minutes), 'scan_width_radec' (in degrees),
        and 'scan_speed_radec' (in arcmin/sec).
    """
    required_params = ['obs_duration', 'scan_width_radec', 'scan_speed_radec']
    if not all(k in kwargs for k in required_params):
        raise ValueError("Multi-scan constant elevation requires {} in YAML config".format(required_params))

    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)

    # Extract parameters
    obs_duration_min = float(kwargs['obs_duration'])
    scan_width_radec = float(kwargs['scan_width_radec'])  # degrees in RA/Dec
    scan_speed_radec = float(kwargs['scan_speed_radec'])  # arcmin/sec in RA/Dec

    obs_duration_sec = obs_duration_min * 60.0

    # Calculate scan line duration in seconds
    scan_line_duration = scan_width_radec / scan_speed_radec * 60
    user_logger.info("Individual scan line duration: {:.2f} s".format(scan_line_duration))

    # Calculate how many scan lines we can fit in the observation time
    num_scan_lines = round(obs_duration_sec / scan_line_duration)
    
    # Basic validation
    if num_scan_lines == 0:
        user_logger.warning("Observation duration too short for any complete scan lines")
        return False
    
    # Calculate total scan duration and slew times
    actual_obs_duration_sec = num_scan_lines * scan_line_duration
    actual_obs_duration_min = actual_obs_duration_sec / 60.0
    slew_time_per_scan = 3.2  # seconds
    scans_slew_time = (num_scan_lines - 1) * slew_time_per_scan
    total_scans_duration = actual_obs_duration_sec + scans_slew_time
    
    user_logger.info("Planning {} scan lines over {:.1f} minutes (requested: {:.1f} min)".format(
        num_scan_lines, actual_obs_duration_min, obs_duration_min))

    # Get current time from session if available, else use real time
    try:
        obs_start_timestamp = session.time
    except AttributeError:
        obs_start_timestamp = time.time()

    # First guess at calculating target position in az,el at middle of observation
    # add a 20 sec slew buffer for good measure
    obs_mid_timestamp = 20 + obs_start_timestamp + total_scans_duration / 2.0
    az_mid_rad, el_mid_rad = target.azel(timestamp=obs_mid_timestamp)

    # Convert RA/Dec width to azimuth width using first elevation guess
    # At high elevation, cos(el) -> 0, requiring large azimuth width
    azimuth_width_deg = scan_width_radec / np.cos(el_mid_rad)

    # Pre-position telescope to first scan line start position
    initial_start_az_offset = -azimuth_width_deg / 2.0  # Always start west->east
    initial_start_az_rad = katpoint.wrap_angle(az_mid_rad + np.radians(initial_start_az_offset))
    
    scan_start_target = katpoint.construct_azel_target(initial_start_az_rad, el_mid_rad)
    scan_start_target.name = target.name
    scan_start_target.antenna = target.antenna
    
    user_logger.info("Pre-positioning to first scan start (Az, El): ({:.2f}, {:.2f}) deg".format(
        np.degrees(initial_start_az_rad), np.degrees(el_mid_rad)))
    
    target_visible = session.track(scan_start_target, duration=0.0, announce=False)
    if not target_visible:
        user_logger.warning("First scan start position not visible")
        return False

    # After slewing, recalculate target position at observation middle for all scan lines
    try:
        current_timestamp = session.time
    except AttributeError:
        current_timestamp = time.time()
    
    # Recalculate target at actual observation middle (including slew times). Add 3 sec slew time for good measure
    obs_mid_timestamp_recalc = 3 + current_timestamp + total_scans_duration / 2.0
    az_mid_recalc, el_mid_recalc = target.azel(timestamp=obs_mid_timestamp_recalc)

    user_logger.info("Target at obs middle (Az, El): ({:.2f}, {:.2f}) deg".format(
        np.degrees(az_mid_recalc), np.degrees(el_mid_recalc)))

    # Convert RA/Dec width to azimuth width using final elevation
    azimuth_width_deg = scan_width_radec / np.cos(el_mid_recalc)

    # Convert RA/Dec speed to azimuth speed (arcmin/sec -> deg/s)
    azimuth_speed_deg_per_sec = (scan_speed_radec / 60.0) / np.cos(el_mid_recalc)
    
    user_logger.info("Converted scan width: {:.2f} deg in azimuth".format(azimuth_width_deg))
    user_logger.info("Converted scan speed: {:.2f} deg/s in azimuth".format(azimuth_speed_deg_per_sec))    

    # Create fixed Az/El target for all scan lines using recalculated position
    azel_target = katpoint.construct_azel_target(az_mid_recalc, el_mid_recalc)
    azel_target.name = target.name
    azel_target.antenna = target.antenna

    # Start multi-scan observation
    scan_direction = False  # Start with west->east (like reversescan)
    completed_scans = 0

    while completed_scans < num_scan_lines:
        # Calculate scan direction for this line
        start_az_offset = -azimuth_width_deg / 2.0 if not scan_direction else azimuth_width_deg / 2.0
        end_az_offset = azimuth_width_deg / 2.0 if not scan_direction else -azimuth_width_deg / 2.0

        # Log scan line info
        direction_str = "East->West" if scan_direction else "West->East"
        user_logger.info("Scan line {}: {} at (Az, El): ({:.2f}, {:.2f}) deg".format(
            completed_scans + 1, direction_str, np.degrees(az_mid_recalc), np.degrees(el_mid_recalc)))
        user_logger.info("Azimuth scan extent [%.1f, %.1f]", start_az_offset, end_az_offset)

        # Prepare scan parameters
        scan_kwargs = kwargs.copy()
        scan_kwargs['duration'] = scan_line_duration
        scan_kwargs['start'] = (start_az_offset, 0.0)
        scan_kwargs['end'] = (end_az_offset, 0.0)
        
        # Clean up parameters not meant for core scan function
        for param in required_params:
            scan_kwargs.pop(param, None)

        # Execute the scan line
        line_success = scan(session, azel_target, nd_period=nd_period, lead_time=lead_time, **scan_kwargs)
        
        if line_success:
            completed_scans += 1
            scan_direction = not scan_direction  # Alternate direction for next scan
        else:
            user_logger.warning("Scan line {} failed".format(completed_scans + 1))
            break

    user_logger.info("Multi-scan completed - {} scan lines executed".format(completed_scans))
    return completed_scans > 0



def reference_pointing_scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Perform offset pointings on nearest pointing calibrator.

    Calculate and store pointing offset corrections in telstate

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time
    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    user_logger.info("Reference pointing scan target: {}".format(target))
    return session.reference_pointing_scan(target, **kwargs)


def forwardscan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Forward scan observation.

    Call to `scan` method described in this module

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    target_visible = scan(session,
                          target,
                          nd_period=nd_period,
                          lead_time=lead_time,
                          **kwargs)
    return target_visible


def _get_scan_area_extents(target_list, antenna_, obs_start_ts, offset_deg=0.1):
    """Return the elevation, azimuth extents, and time extents of the scan."""
    antenna = copy.copy(antenna_)
    antenna.observer.date = obs_start_ts
    is_rising_list = []
    el_list = []
    az_list = []
    time_list = []
    for target in target_list:
        _, el = target.azel(timestamp=obs_start_ts)
        el_list.append(el)
        if el < 0:
            user_logger.warning(
                target.name + "is below the horizon (%s deg at %s)", el, obs_start_ts
            )
    user_logger.debug('Min elevation of scan area at start: %s', min(el_list))
    user_logger.debug('Max elevation of scan area at start: %s', max(el_list))

    el_just_below_lowest = min(el_list) - np.radians(_HORIZON_ANGLE_OFFSET_DEG)
    antenna.observer.horizon = el_just_below_lowest
    for target in target_list:
        next_transit = antenna.observer.next_transit(target.body)
        next_setting = antenna.observer.next_setting(target.body)
        next_rising = antenna.observer.next_rising(target.body)
        is_rising = next_transit < next_setting < next_rising
        is_rising_list.append(is_rising)
        user_logger.debug("Is Target rising :%s, %s" % (target.body, is_rising))

    if all(is_rising_list):
        # Rising sources
        antenna.observer.horizon = max(el_list) + np.radians(offset_deg)  # top point
        user_logger.debug('Highest elevation for rising source: %s', max(el_list))
        for target in target_list:
            antenna.observer.next_rising(target.body)  # rise through the scan line
            az_list.append(target.body.rise_az)
            time_list.append(target.body.rise_time)
    else:
        antenna.observer.horizon = min(el_list) - np.radians(offset_deg)  # bottom point
        user_logger.debug('Lowest elevation for setting source: %s', min(el_list))
        for target in target_list:
            antenna.observer.next_setting(target.body)  # Set through the scan line
            az_list.append(target.body.set_az)
            time_list.append(target.body.set_time)
    min_time = katpoint.Timestamp(min(time_list))
    max_time = katpoint.Timestamp(max(time_list))
    user_logger.debug(
        "Scan Area Points: el: %s, az: %s %s, time: %s %s",
        antenna.observer.horizon,
        min(az_list), max(az_list),
        min_time, max_time,
    )
    return (
        antenna.observer.horizon,
        min(az_list), max(az_list),
        min_time, max_time,
    )


def reversescan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Reverse scan observation.

    This scan is done in "Reverse"
    This means that it is given an area to scan (via kwargs)
    rather that a target and parameters

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # trigger noise diode if set
    trigger(session.kat, duration=nd_period, lead_time=lead_time)
    if 'radec_p1' in kwargs and 'radec_p2' in kwargs:
        # means that there is a target area
        # find lowest setting part or
        # highest rising part
        antenna = copy.copy(target.antenna)
        target_list = []
        for i in range(1, _MAX_POINTS_IN_SCAN_AREA_POLYGON + 1):
            key = 'radec_p%i' % i
            if key in kwargs:
                target_list.append(
                    katpoint.Target(
                        't%i,radec,%s' % (i, kwargs[key]),
                        antenna=target.antenna,
                    )
                )
    else:
        user_logger.error("No scan area defined - require radec_p1 and radec_p2")
        return False
    direction = kwargs.get("direction", False)
    scan_speed = kwargs.get("scan_speed", _DEFAULT_SCAN_SPEED_ARCMIN_PER_SEC)

    obs_start_ts = katpoint.Timestamp(time.time()).to_ephem_date()
    # use 1 deg offset to pre-position >4 min in the future to take into account slewing
    el, az_min, az_max, t_start, t_end = _get_scan_area_extents(target_list, antenna,
                                                                obs_start_ts,
                                                                offset_deg=1)

    # TODO: get horizon limit from observation - may want to pass limits of
    #       the "acceptable elevation extent" into _get_scan_area_extents.
    if _MIN_HORIZON_EL_FOR_SCAN_DEG > np.degrees(el):
        user_logger.warning(
            "Source and scan below horizon: %s < %s",
            np.degrees(el),
            _MIN_HORIZON_EL_FOR_SCAN_DEG,
        )
        return False

    scan_target = katpoint.construct_azel_target(katpoint.wrap_angle(az_min), el)
    scan_target.name = target.name
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    scan_target.antenna = antenna
    scan_target.antenna.observer.date = obs_start_ts
    user_logger.info("Slew to scan start")  # slew to target.
    target_visible = session.track(scan_target, duration=0.0, announce=False)
    if not target_visible:
        user_logger.warning(
            "Start of scan is not visible!  Elevation: %.1f deg.", np.degrees(el)
        )
        return False

    # This is the real scan
    obs_start_ts = katpoint.Timestamp(time.time()).to_ephem_date()
    el, az_min, az_max, t_start, t_end = _get_scan_area_extents(target_list, antenna,
                                                                obs_start_ts)
    scan_target = katpoint.construct_azel_target(
        katpoint.wrap_angle((az_min + az_max) / 2.), el)
    scan_target.name = target.name
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    scan_target.antenna = antenna
    scan_target.antenna.observer.date = obs_start_ts

    scan_start = np.degrees(az_min - (az_min + az_max) / 2.)
    scan_end = np.degrees(az_max - (az_min + az_max) / 2.)

    scanargs = {}
    if "projection" in kwargs:
        scanargs["projection"] = kwargs["projection"]

    # take into account projection effects of the sky and convert to degrees per second
    # E.g., 5 arcmin/s should translate to 5/60/cos(el) deg/s
    scan_speed = (scan_speed / 60.0) / np.cos(el)
    scanargs["duration"] = abs(scan_start - scan_end) / scan_speed  # Duration in seconds
    user_logger.info(
        "Scan duration is %.2f and scan speed is %.2f deg/s",
        scanargs["duration"], scan_speed
    )
    user_logger.info("Start Time: %s", t_start)
    user_logger.info("End Time: %s", t_end)
    num_scan_lines = 0
    while time.time() <= t_end.secs:
        if direction:
            scanargs["start"] = scan_start, 0.0
            scanargs["end"] = scan_end, 0.0
        else:
            scanargs["start"] = scan_end, 0.0
            scanargs["end"] = scan_start, 0.0
        user_logger.info("Azimuth scan extent [%.1f, %.1f]" %
                         (scanargs["start"][0], scanargs["end"][0]))
        target_visible = scan(session,
                              scan_target,
                              nd_period=nd_period,
                              lead_time=lead_time,
                              **scanargs)
        direction = not direction
        if target_visible:
            num_scan_lines += 1
    user_logger.info("Scan completed - %s scan lines", num_scan_lines)
    return num_scan_lines > 0


def return_scan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Return scan observation.

    A temporary fix until raster scan can be fixed

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    # set up 2way scan
    user_logger.info("Forward scan over target")
    target_visible = scan(session,
                          target,
                          nd_period=nd_period,
                          lead_time=lead_time,
                          **kwargs)

    user_logger.info("Reverse scan over target")
    returnscan = dict(kwargs)
    returnscan["start"] = kwargs["end"]
    returnscan["end"] = kwargs["start"]
    target_visible &= scan(session,
                           target,
                           nd_period=nd_period,
                           lead_time=lead_time,
                           **returnscan)
    return target_visible


# -fin-
