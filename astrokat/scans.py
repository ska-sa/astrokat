# flake8: noqa
import katpoint
import noisediode
libnames = ['user_logger']
try:
    lib = __import__('katcorelib', globals(), locals(), libnames, -1)
except ImportError:
    lib = __import__('simulate', globals(), locals(), libnames, -1)
finally:
    for libname in libnames:
        globals()[libname] = getattr(lib, libname)


def drift_pointing_offset(target, duration=60.):
    try:
        obs_start_ts = target.antenna.observer.date
    except:
        obs_start_ts = katpoint.Timestamp()
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

def drift_scan(session, target, nd_period=None, duration=60.):
    # trigger noise diode if set
    noisediode.trigger(session.kat, duration=nd_period)
    target = drift_pointing_offset(target, duration=duration)
    user_logger.info('Drift_scan observation for {} sec'.format(
        duration))
    return session.track(target, duration=duration)


def raster_scan(session, target, nd_period=None, **kwargs):
    # trigger noise diode if set
    noisediode.trigger(session.kat, duration=nd_period)
# TODO: ignoring raster_scan, not currently working robustly
# TODO: there are errors in raster scan calculations, need some review
#         session.raster_scan(target,num_scans=2,
#                                 scan_duration=120,
#                                 scan_extent=10,
#                                 scan_spacing=0.5,
#                                 scan_in_azimuth=True)#,
#                                 #projection='plate-carree')
    return session.raster_scan(target, **kwargs)


def scan(session, target, nd_period=None, **kwargs):
    # trigger noise diode if set
    noisediode.trigger(session.kat, duration=nd_period)
        # session.label('scan')
        # user_logger.error(obs_type)
        # if 'return' in obs_type:
        #     forwardscan = dict(kwargs['scan'])
        #     returnscan = dict(kwargs['scan'])
        #     print 'forward', forwardscan
        #     print 'return', returnscan
        #     returnscan['start']=kwargs['scan']['end']
        #     returnscan['end']=kwargs['scan']['start']
        #     print 'forward', forwardscan
        #     print 'return', returnscan
        #     target_visible = session.scan(target, **forwardscan)
        #     target_visible = session.scan(target, **returnscan)
    return session.scan(target, **kwargs)


# temporary fix until raster scan can be fixed
def return_scan(session, target, nd_period=None, **kwargs):
    # set up 2way scan
    forwardscan = dict(kwargs)
    returnscan = dict(kwargs)
    returnscan['start']=kwargs['end']
    returnscan['end']=kwargs['start']

    user_logger.info('Forward scan over target')
    target_visible = scan(session,
            target,
            nd_period=nd_period,
            **forwardscan)

    user_logger.info('Reverse scan over target')
    target_visible += scan(session,
            target,
            nd_period=nd_period,
            **returnscan)
    return target_visible


# -fin-
