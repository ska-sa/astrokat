#!/usr/bin/env python
"""Theoretical UV coverage from antenna position"""

from __future__ import print_function
from astropy import units as u
from astropy.coordinates import Longitude, Latitude, EarthLocation
from numpy import recarray

import argparse
import astropy.constants as phys
import matplotlib.pyplot as plt
import numpy as np
import sys
import yaml

from astrokat import __version__


class Interferometer(object):
    def __init__(self,
                 configuration_file,
                 centre_freq=1420e6,  # Hz
                 ):
        self.frequency = centre_freq / u.s
        self.wavelength = phys.c / self.frequency

        self.ref_position = None
        arr_desc = {'names': ('name', 'north', 'east', 'up', 'location'),
                    'formats': ('S5', float, float, float, EarthLocation)}
        self.antennas = recarray((0,), dtype=arr_desc)

        array_config = self.read_config(configuration_file)
        if 'reference' in array_config.keys():
            self._set_reference_(array_config['reference'])
        self._build_array_(array_config['antennas'])

        # function to update with only selected antennas

        # number of antennas
        self.nr_antennas = len(self.antennas)
        # number pair or baseline
        self.nr_baselines = (self.nr_antennas * (self.nr_antennas - 1)) // 2

    def read_config(self, filename):
        """Read array default .yaml file."""
        with open(filename, "r") as stream:
            data = yaml.safe_load(stream)
        return data

    def __return_value__(self, prefix, item):
        if item.startswith(prefix):
            return item.split('=')[-1].strip()
        else:
            return None

    def _set_reference_(self, ref_position):
        """General Earth position for the Telescope"""
        ref_LAT = Latitude(ref_position['latitude'],
                           u.degree,
                           copy=False)
        ref_LON = Longitude(ref_position['longitude'],
                            u.degree,
                            wrap_angle=180. * u.degree,
                            copy=False)
        ref_ALT = u.Quantity(ref_position['altitude'],
                             u.m,
                             copy=False)
        self.ref_position = EarthLocation(lat=ref_LAT,
                                          lon=ref_LON,
                                          height=ref_ALT)

    def _build_array_(self, antennas):
        """ENU coordinates per antenna"""
        if self.ref_position is not None:
            [x, y, z] = self.ref_position.to_geocentric()

        self.antennas.resize(len(antennas))
        for cnt, antenna in enumerate(antennas):
            ant_ = [item.strip() for item in antenna.split(",")]
            for item_ in ant_:
                for prefix_ in ('name', 'north', 'east', 'up'):
                    val_ = self.__return_value__(prefix_, item_)
                    if val_ is not None:
                        self.antennas[cnt][prefix_] = val_
            if self.ref_position is not None:
                ant_North = x.value + self.antennas[cnt]['north']
                ant_East = y.value + self.antennas[cnt]['east']
                ant_Up = z.value + self.antennas[cnt]['up']
                self.antennas[cnt]['location'] = EarthLocation(x=ant_North * u.m,
                                                               y=ant_East * u.m,
                                                               z=ant_Up * u.m)

    def baselines(self):
        """The function evaluates baselines lenghts
           and the angle between antennas
        """
        P = np.array([self.antennas['north'],
                      self.antennas['east']]).T
        # antenna position in wavelength units
        P /= self.wavelength  # baseline

        bl_length = np.zeros((self.nr_baselines, ))
        bl_az_angle = np.zeros((self.nr_baselines, ))
        cnt = 0
        for idx0 in range(self.nr_antennas):
            for idx1 in range(idx0 + 1, self.nr_antennas):
                bl_length[cnt] = np.sqrt((P[idx0, 0] - P[idx1, 0])**2
                                         + (P[idx0, 1] - P[idx1, 1])**2)
                bl_az_angle[cnt] = np.arctan2((P[idx0, 1] - P[idx1, 1]),
                                              (P[idx0, 0] - P[idx1, 0]))
                cnt += 1

        return bl_length, bl_az_angle


