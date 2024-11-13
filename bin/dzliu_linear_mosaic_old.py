#!/usr/bin/env python
# 
# This needs to be run in CASA
# 
# CASA modules/functions used:
#     tb, casalog, mstransform, inp, saveinputs, exportfits
# 
# Example:
#     import dzliu_linear_mosaic; reload(dzliu_linear_mosaic); from a_dzliu_code_level_4_clean import dzliu_clean; dzliu_clean()
# 
# For old CASA 4.7.2
#     pip-2.7 install --target=~/Applications/CASA-472.app/Contents/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages astropy
# 
from __future__ import print_function
import os, sys, re, json, copy, timeit, time, datetime, shutil
import numpy as np
from taskinit import casalog, tb #, ms, iatool
#from taskinit import casac
#tb = casac.table
#from __casac__.table import table as tb
#from recipes import makepb, pixelmask2cleanmask
import casadef
def version_tuple(version_str):
    return tuple(map(int, (version_str.split("."))))
def version_less_than(version_str, compared_version_str):
    return version_tuple(version_str) < version_tuple(compared_version_str)
def version_greater_equal(version_str, compared_version_str):
    return version_tuple(version_str) >= version_tuple(compared_version_str)
if version_less_than(casadef.casa_version, '6.0.0'):
    #from __main__ import default, inp, saveinputs
    ##import task_tclean; task_tclean.tclean # this is what tclean.py calls
    ##import tclean
    ##import tclean_cli
    from tclean_cli import tclean_cli_
    tclean = tclean_cli_()
    from mstransform_cli import mstransform_cli_
    mstransform = mstransform_cli_()
    from exportfits_cli import exportfits_cli_
    exportfits = exportfits_cli_()
    from imstat_cli import imstat_cli_
    imstat = imstat_cli_()
else:
    # see CASA 6 updates here: https://alma-intweb.mtk.nao.ac.jp/~eaarc/UM2018/presentation/Nakazato.pdf
    from casatasks import tclean, mstransform, exportfits, imstat
    #from casatasks import sdbaseline
    #from casatools import ia



# 
# def print2
# 
def print2(message):
    print(message)
    casalog.post(message, 'INFO')




# 
# def velo2freq
# 
def velo2freq(input_fits_header):
    # 
    if input_fits_header['NAXIS'] >= 3:
        if input_fits_header['CTYPE3'].strip().upper() == 'VRAD':
            ctype3 = input_fits_header['CTYPE3']
            cunit3 = input_fits_header['CUNIT3'].strip().replace(' ','').lower()
            crpix3 = input_fits_header['CRPIX3']
            crval3 = input_fits_header['CRVAL3']
            cdelt3 = input_fits_header['CDELT3']
            if cunit3 == 'km/s' or cunit3 == 'kms-1':
                c30 = 2.99792458e5
            else:
                c30 = 2.99792458e8
            input_fits_header['CRVAL3'] = (1.0-(crval3/c30))*input_fits_header['RESTFRQ'] # Hz, (nu0-nu)/nu0 = (v/c), so nu = (1-(v/c))*nu0
            input_fits_header['CDELT3'] = (-(cdelt3/c30))*input_fits_header['RESTFRQ'] # Hz, reversed order
            input_fits_header['CTYPE3'] = 'FREQ'
            input_fits_header['CUNIT3'] = 'Hz'
    # 
    return input_fits_header





