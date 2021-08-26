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
    print('    alma_fits_uv_cube_plot_interferogram.py INPUT_FITS_IMAGE_CUBE.fits -out OUTPUT_NAME')
    print('Note:')
    print('    This code will plot the uv-plane amplitude and phase of the input fits uv cube.')
    print('')
    sys.exit()


# Set default output name
if output_name == '':
    output_name = 'Plot_interferogram_of_' + re.sub(r'(\.fits|\.uvfits)$', r'', input_fits_file, re.IGNORECASE)
else:
    output_name = re.sub(r'\.pdf$', r'', output_name) # remove suffix


#print('input_fits_file = "%s"'%(input_fits_file))
#print('output_name = "%s"'%(output_name))


# Open fits file and extract the spectrum
with fits.open(input_fits_file) as hdulist:
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
    
    # 
    # make output dir if needed for multi-channel data
    if nchan > 1:
        if not os.path.isdir(output_name):
            print('os.makedirs("%s")'%(output_name))
            os.makedirs(output_name)
    
    # 
    # prepare grid dimension and the gridded_vis_cube
    nx = 201
    ny = 201
    gridded_vis_cube = np.zeros((nchan,ny,nx))
    
    # 
    # Loop each channel
    for i in range(nchan):
        
        # 
        # Show the image
        fig = plt.figure(figsize=(10.0,4.0))
        
        # grid the data
        xi = np.linspace(-uvdist_absmax, uvdist_absmax, num=nx, endpoint=True)
        yi = np.linspace(-uvdist_absmax, uvdist_absmax, num=ny, endpoint=True)
        xd = np.concatenate((udist_array,-udist_array))
        yd = np.concatenate((vdist_array,-vdist_array))
        vd = np.concatenate((vis_array_abs[:,i],vis_array_abs[:,i]))
        zi = griddata((xd, yd), vd, 
                      (xi[None,:], yi[:,None]), method='linear')
        
        print('channel %d, vis array abs, sum(zi) = %s, (zi[50,50]) = %s'%(i, np.nansum(zi), zi[50,50]))
        gridded_vis_cube[i,:,:] = zi
        
        # plot
        ax_visabs = fig.add_subplot(1,2,1)
        ax_imshow = ax_visabs.imshow(zi, origin='lower', extent=[udist_min,udist_max,vdist_min,vdist_max], vmin=vis_min, vmax=vis_max)
        plt.colorbar(ax_imshow)
        ax_visabs.set_title('Interferogram Amplitude')
        
        
        # grid the data
        xd = np.concatenate((udist_array,-udist_array))
        yd = np.concatenate((vdist_array,-vdist_array))
        vd = np.concatenate((vis_array_ang[:,i],vis_array_ang[:,i]))
        zi = griddata((xd, yd), vd, 
                      (xi[None,:], yi[:,None]), method='linear')
        
        # plot
        ax_visangle = fig.add_subplot(1,2,2)
        ax_imshow = ax_visangle.imshow(zi/np.pi*180.0, origin='lower', extent=[udist_min,udist_max,vdist_min,vdist_max], vmin=-180, vmax=180)
        plt.colorbar(ax_imshow)
        ax_visangle.set_title('Interferogram Phase')
        
        
        
        # adjust margin
        fig.tight_layout()
        
        #fig = plt.figure(figsize=(15.0, 4.0))
        #ax = fig.add_subplot(1,1,1)
        #ax.plot(skycoord3, skycoord3*0.0, linestyle='solid', linewidth=0.9, color='#555555')
        #ax.step(skycoord3, extracted_spectrum)
        #ax.tick_params(axis='both', which='major', direction='in', labelsize=13)
        #ax.xaxis.set_ticks_position('both')
        #ax.yaxis.set_ticks_position('both')
        #ax.set_xlabel(output_X_column_name, fontsize=15, labelpad=10)
        #ax.set_ylabel(output_Y_column_name, fontsize=15, labelpad=10)
        #fig.tight_layout()
        if nchan > 1:
            output_filename = output_name+os.sep+'channel_%d.pdf'%(i)
        else:
            output_filename = output_name+'.pdf'
        fig.savefig(output_filename, dpi=200, overwrite=True)
        print('Output to "%s"!'%(output_filename))
        
        plt.clf()
    
    
    # 
    # save gridded_vis_cube
    if nchan > 1:
        output_filename = output_name+os.sep+'gridded_vis_cube.fits'
        output_hdu = fits.PrimaryHDU()
        output_hdu.data = gridded_vis_cube
        output_hdu.writeto(output_filename, clobber=True) # clobber=True overwrites the output file
        print('Output to "%s"!'%(output_filename))