class UVplot(object):
    def __init__(self,
                 latitude,
                 declination,
                 elevation):
        self.lat = latitude
        self.dec = declination
        self.elev = elevation

    def __baseline_to_xyz__(self,
                            baseline_lengths,
                            baseline_azimuth):
        """The following function transform baseline to x,y,z coordinates
            elevation: Elevation angle in radian
            The result is a vector of (x,y,z) with unit the same as baseline length
            Interferometry and Synthesis in Radio Astronomy, Chapter 4, Equation 4.4
        """
        x = (np.cos(self.lat) * np.sin(baseline_azimuth)
             - np.sin(self.lat) * np.cos(baseline_azimuth) * np.cos(self.elev))
        y = np.cos(baseline_azimuth) * np.sin(self.elev)
        z = (np.sin(self.lat) * np.sin(baseline_azimuth)
             + np.cos(self.lat) * np.cos(baseline_azimuth) * np.cos(self.elev))
        xyz = np.array([(x, y, z)])
        return baseline_lengths * xyz.T

    def __xyz_to_baseline__(self,
                            hour_angle):
        """Transform x, y, z to u, v, w components
           hour_angle: Source hour angle in radians
           dec: Source declination in radian
           Interferometry and Synthesis in Radio Astronomy, Chapter 4, Equation 4.1
        """
        a1 = np.sin(hour_angle)
        a2 = np.cos(hour_angle)
        a3 = 0.

        b1 = -1 * np.sin(self.dec) * np.cos(hour_angle)
        b2 = np.sin(self.dec) * np.sin(hour_angle)
        b3 = np.cos(self.dec)

        c1 = np.cos(self.dec) * np.cos(hour_angle)
        c2 = -1 * np.cos(self.dec) * np.sin(hour_angle)
        c3 = np.sin(self.dec)

        return np.array([(a1, a2, a3),
                         (b1, b2, b3),
                         (c1, c2, c3)])

    def track_uv(self,
                 ha_range,
                 bl_length,
                 bl_azimuth,
                 timeslots):
        """Evaluate the track of a single antenna pair
           The function return a set of u,v,w components
        """
        uvw = np.zeros((timeslots, 3), dtype=float)
        for i in range(timeslots):
            uvw[i, :] = np.dot(self.__xyz_to_baseline__(ha_range[i]),
                               self.__baseline_to_xyz__(bl_length,
                                                        bl_azimuth)).T
        return uvw

    def uvMask(self,
               ha_range,
               bl_length,
               bl_azimuth,
               timeslots,
               maxsize,
               uvscaling):
        maskmat = np.zeros((maxsize, maxsize))
        uvw = self.track_uv(ha_range,
                            bl_length,
                            bl_azimuth,
                            timeslots)
        sctrl = maxsize // 2 + 1
        for i in range(timeslots):
            maskmat[sctrl + int(np.ceil(uvw[i, 0] * uvscaling)),
                    sctrl + int(np.ceil(uvw[i, 1] * uvscaling))] = 1.
            maskmat[sctrl - int(np.ceil(uvw[i, 0] * uvscaling)),
                    sctrl - int(np.ceil(uvw[i, 1] * uvscaling))] = 1.
        return maskmat

    def plot_uv(self,
                ha_range,
                bl_length,
                bl_azimuth,
                timeslots,
                comment=''):
        """UV coverage graph"""
        nr_baselines = len(bl_length)
        fig, ax = plt.subplots(nrows=1, ncols=1,
                               figsize=(20, 13),  # W x H
                               facecolor='white')
        for i in range(nr_baselines):
            uv = self.track_uv(ha_range,
                               bl_length[i],
                               bl_azimuth[i],
                               timeslots)
            ax.plot(uv[:, 0], uv[:, 1], 'b.', markersize=2)
            ax.plot(-uv[:, 0], -uv[:, 1], 'r.', markersize=2)
        ax.set_xlabel('u')
        ax.set_ylabel('v')
        ax.set_title('Declination {} deg: UV coverage'
                     .format(comment))
        return fig, ax

    def plot_mask(self,
                  mask,
                  psf,
                  comment=''):
        """Display simulated beamshape"""
        fig, ax = plt.subplots(nrows=1, ncols=2,
                               figsize=(20, 13),  # W x H
                               facecolor='white')
        ax[0].imshow(mask)
        [nr, nc] = np.shape(mask)
        ax[0].set_xlim(0.5 * nr - 0.25 * nr,
                       0.5 * nr + 0.25 * nr)
        ax[0].set_ylim(0.5 * nc - 0.25 * nc,
                       0.5 * nc + 0.25 * nc)
        ax[0].set_xlabel('u')
        ax[0].set_ylabel('v')
        ax[0].set_title('uv coverage, "%s"' % comment)

        ax[1].imshow(psf,
                     interpolation='gaussian',
                     origin='lower',
                     vmin=psf.min() / 1000.,
                     vmax=psf.max())
        [nr, nc] = np.shape(psf)
        ax[1].set_xlim(0.5 * nr - 0.25 * nr,
                       0.5 * nr + 0.25 * nr)
        ax[1].set_ylim(0.5 * nc - 0.25 * nc,
                       0.5 * nc + 0.25 * nc)
        ax[1].set_xlabel('u')
        ax[1].set_ylabel('v')
        ax[1].set_title('psf, "%s"' % comment)

        return fig, ax


def Gauss(npix, FWHM):
    """Gaussian Kernel for tapering given FWHM"""
    n = npix // 2
    scale = -1 / (2 * FWHM**2)
    G = np.zeros((npix, npix))
    for i in range(npix):
        for j in range(npix):
            G[i][j] = np.exp(scale * ((i - n)**2 + (j - n)**2))
    return G