# 
# def project_fits_cube_data
# 
def project_fits_cube_data(input_fits_cube_data, input_fits_header, template_fits_header):
    # 
    # We will project the input_fits_cube to the pixel grid of the template_fits_cube_wcs
    # by matching the World Coordinate System (WCS). 
    # 
    # We can process both fits cubes and images. 
    # 
    # No CASA module required. 
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    from scipy.interpolate import griddata
    # 
    # Check input
    #if type(input_fits_cube_wcs) is not WCS:
    #    raise ValueError('Error! The input input_fits_cube_wcs is not a astropy.wcs.WCS!')
    #if type(template_fits_cube_wcs) is not WCS:
    #    raise ValueError('Error! The input template_fits_cube_wcs is not a astropy.wcs.WCS!')
    #if len(list(input_fits_cube_data.shape)) != input_fits_cube_wcs.naxis:
    #    raise ValueError('Error! The input input_fits_cube_data has a shape of %s which is inconsistent with the input WCS with NAXIS %d!'%(list(input_fits_cube_data.shape), input_fits_cube_wcs.naxis))
    if type(input_fits_header) is not fits.Header:
        raise ValueError('Error! The input input_fits_header is not a astropy.io.fits.Header!')
    if type(template_fits_header) is not fits.Header:
        raise ValueError('Error! The input template_fits_header is not a astropy.io.fits.Header!')
    if len(list(input_fits_cube_data.shape)) != input_fits_header['NAXIS']:
        raise ValueError('Error! The input input_fits_cube_data has a shape of %s which is inconsistent with the input fits header with NAXIS %d!'%(list(input_fits_cube_data.shape), input_fits_header['NAXIS']))
    # 
    #template_fits_header = template_fits_cube_wcs.to_header()
    #input_fits_header = input_fits_cube_wcs.to_header()
    idata = input_fits_cube_data
    # 
    # Make sure the input is a 3D cube or at least a 2D image
    if int(input_fits_header['NAXIS']) < 2:
        raise Exception('Error! The input fits header does not have more than 2 dimensions!')
    if int(template_fits_header['NAXIS']) < 2:
        raise Exception('Error! The template fits header does not have more than 2 dimensions!')
    # 
    # Do velocity-to-frequency conversion before checking header consistency
    if input_fits_header['CTYPE3'].strip().upper() == 'VRAD' and template_fits_header['CTYPE3'].strip().upper() == 'FREQ':
        input_fits_header = velo2freq(input_fits_header)
    # 
    # Take the minimum dimension of the input and the template fits dimension.
    naxis = min(int(input_fits_header['NAXIS']), int(template_fits_header['NAXIS']))
    # 
    # Check header consistency
    for i in range(1, naxis+1):
        if input_fits_header['CTYPE%d'%(i)].strip().upper() != template_fits_header['CTYPE%d'%(i)].strip().upper():
            raise Exception('Error! The input fits cube CTYPE%d is %s but the template CTYPE%d is %s!'%(\
                                i, input_fits_header['CTYPE%d'%(i)].strip(), \
                                i, template_fits_header['CTYPE%d'%(i)].strip() ) )
    # 
    # Store dimension arrays 'NAXISi'
    inaxis = np.array([int(input_fits_header['NAXIS%d'%(i)]) for i in range(1, input_fits_header['NAXIS']+1)]) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    onaxis = np.array([int(template_fits_header['NAXIS%d'%(i)]) for i in range(1, template_fits_header['NAXIS']+1)]) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    inaxis_str = 'x'.join(inaxis[0:naxis].astype(str))
    onaxis_str = 'x'.join(onaxis[0:naxis].astype(str)) # output naxis, same as template
    idatashape = copy.copy(inaxis[0:naxis][::-1])
    odatashape = copy.copy(onaxis[0:naxis][::-1])
    # 
    # If input fits data have extra higher dimensions than the template data, we will condense the additional dimensions into one extra dimension, and later we will loop them over and do the interpolation slice-by-slice.
    idataslice = 0
    if len(inaxis) > naxis:
        print2('Warning! The input fits cube has %d dimensions while the template has only %d dimensions! We will loop the extra higher dimensions of the input data slice-by-slice and project to template pixel grid.'%(input_fits_header['NAXIS'], template_fits_header['NAXIS']))
        idataslice = np.product(inaxis[naxis:])
        idatashape = np.concatenate([[idataslice], idatashape])
        idata.shape = idatashape # this will reshape the idata array.
        odatashape = np.concatenate([inaxis[naxis:][::-1], odatashape])
        # here we reshape the input data to shrink all higher dimensions into one extra dimension, 
        # e.g., from (m,n,a,b,c) to (x,a,b,c), when the template data shape is (a,b,c), and x = m*n. 
    # 
    # Otherwise if the template fits data have extra higher dimensions, we will only use the common dimensions, while pad extra dimensions with np.newaxis
    elif len(onaxis) > naxis:
        print2('Warning! The input fits cube has %d dimensions while the template has %d dimensions! We will ignore the extra higher dimensions in the template for computation and simply reshape the output data to the template dimensions.'%(input_fits_header['NAXIS'], template_fits_header['NAXIS']))
        odatashape = []
        idataslice = -(len(onaxis) - naxis) # negative value means template has more dimension than the input fits cube.
        odatashape = np.concatenate([[1]*idataslice, odatashape]) # just fill extra dimensions with 1.
        output_fits_data_shape = odatashape
    # 
    # Otherwise the output fits data shape is the same as the template fits data shape
    else:
        output_fits_data_shape = copy.copy(onaxis[::-1])
    # 
    # Get input fits WCS with naxis=naxis
    iwcs = WCS(input_fits_header, naxis=naxis)
    # 
    # Get template fits WCS with naxis=naxis
    twcs = WCS(template_fits_header, naxis=naxis)
    # 
    # Make pixel mgrid
    timestart = timeit.default_timer()
    if naxis == 2:
        # input grid
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        iy, ix = np.mgrid[0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten()])
        # output grid = template grid
        print2('Generating pixel mgrid with %s pixels'%(onaxis_str))
        ty, tx = np.mgrid[0:onaxis[1], 0:onaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten()])
    elif naxis == 3:
        # input grid
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        ichan, iy, ix = np.mgrid[0:inaxis[2], 0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten(), ichan.flatten()])
        # output grid = template grid
        print2('Generating pixel mgrid with %s pixels'%(onaxis_str))
        tchan, ty, tx = np.mgrid[0:onaxis[2], 0:onaxis[1], 0:onaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten(), tchan.flatten()])
    else:
        raise NotImplementedError('Error! The cube projection and interpolation have not been implemented for an NAXIS of %d!'%(naxis))
    timestop = timeit.default_timer()
    print2('Used %s seconds'%(timestop-timestart))
    # 
    # Timer starts
    timestart = timeit.default_timer()
    # 
    # Convert each pixel coordinate to skycoordinate for the template pixel grid which is also the output pixel grid.
    print2('Computing wcs_pix2world for %s pixels'%(onaxis_str))
    oskycoords = twcs.wcs_pix2world(tpixcoords, 0)
    print2('oskycoords.shape = %s'%(str(list(oskycoords.shape))))
    # 
    # Convert each pixel skycoordinate to the coordinate in the input mask cube, so that we can do interpolation. 
    print2('Computing wcs_world2pix for %s pixels'%(onaxis_str))
    opixcoords = iwcs.wcs_world2pix(oskycoords, 0)
    print2('opixcoords.shape = %s'%(str(list(opixcoords.shape))))
    # 
    # Timer stops
    timestop = timeit.default_timer()
    print2('Used %s seconds'%(timestop-timestart))
    # 
    # Loop each input data slice
    print2('Looping %d data slices...'%(max(1,idataslice)))
    timestart = timeit.default_timer()
    odata = []
    odataarray = None
    for i in range(max(1,idataslice)):
        # 
        # Do interpolation with scipy.interpolate.griddata
        print2('Interpolating griddata...')
        if idataslice > 0:
            idataarray = idata[i].flatten()
        else:
            idataarray = idata.flatten()
        print2('idata[%d].shape = %s'%(i, list(idata[i].shape)))
        print2('ipixcoords.shape = %s'%(list(ipixcoords.shape)))
        print2('opixcoords.shape = %s'%(list(opixcoords.shape)))
        # note that if the last dimension has a size of 1, griddata will fail. So we have to wrap around.
        if naxis == 3 and idata[i].shape[0] == 1:
            idatamask = ~np.isnan(idataarray)
            ipixcoords_2 = ipixcoords[:, 0:2]
            opixcoords_2 = opixcoords[:, 0:2]
            idataarray_2 = idataarray
            odataarray = griddata(ipixcoords_2[idatamask], \
                                  idataarray_2[idatamask], \
                                  opixcoords_2, \
                                  method = 'cubic', \
                                  fill_value = np.nan ) # 2D cubic
        else:
            idatamask = ~np.isnan(idataarray)
            odataarray = griddata(ipixcoords[idatamask], \
                                  idataarray[idatamask], \
                                  opixcoords, \
                                  method = 'linear', \
                                  fill_value = np.nan ) # 3D linear
        # 
        # The interpolation is done with serialized arrays, so we reshape the output interpolated aray to 3D cube 
        odataarray = odataarray.reshape(onaxis[0:naxis][::-1]).astype(idata.dtype)
        if idataslice > 0:
            odata.append(odataarray)
        else:
            odata = odataarray
        # 
        # Timer stops
        timestop = timeit.default_timer()
        print2('Used %s seconds'%(timestop-timestart))
    # 
    odata = np.array(odata)
    # 
    print('input_fits_data_shape = %s'%(idatashape))
    print('output_fits_data_shape = %s'%(odatashape))
    odata.shape = odatashape
    # 
    return odata




