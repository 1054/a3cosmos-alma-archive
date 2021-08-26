#!/usr/bin/env python
# 
# 20190503

import os, sys, re, copy
import numpy as np
import astropy
import astropy.io.fits as fits



# Read user input
input_fits_file = ''
output_fits_file = ''
for i in range(1,len(sys.argv)):
    if input_fits_file == '':
        input_fits_file = sys.argv[i]
        continue
    if output_fits_file == '':
        output_fits_file = sys.argv[i]
    

if input_fits_file == '':
    print('Usage:')
    print('    alma_fits_image_cube_trim_dimension.py INPUT_FITS_IMAGE_CUBE.fits OUTPUT_NAME.fits')
    print('Note:')
    print('    This code will trim the 4th and higher dimensions of the input fits image cube.')
    print('    So that the output fits image cube can be processed with STARLINK GAIA.')
    print('')
    sys.exit()


if output_fits_file == '':
    output_fits_file = re.sub(r'\.fits$', r'', input_fits_file, re.IGNORECASE) + '_3D.fits'


#print('input_fits_file = "%s"'%(input_fits_file))
#print('output_fits_file = "%s"'%(output_fits_file))


with fits.open(input_fits_file) as hdulist:
    
    print(hdulist.info())
    hdu0 = hdulist[0]
    #print(hdu0)
    
    #hdu0.header
    #hdu0.data
    print('Dimensions:', hdu0.data.shape)
    print('Dimensions:', hdu0.data[0,:,:,:].shape)
    hdu1data = copy.deepcopy(hdu0.data[0,:,:,:])
    hdu1header = copy.deepcopy(hdu0.header)
    hdu1header['NAXIS'] = 3
    for key in ['NAXIS4','PC01_04','PC02_04','PC03_04','PC04_04',
                         'PC04_01','PC04_02','PC04_03',
                'CTYPE4','CRVAL4','CDELT4','CRPIX4','CUNIT4']:
        del hdu1header[key]
    # 
    hdu1 = fits.PrimaryHDU(hdu1data, header=hdu1header)
    hdu1.writeto(output_fits_file)
    print('Output to "%s"!'%(output_fits_file))









