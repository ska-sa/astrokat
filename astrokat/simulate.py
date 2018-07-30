# Scripts that can be run independently of the observation system to allow easy observation planning
import katpoint
import numpy as np
import ephem

from .utility import NotAllTargetsUpError

# Use katpoint to add targets to MeerKAT catalogue
def build_cat(targets=[], catalogues=[]):
    catalogue = katpoint.Catalogue()
    catalogue.antenna = katpoint.Antenna('ref, -30:42:47.4, 21:26:38.0, 1060.0, 0.0, , , 1.15')
    for cat in catalogues:
        catalogue.add(file(cat))
    catalogue.add(targets)
    return catalogue


# Verify all targets are above the horizon
def all_up(targets, horizon=20.):
    if len(targets) != len(targets.filter(el_limit_deg=horizon)):
        mask = np.array([np.degrees(target.azel()[1]) for target in targets]) < horizon
        the_list = [target.name for target in np.asarray(targets)[mask]]
        msg = 'Target(s) below horizon %d [deg] (%s)' % (horizon, ','.join(the_list))
        raise NotAllTargetsUpError(msg)


# Display basic rise and set information per target
def visible(targets, horizon=20.):
    observer = targets.antenna.observer
    observer.horizon = np.deg2rad(horizon)
    observer.date = ephem.now()
    
    print 'Reference observer location (lat, lon) = (%s, %s)' % (observer.lat, observer.lon)
    for target in targets:
        source = target.body
        source.compute(observer)
        print source
        print 'Observation target %s' % target.name
        try:
            print '\t Rising %s' % observer.next_rising(source)
            print '\t Setting %s' % observer.next_setting(source)
        except ephem.AlwaysUpError:
            print '\t Always up'
	except:
            if np.degrees(target.body.el) >= horizon:
                 print '\t Target visibile'
            else:
                 print '\t Target below horizon %d' % horizon


# Use observation options to simulate observation plan
def plan_observation(opts):
    print 'Observation planning output'
    # Load targets for observation
    targets = [item.strip().replace(' ','') for sublist in opts.target for item in sublist]
    catalogues = [file_ for sublist in opts.catalogue for file_ in sublist]
    targets = build_cat(targets=targets, catalogues=catalogues)

    # Display target visibility information
    if opts.visibility:
        visible(targets, horizon=opts.horizon)
	return

    # Check that all targets are above the horizon
    if opts.all_up:
        all_up(build_cat(targets), horizon=opts.horizon)

    