# 
# def project_fits_cube
# 
def project_fits_cube(input_fits_cube, template_fits_cube, output_fits_cube, overwrite = False):
    # 
    # We will project the input_fits_cube to the pixel grid of the template_fits_cube_or_wcs
    # by matching the World Coordinate System (WCS). 
    # 
    # We can process both fits cubes and images. 
    # 
    # No CASA module required. 
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    from scipy.interpolate import griddata
    # 
    # Read template_fits_cube_or_wcs
    if type(template_fits_cube) is WCS:
        # If input is a fits wcs
        template_fits_header = template_fits_cube_or_wcs.to_header()
    elif type(template_fits_cube) is fits.Header:
        # If input is a fits wcs
        template_fits_header = template_fits_cube
    else:
        # If input is a fits file
        print('Reading "%s"'%(template_fits_cube))
        template_hdulist = fits.open(template_fits_cube)
        template_hdu = template_hdulist[0]
        template_fits_header = template_hdu.header
    # 
    # Read input_fits_cube
    print('Reading "%s"'%(input_fits_cube))
    input_hdulist = fits.open(input_fits_cube)
    input_hdu = input_hdulist[0]
    input_fits_header = input_hdu.header
    input_fits_data = input_hdu.data
    input_fits_data_shape = list(input_fits_data.shape)
    # 
    # Make sure the input is a 3D cube or at least a 2D image
    if int(input_fits_header['NAXIS']) < 2:
        raise Exception('Error! The input fits cube "%s" does not have more than 2 dimensions!'%(input_fits_cube))
    if int(template_fits_header['NAXIS']) < 2:
        raise Exception('Error! The input fits cube "%s" does not have more than 2 dimensions!'%(template_fits_cube))
    # 
    # Make sure the input fits data have at least equal dimensions as the template fits data. For extra higher dimensions, we will loop them over.
    #if int(input_fits_header['NAXIS']) < int(template_fits_header['NAXIS']):
    #    raise Exception('Error! The input fits cube "%s" has %d dimensions but the template "%s" has %d dimensions!'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
    # 
    # Take the template fits dimension.
    naxis = min(int(input_fits_header['NAXIS']), int(template_fits_header['NAXIS']))
    # 
    # Do velocity-to-frequency conversion before checking header consistency
    input_fits_header = velo2freq(input_fits_header)
    # 
    # Check header consistency and record NAXISi
    inaxis = []
    tnaxis = []
    for i in range(1, naxis+1):
        if input_fits_header['CTYPE%d'%(i)].strip().upper() != template_fits_header['CTYPE%d'%(i)].strip().upper():
            raise Exception('Error! The input fits cube "%s" CTYPE%d is %s but the template "%s" CTYPE%d is %s!'%(\
                                input_fits_cube, i, input_fits_header['CTYPE%d'%(i)].strip(), \
                                template_fits_cube, i, template_fits_header['CTYPE%d'%(i)].strip() ) )
        inaxis.append(int(input_fits_header['NAXIS%d'%(i)]))
        tnaxis.append(int(template_fits_header['NAXIS%d'%(i)]))
    inaxis = np.array(inaxis) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    tnaxis = np.array(tnaxis) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    inaxis_str = 'x'.join(inaxis.astype(str))
    tnaxis_str = 'x'.join(tnaxis.astype(str))
    # 
    # If input fits data have extra higher dimensions than the template data, we will condense the additional dimensions into one extra dimension, and later we will loop them over and do the interpolation slice-by-slice.
    idataslice = 0
    if int(input_fits_header['NAXIS']) > naxis:
        print2('Warning! The input fits cube "%s" has %d dimensions while the template "%s" has only %d dimensions! We will loop the extra higher dimensions of the input data slice-by-slice and project to template pixel grid.'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
        idatashape = copy.copy(input_fits_data_shape[::-1][0:naxis])
        idataslice = np.product(input_fits_data_shape[::-1][naxis:])
        idatashape.append(idataslice)
        idatashape = idatashape[::-1]
        input_fits_data.shape = idatashape
        output_fits_data_shape = copy.copy(input_fits_data_shape)
        output_fits_data_shape = output_fits_data_shape[::-1]
        output_fits_data_shape[0:naxis] = [0]*naxis # set to zero for now
        output_fits_data_shape = output_fits_data_shape[::-1]
        #print2('input_fits_data_shape = %s'%(input_fits_data_shape))
        #print2('output_fits_data_shape = %s'%(output_fits_data_shape))
        # here we reshape the input data to shrink all higher dimensions into one extra dimension, 
        # e.g., from (m,n,a,b,c) to (x,a,b,c), when the template data shape is (a,b,c), and x = m*n. 
    # 
    # Otherwise if the template fits data have extra higher dimensions, we will only use the common dimensions, while pad extra dimensions with np.newaxis
    elif int(template_fits_header['NAXIS']) > naxis:
        print2('Warning! The input fits cube "%s" has %d dimensions while the template "%s" has %d dimensions! We will ignore the extra higher dimensions in the template for computation and simply reshape the output data to the template dimensions.'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
        odatashape = []
        idataslice = -(int(template_fits_header['NAXIS']) - naxis)
        for i in range(naxis):
            odatashape.append(tnaxis[i]) # template_fits_header['NAXIS%d'(i+1)]
        for i in range(naxis, naxis-idataslice):
            odatashape.append(1) # template_fits_header['NAXIS%d'(i+1)]
        odatashape = odatashape[::-1]
        output_fits_data_shape = odatashape
    # 
    # Otherwise the output fits data shape is the same as the template fits data shape
    else:
        output_fits_data_shape = copy.copy(tnaxis[::-1])
    # 
    # Get input fits WCS
    iwcs = WCS(input_fits_header, naxis=naxis)
    idata = input_fits_data
    # 
    # Get template fits WCS
    twcs = WCS(template_fits_header, naxis=naxis)
    tdatashape = tnaxis[::-1] # this will also be the shape of (each slice of) the output data array
    #print2('tdatashape = %s'%(tdatashape)) # [nchan, ny, nx]
    # 
    # trim the single dimension axis
    #while inaxis[-1] == 1:
    #    del inaxis[-1]
    #while tnaxis[-1] == 1:
    #    del tnaxis[-1]
    # 
    # Make pixel mgrid
    timestart = timeit.default_timer()
    if naxis == 2:
        # 
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        iy, ix = np.mgrid[0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten()])
        # 
        print2('Generating pixel mgrid with %s pixels'%(tnaxis_str))
        ty, tx = np.mgrid[0:tnaxis[1], 0:tnaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten()])
        # 
    elif naxis == 3:
        # 
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        ichan, iy, ix = np.mgrid[0:inaxis[2], 0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten(), ichan.flatten()])
        # 
        print2('Generating pixel mgrid with %s pixels'%(tnaxis_str))
        tchan, ty, tx = np.mgrid[0:tnaxis[2], 0:tnaxis[1], 0:tnaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten(), tchan.flatten()])
        # 
    else:
        raise NotImplementedError('Error! The cube projection and interpolation have not been implemented for an NAXIS of %d!'%(naxis))
    # 
    timestop = timeit.default_timer()
    print2('Used %s seconds'%(timestop-timestart))
    # 
    #raise NotImplementedError() # debug point
    # 
    timestart = timeit.default_timer()
    # 
    # Convert each pixel coordinate to skycoordinate for the template pixel grid which is also the output pixel grid.
    print2('Computing wcs_pix2world for %s pixels'%(tnaxis_str))
    oskycoords = twcs.wcs_pix2world(tpixcoords, 0)
    print2('oskycoords.shape = %s'%(list(oskycoords.shape)))
    #tra, tdec, tfreq = oskycoords.T
    # 
    # Convert each pixel skycoordinate to the coordinate in the input mask cube, so that we can do interpolation. 
    print2('Computing wcs_world2pix for %s pixels'%(tnaxis_str))
    opixcoords = iwcs.wcs_world2pix(oskycoords, 0)
    print2('opixcoords.shape = %s'%(list(opixcoords.shape)))
    # 
    timestop = timeit.default_timer()
    print2('Used %s seconds'%(timestop-timestart))
    # 
    # Loop each input data slice
    odata = []
    odataarray = None
    for i in range(max(1,idataslice)):
        # 
        # Do interpolation with scipy.interpolate.griddata
        timestart = timeit.default_timer()
        print2('Interpolating griddata...')
        if idataslice > 0:
            idataarray = idata[i].flatten()
        else:
            idataarray = idata.flatten()
        print2('idata[%d].shape = %s'%(i, list(idata[i].shape)))
        print2('ipixcoords.shape = %s'%(list(ipixcoords.shape)))
        # note that if the last dimension has a size of 1, griddata will fail. So we have to wrap around.
        if idata[i].shape[0] == 1:
            idatamask = ~np.isnan(idataarray)
            ipixcoords_2 = ipixcoords[:, 0:2]
            opixcoords_2 = opixcoords[:, 0:2]
            idataarray_2 = idataarray
            odataarray = griddata(ipixcoords_2[idatamask], \
                                  idataarray_2[idatamask], \
                                  opixcoords_2, \
                                  method = 'cubic', \
                                  fill_value = np.nan )
        else:
            idatamask = ~np.isnan(idataarray)
            odataarray = griddata(ipixcoords[idatamask], \
                                  idataarray[idatamask], \
                                  opixcoords, \
                                  method = 'linear', \
                                  fill_value = np.nan )
        timestop = timeit.default_timer()
        print2('Used %s seconds'%(timestop-timestart))
        # 
        # The interpolation is done with serialized arrays, so we reshape the output interpolated aray to 3D cube 
        odataarray = odataarray.reshape(tdatashape).astype(idata.dtype)
        if idataslice > 0:
            odata.append(odataarray)
        else:
            odata = odataarray
    odata = np.array(odata)
    #odatashape = list(odataarray.shape)[::-1]
    #odatashape.append(input_fits_data_shape[::-1][naxis:])
    #odatashape = odatashape[::-1]
    #print('odata.shape = %s'%(list(odata.shape)))
    output_fits_data_shape = output_fits_data_shape[::-1]
    output_fits_data_shape[0:naxis] = list(odata.shape)[::-1][0:naxis]
    output_fits_data_shape = output_fits_data_shape[::-1]
    print('input_fits_data_shape = %s'%(input_fits_data_shape))
    print('output_fits_data_shape = %s'%(output_fits_data_shape))
    print('odata.shape = %s'%(list(odata.shape)))
    odata.shape = output_fits_data_shape
    print('odata.shape = %s'%(list(odata.shape)))
    # 
    # Prepare output fits header
    twcs_to_header = twcs.to_header()
    output_hdu = fits.PrimaryHDU(data = odata)
    output_fits_header = copy.copy(output_hdu.header)
    for i in range(0, naxis):
        for keybase in ['CTYPE', 'CUNIT', 'CRPIX', 'CRVAL', 'CDELT']:
            key = keybase+'%d'%(i+1)
            output_fits_header[key] = twcs_to_header[key]
    # 
    if idataslice > 0:
        #output_fits_header['NAXIS'] = len(input_fits_data_shape)
        for i in range(naxis, len(input_fits_data_shape)):
            for keybase in ['CTYPE', 'CUNIT', 'CRPIX', 'CRVAL', 'CDELT']:
                key = keybase+'%d'%(i+1)
                if key in input_fits_header:
                    output_fits_header[key] = input_fits_header[key] # read extra dimension from input fits header
    elif idataslice < 0:
        #output_fits_header['NAXIS'] = len(output_fits_data_shape)
        for i in range(naxis, len(output_fits_data_shape)):
            for keybase in ['CTYPE', 'CUNIT', 'CRPIX', 'CRVAL', 'CDELT']:
                key = keybase+'%d'%(i+1)
                if key in template_fits_header:
                    output_fits_header[key] = template_fits_header[key] # read extra dimension from template fits header
    # 
    for key in ['EQUINOX', 'RADESYS', 'LONPOLE', 'LATPOLE', 'RESTFRQ', 'SPECSYS', 'ALTRVAL', 'ALTRPIX', 'VELREF', 'TELESCOP', 'INSTRUME', 'OBSERVER', 'DATE-OBS', 'TIMESYS', 'OBSRA', 'OBSDEC', 'OBSGEO-X', 'OBSGEO-Y', 'OBSGEO-Z', 'OBJECT']:
        if key in input_fits_header:
            output_fits_header[key] = input_fits_header[key]
    # 
    output_fits_header['DATE'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + 'T' + time.strftime('%Z')
    output_fits_header['ORIGIN'] = 'dzliu_linear_mosaic.project_fits_cube()'
    # 
    # Output the interpolated mask cube as a fits file
    print2('Writing fits file...')
    output_hdu = fits.PrimaryHDU(data = odata, header = output_fits_header)
    if not re.match(r'.*\.fits$', output_fits_cube, re.IGNORECASE):
        output_fits_cube += '.fits'
    output_hdu.writeto(output_fits_cube, overwrite = overwrite)
    print2('Output to "%s"!'%(output_fits_cube))

# 
# def test_project_fits_cube
# 
#def test_project_fits_cube():
#    project_fits_cube(input_fits_cube = 'ngc4321_co21_clean_mask.fits', 
#                      template_fits_cube = 'run_tclean_2015.1.00956.S._.12m._.1/ngc4321_co21_dirty.image.pbcor.fits', 
#                      output_fits_cube = 'test_project_fits_cube.fits', 
#                      overwrite = True)

# 
# test here!
# 
#test_project_fits_cube()
#raise NotImplementedError()





# 
# def examine_overlap_pixels
# 
def examine_overlap_pixels(input_image_1, input_image_2):
    # 
    # Input two data cubes with the same 3rd dimension.
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    raise NotImplementedError('Sorry, dzliu_linear_mosaic.examine_overlap_pixels() not implemented! Use phangs_alma_QA_for_multipart_combined_cube.py instead!')
    




# 
# def dzliu_linear_mosaic
# 
def dzliu_linear_mosaic(input_image_name_list, output_fits_cube):
    # 
    # We will read the input_mask_cube, register the cube to the template_image_cube WCS, 
    # and output the mask cube. 
    # 
    # No CASA module required
    # 
    # TODO: The user can supply some parameters to add some mask conditions using the template_image_cube
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    # 
    # check input
    if np.isscalar(input_image_name_list):
        input_image_name_list = [input_image_name_list]
    # 
    # find image fits file and pb file
    input_fits_cube_list = []
    input_fits_pb_list = []
    for i in range(len(input_image_name_list)):
        input_fits_cube_list.append(input_image_name_list[i])
        if re.match(r'.*\.image\.pbcor\.fits$', input_image_name_list[i], re.IGNORECASE):
            input_fits_cube_list.append(input_image_name_list[i])
            input_image_name_list[i] = re.sub(r'\.image\.pbcor\.fits$', r'', input_image_name_list[i], re.IGNORECASE)
            is_pbcorreced = True
        elif re.match(r'.*\.image\.fits$', input_image_name_list[i], re.IGNORECASE):
            input_image_name_list[i] = re.sub(r'\.image\.fits$', r'', input_image_name_list[i], re.IGNORECASE)
        elif re.match(r'.*\.pb\.fits$', input_image_name_list[i], re.IGNORECASE):
            input_image_name_list[i] = re.sub(r'\.pb\.fits$', r'', input_image_name_list[i], re.IGNORECASE)
        elif re.match(r'.*\.fits$', input_image_name_list[i], re.IGNORECASE):
            input_image_name_list[i] = re.sub(r'\.fits$', r'', input_image_name_list[i], re.IGNORECASE)
        elif re.match(r'.*\.image$', input_image_name_list[i], re.IGNORECASE):
            input_image_name_list[i] = re.sub(r'\.image$', r'', input_image_name_list[i], re.IGNORECASE)
        elif re.match(r'.*_pb\.fits$', input_image_name_list[i], re.IGNORECASE):
            input_image_name_list[i] = re.sub(r'_pb\.fits$', r'', input_image_name_list[i], re.IGNORECASE)
        else:
            raise ValueError('Error! The input fits image "%s" should ends with ".image.pbcor.fits", ".image.fits" or ".fits" or ".image"!')
        # check fits cube file existence
        if not os.path.isfile(input_fits_cube_list[i]):
            raise Exception('Error! The fits image "%s" was not found! input_image_name_list[%d]: %s'%(input_fits_cube_list[i], i, input_image_name_list[i]))
        # check fits pb file existence and set 'input_fits_pb_list'
        if os.path.isfile(input_image_name_list[i]+'_pb.fits'):
            input_fits_pb_list.append(input_image_name_list[i]+'_pb.fits')
        elif os.path.isfile(input_image_name_list[i]+'.pb.fits'):
            input_fits_pb_list.append(input_image_name_list[i]+'.pb.fits')
        else:
            raise Exception('Error! The fits pb "%s" was not found! input_image_name_list[%d]: %s'%(input_image_name_list[i]+'.pb.fits', i, input_image_name_list[i]))
    # 
    if len(input_fits_pb_list) != len(input_fits_cube_list):
        raise Exception('Error! The input fits cube and pb are inconsistent! input_fits_cube_list: %s; input_fits_pb_list: %s'%(input_fits_cube_list, input_fits_pb_list))
    # 
    ninput = len(input_fits_cube_list)
    # 
    # 
    # check output, remove suffix
    #if output_fits_cube is None:
    #    output_fits_cube = 'run_linear_mosaic_%s/linear_mosaic'%(os.path.basename(input_fits_cube_list[0]))
    # 
    if re.match(r'.*\.fits$', output_fits_cube, re.IGNORECASE):
        output_fits_cube = re.sub(r'\.fits$', r'', output_fits_cube, re.IGNORECASE)
    # 
    if output_fits_cube.find(os.sep)>=0:
        if not os.path.isdir(os.path.dirname(output_fits_cube)):
            os.makedirs(os.path.dirname(output_fits_cube))
        if not os.path.isdir(os.path.dirname(output_fits_cube)):
            raise Exception('Error! Could not create output directory "%s"!'%(os.path.dirname(output_fits_cube)))
    # 
    # read fits header and wcs info
    fits_header_list = []
    fits_wcs_2D_list = []
    fits_pixscale_list = []
    fits_dimension_list = []
    fits_corner_00_RA_list = []
    fits_corner_00_Dec_list = []
    fits_corner_11_RA_list = []
    fits_corner_11_Dec_list = []
    fits_corner_01_RA_list = []
    fits_corner_01_Dec_list = []
    fits_corner_10_RA_list = []
    fits_corner_10_Dec_list = []
    for i in range(ninput):
        if not re.match(r'.*\.fits$', input_fits_cube_list[i], re.IGNORECASE):
            raise Exception('Error! Please input fits files!')
        if not re.match(r'.*\.fits$', input_fits_pb_list[i], re.IGNORECASE):
            raise Exception('Error! Please input fits files!')
        fits_header = None
        with fits.open(input_fits_cube_list[i]) as hdulist:
            hdu = hdulist[0]
            fits_header = copy.copy(hdu.header)
        fits_wcs_2D = WCS(fits_header, naxis=2)
        fits_corner_coords = fits_wcs_2D.wcs_pix2world([[0.5, 0.5], 
                                                        [fits_header['NAXIS1']+0.5, fits_header['NAXIS2']+0.5],
                                                        [0.5, fits_header['NAXIS2']+0.5],
                                                        [fits_header['NAXIS1']+0.5, 0.5]], 
                                                       1) # lower-left, and upper-right.
                                                          # pixel corners are 0.5, 0.5! see -- https://docs.astropy.org/en/stable/_modules/astropy/wcs/wcs.html
        print2('fits_corner_coords[%d][00][RA,Dec] = %.10f, %.10f, image = %r'%(i, fits_corner_coords[0][0], fits_corner_coords[0][1], input_fits_cube_list[i]))
        print2('fits_corner_coords[%d][11][RA,Dec] = %.10f, %.10f, image = %r'%(i, fits_corner_coords[1][0], fits_corner_coords[1][1], input_fits_cube_list[i]))
        print2('fits_corner_coords[%d][01][RA,Dec] = %.10f, %.10f, image = %r'%(i, fits_corner_coords[2][0], fits_corner_coords[2][1], input_fits_cube_list[i]))
        print2('fits_corner_coords[%d][10][RA,Dec] = %.10f, %.10f, image = %r'%(i, fits_corner_coords[3][0], fits_corner_coords[3][1], input_fits_cube_list[i]))
        fits_header_list.append(copy.copy(fits_header))
        fits_wcs_2D_list.append(copy.copy(fits_wcs_2D))
        fits_pixscale_list.append(proj_plane_pixel_scales(fits_wcs_2D)[1]*3600.0) # arcsec
        fits_dimension_list.append(fits_header['NAXIS'])
        fits_corner_00_RA_list.append(fits_corner_coords[0][0]) # note that RA increases to the left, so this corner has the largest RA. 
        fits_corner_00_Dec_list.append(fits_corner_coords[0][1])
        fits_corner_11_RA_list.append(fits_corner_coords[1][0])
        fits_corner_11_Dec_list.append(fits_corner_coords[1][1])
        fits_corner_01_RA_list.append(fits_corner_coords[2][0]) # note that RA increases to the left, so this corner has the largest RA. 
        fits_corner_01_Dec_list.append(fits_corner_coords[2][1])
        fits_corner_10_RA_list.append(fits_corner_coords[3][0])
        fits_corner_10_Dec_list.append(fits_corner_coords[3][1])
    # 
    # make sure pixel scales are the same, otherwise <TODO>
    for i in range(ninput):
        if not np.isclose(fits_pixscale_list[i], fits_pixscale_list[0]):
            raise Exception('Error! Pixel scales are inconsistent! Values are %s for input fits cubes %s.'%(fits_pixscale_list, input_fits_cube_list))
    # 
    # make sure all are images or cubes, and if cubes all channels are consistent
    naxis = 0
    if np.min(fits_dimension_list) < 2:
        raise Exception('Error! Data dimensions are smaller than 2! Dimensions are %s for input fits cubes %s.'%(fits_dimension_list, input_fits_cube_list))
    elif np.min(fits_dimension_list) == 2:
        naxis = 2
        for i in range(ninput):
            if fits_dimension_list[i] != 2:
                raise Exception('Error! Data dimensions are inconsistent! Dimensions are %s for input fits cubes %s.'%(fits_dimension_list, input_fits_cube_list))
    else:
        naxis = 3
        nchan = fits_header_list[0]['NAXIS3']
        for i in range(ninput):
            if fits_header_list[i]['NAXIS3'] != nchan:
                raise Exception('Error! The third dimension of the data cubes are inconsistent! NAXIS3 are %s for input fits cubes %s.'%(str([t['NAXIS3'] for t in fits_header_list]), input_fits_cube_list))
    print2('naxis = %d'%(naxis))
    # 
    # compute output image sizes and prepare output fits header and wcs
    pixscale = np.max(np.abs(fits_pixscale_list))
    argmin_RA = np.argmin(fits_corner_11_RA_list).flatten()[0] # upper right
    argmin_Dec = np.argmin(fits_corner_00_Dec_list).flatten()[0]
    argmax_RA = np.argmax(fits_corner_01_RA_list).flatten()[0] # upper left
    argmax_Dec = np.argmax(fits_corner_11_Dec_list).flatten()[0]
    min_RA = fits_corner_11_RA_list[argmin_RA]
    min_Dec = fits_corner_00_Dec_list[argmin_Dec]
    max_RA = fits_corner_01_RA_list[argmax_RA]
    max_Dec = fits_corner_11_Dec_list[argmax_Dec]
    nx = (max_RA - min_RA) * np.cos(np.deg2rad(max_Dec)) * 3600.0 / pixscale
    ny = (max_Dec - min_Dec) * 3600.0 / pixscale
    nx = int(np.ceil(nx))
    ny = int(np.ceil(ny))
    if naxis == 2:
        output_slices = np.full([ninput, ny, nx], 0.0)
        output_weights = np.full([ninput, ny, nx], 0.0)
        output_data = np.full([ny, nx], np.nan)
        output_mean = np.full([ny, nx], 0.0)
        output_cov = np.full([ny, nx], 0)
    elif naxis == 3:
        output_slices = np.full([ninput, nchan, ny, nx], 0.0)
        output_weights = np.full([ninput, nchan, ny, nx], 0.0)
        output_data = np.full([nchan, ny, nx], np.nan)
        output_mean = np.full([nchan, ny, nx], 0.0)
        output_cov = np.full([nchan, ny, nx], 0)
    else:
        raise NotImplementedError('NAXIS %d not implemented!'%(naxis))
    # 
    # copy header keywords, recalculate the reference pixel coordinate using the left-most image (argmax_RA)
    output_hdu = fits.PrimaryHDU(data = output_data)
    output_header = copy.copy(output_hdu.header)
    if argmax_RA != argmin_Dec:
        corner_00_offset_in_Dec = (fits_corner_00_Dec_list[argmax_RA] - fits_corner_00_Dec_list[argmin_Dec]) # argmin_Dec defines the lower boudary of the output image, argmax_RA defines the left boudary. 
        corner_00_offset_in_y = corner_00_offset_in_Dec * 3600.0 / pixscale
        corner_00_offset_in_y = int(np.ceil(corner_00_offset_in_y))
        print('corner_00_offset_in_Dec = %s'%(corner_00_offset_in_Dec))
        print('corner_00_offset_in_y = %s'%(corner_00_offset_in_y))
    else:
        corner_00_offset_in_y = 0
    # 
    for i in range(1, naxis+1):
        for t in ['CTYPE', 'CUNIT', 'CRVAL', 'CRPIX', 'CDELT']:
            key = '%s%d'%(t, i)
            if key in fits_header_list[0]:
                output_header[key] = fits_header_list[0][key]
    # 
    output_header['CRPIX1'] = fits_header_list[0]['CRPIX1']
    output_header['CRPIX2'] = fits_header_list[0]['CRPIX2'] + corner_00_offset_in_y
    # 
    for key in ['EQUINOX', 'RADESYS', 'LONPOLE', 'LATPOLE', 'RESTFRQ', 'SPECSYS', 'ALTRVAL', 'ALTRPIX', 'VELREF', 'TELESCOP', 'INSTRUME', 'OBSERVER', 'DATE-OBS', 'TIMESYS', 'OBSRA', 'OBSDEC', 'OBSGEO-X', 'OBSGEO-Y', 'OBSGEO-Z', 'OBJECT']:
        if key in fits_header_list[0]:
            output_header[key] = fits_header_list[0][key]
    # 
    output_header['DATE'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + 'T' + time.strftime('%Z')
    output_header['ORIGIN'] = 'dzliu_linear_mosaic.dzliu_linear_mosaic()'
    # 
    #print(output_header)
    # 
    #for i in range(len()):
    #for t in ['RESTFRQ', 'SPECSYS', ]
    #for t in ['BMAJ', 'BMIN', 'BPA', ]
    # 
    # save to disk
    output_hdu = fits.PrimaryHDU(data = output_data, header = output_header)
    print2('writing cache blank fits file...')
    output_hdu.writeto(output_fits_cube+'.cache.blank.fits', overwrite = True)
    # 
    # Get WCS
    #output_wcs = WCS(output_header, naxis=naxis)
    # 
    # project each input data cube to the output data cube pixel coordinate
    #for i in range(ninput):
    #    project_fits_cube(input_fits_cube_list[i], 
    #                      output_fits_cube+'.cache.blank.fits', 
    #                      output_fits_cube+'.cache.projected.%d.fits'%(i), 
    #                      overwrite = True)
    # 
    # project and coadd
    for i in range(ninput):
        fits_image = None
        fits_pb = None
        with fits.open(input_fits_cube_list[i]) as hdulist:
            hdu = hdulist[0]
            fits_image = project_fits_cube_data(hdu.data, hdu.header, output_header)
        # 
        with fits.open(input_fits_pb_list[i]) as hdulist:
            hdu = hdulist[0]
            fits_pb = project_fits_cube_data(hdu.data, hdu.header, output_header)
        # 
        print('fits_image.shape = %s'%(str(list(fits_image.shape))))
        print('fits_pb.shape = %s'%(str(list(fits_pb.shape))))
        # 
        while len(fits_image.shape) > naxis:
            fits_image = fits_image[0]
        while len(fits_pb.shape) > naxis:
            fits_pb = fits_pb[0]
        # 
        print('fits_image.shape = %s'%(str(list(fits_image.shape))))
        print('fits_pb.shape = %s'%(str(list(fits_pb.shape))))
        # 
        mask = ~np.isnan(fits_image)
        output_cov[mask] += 1
        output_weights[i][mask] = (fits_pb[mask])**2
        output_slices[i][mask] = fits_image[mask]
        output_mean[mask] += fits_image[mask]
    # 
    # normalize weights
    mask_4D = (output_weights>0)
    mask_3D = (output_cov>0)
    output_weightsum_3D = np.sum(output_weights, axis=0)
    print('mask_4D.shape', mask_4D.shape)
    print('mask_3D.shape', mask_3D.shape, 'np.count_nonzero(mask_3D)', np.count_nonzero(mask_3D))
    print('output_weightsum_3D.shape', output_weightsum_3D.shape, 'np.count_nonzero(output_weightsum_3D)', np.count_nonzero(output_weightsum_3D))
    output_weights = output_weights / output_weightsum_3D
    # 
    # weighted mean
    output_data[mask_3D] = np.sum(output_slices * output_weights, axis=0)[mask_3D]
    # 
    # simple mean
    output_mean[mask_3D] = output_mean[mask_3D] / output_cov[mask_3D].astype(float)
    # 
    # Output the interpolated mask cube as a fits file
    print2('writing final coadded weighted-mean...')
    output_hdu = fits.PrimaryHDU(data = output_data, header = output_header)
    output_hdu.writeto(output_fits_cube+'.coadd.fits', overwrite = True)
    print2('Output to "%s"!'%(output_fits_cube+'.coadd.fits'))
    # 
    print2('writing final coadded simple-mean file...')
    output_hdu = fits.PrimaryHDU(data = output_mean, header = output_header)
    output_hdu.writeto(output_fits_cube+'.mean.fits', overwrite = True)
    print2('Output to "%s"!'%(output_fits_cube+'.mean.fits'))
    # 
    print2('writing final coadded coverage file...')
    output_hdu = fits.PrimaryHDU(data = output_cov, header = output_header)
    output_hdu.writeto(output_fits_cube+'.cov.fits', overwrite = True)
    print2('Output to "%s"!'%(output_fits_cube+'.cov.fits'))







############
#   main   #
############

dzliu_main_func_name = 'dzliu_linear_mosaic' # make sure this is the right main function in this script file

if __name__ == '__main__':
    if 'casa' in globals():
        # We are already in CASA and are called via execfile
        dzliu_main_func = globals()[dzliu_main_func_name]
        dzliu_main_func(globals())
    else:
        print('Please run this in CASA via:')
        print('(Python2)')
        print('    execfile(\'%s\')'%(os.path.basename(__file__)))
        print('(Python3)')
        print('    from %s import %s'%(re.sub(r'\.py$', r'', os.path.basename(__file__)), dzliu_main_func_name) )
        print('    %s(globals())'%(dzliu_main_func_name) )
        raise Exception('Please see message above.')




