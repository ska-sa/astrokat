"""Scan observations."""
from __future__ import division
from __future__ import absolute_import

import katpoint

from .noisediode import trigger

import time

try:
    from katcorelib import user_logger
except ImportError:
    from .simulate import user_logger


def drift_pointing_offset(target, duration=60.0):
    """Drift pointing offset observation.

    Parameters
    ----------
    target: katpoint.Target
    duration: float

    """
    obs_start_ts = target.antenna.observer.date
    transit_time = obs_start_ts + duration / 2.0
    # Stationary transit point becomes new target
    antenna = target.antenna
    az, el = target.azel(timestamp=transit_time)
    target = katpoint.construct_azel_target(katpoint.wrap_angle(az), el)
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    target.antenna = antenna
    target.antenna.observer.date = obs_start_ts
    return target


def drift_scan(session, target, duration=60.0, nd_period=None, lead_time=None):
    """Drift scan observation.

    Parameters
    ----------
    session: `CaptureSession`
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
    target = drift_pointing_offset(target, duration=duration)
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

def scan_area(target_list,antenna_,offset_deg=0.1):
    import copy
    import numpy as np
    #returns elevation and the azimuth extents of the scan
    antenna = copy.copy(antenna_ )
    print(antenna.observer.date)
    results = []
    alt = []
    az = []
    time_end = []
    for i,tar in enumerate(target_list):
        alt.append(tar.azel()[1]) # should this be time.time()
        if tar.body.alt < 0 : 
            print(tar.name + "is below the horizon")
    antenna.observer.horizon = min(alt)-np.radians(2.) # just a little below the lowest point
    print('Min alt',min(alt))
    print('Max alt',max(alt))
    for i,tar in enumerate(target_list):
        rising = antenna.observer.next_transit(tar.body)  < antenna.observer.next_setting(tar.body) < antenna.observer.next_rising(tar.body) 
        print("Target:%s, %s"%(tar.body,rising))
        results.append(rising)
    print("Rising::",results)
    if np.all(results):
        #return True # rising
        antenna.observer.horizon = max(alt)+np.radians(offset_deg)#top point
        print('Rising loop Max alt',max(alt))
        for i,tar in enumerate(target_list):
            antenna.observer.next_rising(tar.body) # rise through the scan line
            az.append(tar.body.rise_az) 
            time_end.append(tar.body.rise_time)
            print("Rise loop",tar.body.rise_az,tar.body.alt)
        print("Scan Points",tar.body.alt,min(az),max(az),min(time_end),max(time_end))
    else: 
        antenna.observer.horizon = min(alt)-np.radians(offset_deg)#bottom point
        print('Setting loop Min alt',min(alt),max(alt))
        for i,tar in enumerate(target_list):
            antenna.observer.next_setting(tar.body) # set through the scan line
            az.append(tar.body.set_az)
            time_end.append(tar.body.set_time)
            print("Set loop",tar.body.set_az,tar.body.alt)
        print("Scan Points",tar.body.alt,min(az),max(az),min(time_end),max(time_end) )
    return tar.body.alt,min(az),max(az),min(time_end),max(time_end) 


def reversescan(session, target, nd_period=None, lead_time=None, **kwargs):
    """Reverse scan observation.

    This scan is done in "Reverse"
    This means that it is given an area to scan
    rather that a target an parameters

    Parameters
    ----------
    session: `CaptureSession`
    target: katpoint.Target
    nd_period: float
        noisediode period
    lead_time: float
        noisediode trigger lead time

    """
    import numpy as np
    import copy
    import datetime
    # trigger noise diode if set
    trigger(session.kat, session, duration=nd_period)
    scanargs = dict(kwargs)
    if 'radec_p1'  in kwargs.keys() and 'radec_p2'  in kwargs.keys():  # means that there is a target area
        # find lowest setting part or
        # higest rising part
        antenna = copy.copy(target.antenna )#.observer.horizon \
        tar = []
        for i in range(10):
            if 'radec_p%i'%(i) in kwargs.keys():
                tar.append(katpoint.Target('t%i,radec,%s'%(i,kwargs["radec_p%i"%(i)]),antenna=target.antenna ))
                del(scanargs['radec_p%i'%(i)])
    else:
        user_logger.error("No scan area defined")
        return False
    direction = False
    if 'direction'  in kwargs.keys():
        direction = True
        del(scanargs['direction'])
    if 'scan_speed'  in kwargs.keys():
        scan_speed = kwargs['scan_speed']
        del(scanargs['scan_speed'])
    el,az_min,az_max,t_start,t_end = scan_area(tar ,antenna,offset_deg=1)   # pre-position >4 min in the future
    if 15.0 > np.degrees(el) :
        user_logger.warning("Source and scan below horison ")
        return False
    obs_start_ts = target.antenna.observer.date
    scan_target = katpoint.construct_azel_target(katpoint.wrap_angle(az_min), el)
    scan_target.name = target.name  # make a nice name
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    scan_target.antenna = antenna
    scan_target.antenna.observer.date = obs_start_ts
    user_logger.info("Slew to scan start")
    target_visible = session.track(scan_target, duration=0.0, announce=False) # slew to target.

    el,az_min,az_max,t_start,t_end = scan_area(tar ,antenna)  # True scan # need to add 1/2 of duration to start.

    obs_start_ts = target.antenna.observer.date
    scan_target = katpoint.construct_azel_target(katpoint.wrap_angle( (az_min+az_max)/2.), el)
    scan_target.name = target.name  # make a nice name
    # katpoint destructively set dates and times during calculation
    # restore datetime before continuing
    scan_target.antenna = antenna
    scan_target.antenna.observer.date = obs_start_ts

    scan_start = np.degrees(az_min-(az_min+az_max)/2.)
    scan_end = np.degrees(az_max-(az_min+az_max)/2.)

    
    scanargs["start"] = scan_start,0.0
    scanargs["end"] = scan_end,0.0
    # 5 arcmin/s if possible so that should translate to 5/cos(el)
    scan_speed = (scan_speed/60.0)/np.cos(el) # take into accout projection effects of the sky and convert to degrees per second
    print("elevation = ",el)
    scanargs["duration"] =abs(scan_start-scan_end)/scan_speed # Duration in seconds.
    target_visible = False
    
    while time.time() <=  (float(t_end.datetime().strftime('%s')) - float(datetime.datetime(1970,1,1).strftime('%s')) ):  # t_end.datetime().timestamp() : 
        if direction :
            scanargs["start"] = scan_start,0.0
            scanargs["end"] = scan_end,0.0
            user_logger.info("Scan extent  %s , %s "%(scanargs["start"][0],scanargs["end"][0]) )
            target_visible += scan(session,
                                   scan_target, 
                                   nd_period=nd_period,
                                   lead_time=lead_time, 
                                   **scanargs)
            direction = False
        else :
            scanargs["start"] = scan_end,0.0
            scanargs["end"] = scan_start,0.0
            user_logger.info("Scan extent  %s , %s "%(scanargs["start"][0],scanargs["end"][0]) )
            target_visible += scan(session,
                                   scan_target, 
                                   nd_period=nd_period,
                                   lead_time=lead_time, 
                                   **scanargs)
            direction = True
    return target_visible


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
    target_visible += scan(session,
                           target,
                           nd_period=nd_period,
                           lead_time=lead_time,
                           **returnscan)
    return target_visible


# -fin-
