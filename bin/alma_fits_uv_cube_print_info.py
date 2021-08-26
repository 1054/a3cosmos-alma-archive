#!/usr/bin/env python
# 
# 20190503

import os, sys, re, copy, datetime
import warnings
warnings.simplefilter("ignore")
import numpy as np
import astropy
import astropy.io.fits as fits
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy.interpolate import griddata


# Read user input
input_fits_file = ''
output_name = ''
arg_str = ''
arg_mode = ''
for i in range(1,len(sys.argv)):
    # 
    arg_str = sys.argv[i].lower().replace('--','-')
    # 
    # parse arg_str
    if arg_str.startswith('-out'):
        arg_mode = 'out'
        continue
    # 
    elif arg_mode == '':
        arg_mode = 'in'
    # 
    # parse arg_mode
    if arg_mode == 'in':
        input_fits_file = sys.argv[i]
        arg_mode = ''
    # 
    elif arg_mode == 'out':
        output_name = sys.argv[i]
        arg_mode = ''
    

# Check user input
if input_fits_file == '':
    print('Usage:')
    print('    alma_fits_uv_cube_print_info.py INPUT_FITS_IMAGE_CUBE.fits')
    print('Note:')
    print('    This code will print basic information of the input fits uv cube.')
    print('')
    sys.exit()


#print('input_fits_file = "%s"'%(input_fits_file))
#print('output_name = "%s"'%(output_name))


# Open fits file and extract the spectrum
with fits.open(input_fits_file, mode='readonly', memmap=False, do_not_scale_image_data=True) as hdulist:
    # 
    print(hdulist.info())
    hdu0 = hdulist[0]
    # 
    # check type
    if not (hdu0.header['groups'] == True):
        print('Error! The input fits file "%s" is not a uvfits! Exit!'%(input_fits_file))
        sys.exit()
    # 
    # check type
    if not (hdu0.header['CTYPE4'].strip() == 'FREQ'):
        print('Error! The input fits file "%s" CTYPE4 is not FREQ! Exit!'%(input_fits_file))
        sys.exit()
    # 
    # check type
    if not (hdu0.header['CTYPE3'].strip() == 'STOKES'):
        print('Error! The input fits file "%s" CTYPE3 is not STOKES! Exit!'%(input_fits_file))
        sys.exit()
    # 
    # check type
    if not (len(hdu0.shape) == 7):
        print('Error! The input fits file "%s" data shape dimension is not 7! It is not a standard CASA uvfits! Exit!'%(input_fits_file))
        print('hdu0.shape', hdu0.shape)
        sys.exit()
    # 
    # check nvis and nchan
    #print('hdu0.shape', hdu0.shape)
    #print('hdu0.header[\'CTYPE4\']', hdu0.header['CTYPE4'])
    print('hdu0.shape', hdu0.shape)
    nvis = hdu0.header['gcount']
    nchan = hdu0.shape[3] # CTYPE4
    nstokes = hdu0.shape[4] # CTYPE3
    ncomplex = hdu0.shape[5] # should be 3: im, re, we
    print('nvis = %d'%(nvis))
    print('nchan = %d'%(nchan))
    print('nstokes = %d'%(nstokes))
    #print(hdu0.data.parnames)
    print(type(hdu0.data.par('UU')))
    udist_array = hdu0.data.par('UU')
    vdist_array = hdu0.data.par('VV')
    udist_min = np.min(udist_array)
    udist_max = np.max(udist_array)
    vdist_min = np.min(vdist_array)
    vdist_max = np.max(vdist_array)
    print('udist_min =', udist_min)
    print('udist_max =', udist_max)
    print('vdist_min =', vdist_min)
    print('vdist_max =', vdist_max)
    uvdist_absmax = np.max([np.abs(udist_min),np.abs(udist_max),np.abs(vdist_min),np.abs(vdist_max)])
    if nstokes == 1:
        vis_array_real = hdu0.data.data[:,0,0,0,:,0,0]
        vis_array_imag = hdu0.data.data[:,0,0,0,:,0,1]
        vis_array = vis_array_real + 1j * vis_array_imag
    elif nstokes == 2:
        vis_array_real = (hdu0.data.data[:,0,0,0,:,0,0] + hdu0.data.data[:,0,0,0,:,1,0]) / 2.0
        vis_array_imag = (hdu0.data.data[:,0,0,0,:,0,1] + hdu0.data.data[:,0,0,0,:,1,1]) / 2.0
        vis_array = vis_array_real + 1j * vis_array_imag
    else:
        print('Error! More than 2 STOKES! Sorry that we could not deal with it!')
        sys.exit()
    # 
    print(vis_array.shape)
    
    # 
    # Loop each channel and determine vis min max
    vis_array_abs = np.absolute(vis_array)
    vis_array_ang = np.angle(vis_array)
    vis_min = 0.0 # np.min(vis_array_abs)
    vis_max = np.max(vis_array_abs)
    print('vis_min =', vis_min)
    print('vis_max =', vis_max)
    







