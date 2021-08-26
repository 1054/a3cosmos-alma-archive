#!/usr/bin/env python
# 
# 20190503

import os, sys, re, copy, datetime
import warnings
warnings.simplefilter("ignore")
import numpy as np
import astropy
import astropy.io.fits as fits
from astropy.table import Table
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS


# Read user input
input_fits_file = ''
input_channel_numbers = []
c30 = 2.99752458e5 # speed of light in units of km/s
arg_str = ''
arg_mode = ''
for i in range(1,len(sys.argv)):
    # 
    # The first arg is input_fits_file
    if input_fits_file == '':
        input_fits_file = sys.argv[i]
        continue
    # 
    # All other args are channel numbers
    input_channel_numbers.append(int(sys.argv[i]))
    

# Check user input
if input_fits_file == '' or len(input_channel_numbers) == 0:
    print('Usage:')
    print('    alma_fits_image_cube_convert_channel_number_to_velocity.py INPUT_FITS_IMAGE_CUBE.fits 100 120 135 145')
    print('Note:')
    print('    This code will convert input channel numbers to velocities using the coordinate system in the input fits image cube.')
    print('')
    sys.exit()


# def get_reffreq
def get_reffreq_GHz(hdu0_header, conv_GHz):
    if 'REFFREQ' in hdu0_header: 
        reffreq_GHz = float(hdu0_header['REFFREQ']) * conv_GHz
        #print('Using the REFFREQ value %s GHz in the fits header!'%(reffreq_GHz))
    elif 'RESTFREQ' in hdu0_header: 
        reffreq_GHz = float(hdu0_header['RESTFREQ']) * conv_GHz
        #print('Using the RESTFREQ value %s GHz in the fits header!'%(reffreq_GHz))
    elif 'RESTFRQ' in hdu0_header: 
        reffreq_GHz = float(hdu0_header['RESTFRQ']) * conv_GHz
        #print('Using the RESTFRQ value %s GHz in the fits header!'%(reffreq_GHz))
    else:
        reffreq_GHz = np.nan
    return reffreq_GHz


# Open fits file and extract the spectrum
with fits.open(input_fits_file) as hdulist:
    # 
    #print(hdulist.info())
    hdu0 = hdulist[0]
    # 
    # check dimension
    if len(hdu0.data.shape) < 3:
        print('Error! The input fits file "%s" is not a data cube! Exit!'%(input_fits_file))
        sys.exit()
    # 
    cenx = ((hdu0.header['NAXIS1']+1.0)/2.0) # 1-based
    ceny = ((hdu0.header['NAXIS2']+1.0)/2.0) # 1-based
    
    
    # now calculate the 3rd axis coordinate
    wcs3 = WCS(hdu0.header)
    #astropy.wcs.utils.pixel_to_skycoord(xp, yp, wc)
    pixcoord3d = np.zeros((len(input_channel_numbers),len(hdu0.data.shape))) # pairs of x,y,freq
    pixcoord3d[:,0] = cenx
    pixcoord3d[:,1] = ceny
    pixcoord3d[:,2] = input_channel_numbers
    skycoord3d = wcs3.wcs_pix2world(pixcoord3d, 1) # 1-based
    skycoord3 = skycoord3d[:,2]
    
    # 
    if hdu0.header['CTYPE3'].strip().lower().startswith('freq'):
        
        if hdu0.header['CUNIT3'].strip().lower().startswith('hz'):
            conv_GHz = 1.0 / 1e9
        elif hdu0.header['CUNIT3'].strip().lower().startswith('khz'):
            conv_GHz = 1.0 / 1e6
        elif hdu0.header['CUNIT3'].strip().lower().startswith('mhz'):
            conv_GHz = 1.0 / 1e3
        elif hdu0.header['CUNIT3'].strip().lower().startswith('ghz'):
            conv_GHz = 1.0
        else:
            conv_GHz = 1.0
        
        freq_GHz = skycoord3 * conv_GHz
        
        reffreq_GHz = get_reffreq_GHz(hdu0.header, conv_GHz)
        
        if np.isnan(reffreq_GHz):
            print('Error! REFFREQ or RESTFRQ or RESTFREQ was not found in the fits header! We need that to compute velocity! Abort!')
            sys.exit()
        else:
            velo_kms = (freq_GHz - reffreq_GHz) / reffreq_GHz * c30
            #print('reffreq_GHz:', reffreq_GHz)
        
    elif hdu0.header['CTYPE3'].strip().lower().startswith('velo'):
        
        if hdu0.header['CUNIT3'].strip().lower().startswith('m/s'):
            conv_kms = 1.0 / 1e3
        else:
            conv_kms = 1.0
        
        velo_kms = skycoord3 * conv_kms
        
        reffreq_GHz = get_reffreq_GHz(hdu0.header, 1./1e9) # assuming fits header key value has a unit of Hz
        
        freq_GHz = velo_kms / c30 * reffreq_GHz + reffreq_GHz
        
    else:
        print('Error! The CTYPE3 "%s" is neither a frequency nor a velocity. Could not proceed!'%(hdu0.header['CTYPE3'].strip()))
        sys.exit()
    
    # output to stdout
    #print(velo_kms)
    sys.stdout.write('Velocity [km/s]:')
    for i in range(len(velo_kms)):
        sys.stdout.write(' ')
        sys.stdout.write('%.12g'%(velo_kms[i]))
    sys.stdout.write('\n')
    
    if len(freq_GHz) > 0:
        sys.stdout.write('Frequency [GHz]:')
        for i in range(len(freq_GHz)):
            sys.stdout.write(' ')
            sys.stdout.write('%.12g'%(freq_GHz[i]))
        sys.stdout.write('\n')
    