def cli(prog):
    usage = "{} [options]".format(prog)
    description = 'UV coverage calculator for MeerKAT telescope'

    parser = argparse.ArgumentParser(
        usage=usage,
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=__version__)
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='MeerKAT antenna positions YAML')
    parser.add_argument(
        '--time',
        dest='ntimeslots',
        type=int,
        default=300,
        help='Number of time slots equally distributed over 8 hours')
    parser.add_argument(
        '--dec',
        dest='declination',
        type=float,
        default=-90,
        help='Pointing declination in degrees')
    # parser.add_argument('--sub',
    #                   action='store',
    #                   dest='subarray',
    #                   type=str,
    #                   default='mkat',
    #                   help='Name of subarray as defined in config')
    parser.add_argument(
        '--natural',
        action="store_true",
        default=False,
        help="UV mask and synthesize beam, "
             "natural weighting without a taper")
    parser.add_argument(
        '--save',
        action="store_true",
        default=False,
        help="Save graphs to PNG format")
    parser.add_argument(
        '-v', "--verbose",
        action="store_true",
        default=False,
        help="Display intermittend results and all graphs")
    args = parser.parse_args()
    return args


def main(args):
    # number of time slots
    ntimeslots = args.ntimeslots
    # declination convert in radian
    dec = np.radians(args.declination)
    # hour angle range in hours given nr of timeslots
    ha_range = np.linspace(-4., 4., ntimeslots) * np.pi / 12.

    mkat = Interferometer(args.config,
                          centre_freq=1420e6)
    latitude = mkat.ref_position.geodetic[1].radian

    if args.verbose:
        print('MeerKAT telescope location')
        print(mkat.ref_position.geodetic)
        print('latitude {:.3f} [rad]'.format(latitude))
        print('UV coverage @ decl={:.3f} [rad]'.format(dec))
        # print(ha_range)

    # baseline lengths and azimuth angles
    [bl_length,
     bl_az_angle] = mkat.baselines()

    # Plot the uv-Coverage
    uvplot = UVplot(latitude=latitude,
                    declination=dec,
                    elevation=0.)

    fig, ax = uvplot.plot_uv(ha_range,
                             bl_length,
                             bl_az_angle,
                             ntimeslots)
    uv = uvplot.track_uv(ha_range=ha_range,
                         bl_length=bl_length[-1],
                         bl_azimuth=bl_az_angle[-1],
                         timeslots=ntimeslots)
    mb = 5 * np.sqrt((uv**2).sum(1)).max()
    ax.set_xlim(-mb, mb)
    ax.set_ylim(-mb, mb)
    plt.axis('equal')
    plt.gca().invert_xaxis()
    if args.save:
        # plt.savefig('%s_uv_coverage_%d.png'%(opts.subarray,int(opts.declination)))
        filename = ('mkat_uv_coverage_dec{:.0f}.png'
                    .format(args.declination))
        print(filename)
        # plt.savefig(filename)

    # Show UV mask and synthesize beam, natural weighting without a taper
    # number of pixels
    npix = 2**10  # should be a power of two
    # kernel matrix
    mask = np.zeros((npix, npix))
    # uv-grid scale factor to fit tracks into matrix
    uvscale = npix / 2 / mb * 0.95 * 0.5
    for i in range(mkat.nr_baselines):
        mask = mask + uvplot.uvMask(ha_range,
                                    bl_length[i],
                                    bl_az_angle[i],
                                    ntimeslots,
                                    npix,
                                    uvscale)
    psf = np.fft.ifftshift(np.fft.ifft2(mask.T)).real
    if args.natural:
        uvplot.plot_mask(mask.T, psf, comment="natural weighting")
        if args.save:
            # filename = '%s_natural_weighting_%d.png' % (opts.subarray,int(opts.declination))
            filename = ('mkat_natural_weighting_dec{:.0f}.png'
                        .format(args.declination))
            print(filename)
            # plt.savefig(filename)

# # Show UV mask and synthesize beam, natural weighting with Gaussian taper
    # gauss_kernel = Gauss (npix, npix/20.)
    # psf = np.fft.ifftshift(np.fft.ifft2(gauss_kernel*(mask.T))).real
# #     # plot the mask
# #     filename = None
# #     if opts.savegraph: filename = '%s_tapered_gaussian_weighting_%d.png'%(opts.subarray,int(opts.declination))
    # uvplot.plot_mask(gauss_kernel*mask.T, psf, comment="tapered Gaussian weighting")
    #     if filename is not None: plt.savefig(filename)


if __name__ == '__main__':

    args = cli(sys.argv[0])
    main(args)
    if args.verbose:
        plt.show()

# -fin-
