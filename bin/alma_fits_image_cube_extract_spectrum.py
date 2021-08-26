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
from astropy import units as u
from astropy.coordinates import Angle
import regions
from regions import PointSkyRegion, PointPixelRegion, CircleSkyRegion, CirclePixelRegion, EllipseSkyRegion, EllipsePixelRegion, PolygonSkyRegion, PolygonPixelRegion # https://astropy-regions.readthedocs.io/en/latest/shapes.html
from regions import DS9Parser, ds9_objects_to_string
from regions import read_ds9, write_ds9


# Read user input
input_fits_file = ''
input_points = []
input_circles = []
input_sky_points = []
input_sky_circles = []
input_regions = []
output_name = ''
extract_method = 'sum'
beam_size = []
make_plot = False
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
    elif arg_str.startswith('-point'):
        arg_mode = 'point'
        continue
    # 
    elif arg_str.startswith('-sky-point'):
        arg_mode = 'sky-point'
        continue
    # 
    elif arg_str.startswith('-circle'):
        arg_mode = 'circle'
        continue
    # 
    elif arg_str.startswith('-sky-circle'):
        arg_mode = 'sky-circle'
        continue
    # 
    elif arg_str.startswith('-region'):
        arg_mode = 'region'
        continue
    # 
    elif arg_str.startswith('-method'):
        arg_mode = 'method'
        continue
    # 
    elif arg_str.startswith('-beam'):
        arg_mode = 'beam'
        continue
    # 
    elif arg_str.startswith('-plot'):
        arg_mode = 'plot'
    # 
    elif arg_mode == '':
        arg_mode = 'in'
    # 
    # parse arg_mode
    if arg_mode == 'in':
        input_fits_file = sys.argv[i]
        arg_mode = ''
    elif arg_mode == 'out':
        output_name = sys.argv[i]
        arg_mode = ''
    elif arg_mode == 'point':
        input_points.append(float(sys.argv[i]))
    elif arg_mode == 'circle':
        input_circles.append(float(sys.argv[i]))
    elif arg_mode == 'sky-point':
        input_sky_points.append(sys.argv[i]) # string
    elif arg_mode == 'sky-circle':
        input_sky_circles.append(sys.argv[i]) # string
    elif arg_mode == 'region':
        parser = DS9Parser(sys.argv[i]) # DS9 region format string
        for parser_region in parser.shapes.to_regions():
            input_regions.append(parser_region)
    elif arg_mode == 'method':
        extract_method = sys.argv[i].lower()
        if not (extract_method in ['sum', 'mean', 'median']):
            print('Error! The input -method must be one of:', "['sum', 'mean', 'median']")
            sys.exit()
    elif arg_mode == 'beam':
        beam_size.append(float(sys.argv[i]))
    elif arg_mode == 'plot':
        make_plot = True
        arg_mode = ''
    

# Check user input
if input_fits_file == '' or ( len(input_regions) == 0 and len(input_points) == 0 and len(input_circles) == 0 and len(input_sky_points) == 0 and len(input_sky_circles) == 0 ):
    print('Usage:')
    print('    alma_fits_image_cube_extract_spectrum.py INPUT_FITS_IMAGE_CUBE.fits -pos 100 100 -out OUTPUT_NAME')
    print('    alma_fits_image_cube_extract_spectrum.py INPUT_FITS_IMAGE_CUBE.fits -offset 0 0 -out OUTPUT_NAME')
    print('    alma_fits_image_cube_extract_spectrum.py INPUT_FITS_IMAGE_CUBE.fits -region "fk5; circle(150.00,02.000,3\")" -out OUTPUT_NAME')
    print('Note:')
    print('    This code will extract spectrum form the input fits image cube.')
    print('    Notice that the input position is the pixel coordinate with 1-based, same as ds9.')
    print('')
    sys.exit()

if len(input_points) % 2 != 0:
    print('Error! The input -point array size should be n times 3!')
    sys.exit()

if len(input_circles) % 3 != 0:
    print('Error! The input -circle array size should be n times 3!')
    sys.exit()


# Set default output name
if output_name == '':
    output_name = re.sub(r'\.fits$', r'', os.path.basename(input_fits_file), re.IGNORECASE) + '_extracted_spectrum'


#print('input_fits_file = "%s"'%(input_fits_file))
#print('output_name = "%s"'%(output_name))


# Open fits file and extract the spectrum
with fits.open(input_fits_file) as hdulist:
    # 
    print(hdulist.info())
    hdu0 = hdulist[0]
    # 
    # check dimension
    if len(hdu0.data.shape) < 3:
        print('Error! The input fits file "%s" is not a data cube! Exit!'%(input_fits_file))
        sys.exit()
    # 
    # fix header
    #if not ('cpdis1' in hdu0.header):
    #    hdu0.header['cpdis1'] = ''
    # 
    wcs0 = WCS(hdu0.header, naxis=2)
    #print(wcs0.wcs.name)
    #wcs0.wcs.print_contents()
    #print(wcs0.wcs.naxis)
    cenx = ((hdu0.header['NAXIS1']+1.0)/2.0) # 1-based
    ceny = ((hdu0.header['NAXIS2']+1.0)/2.0) # 1-based
    
    # get all-image pixel coordinate mesh
    py, px = np.mgrid[1:hdu0.header['NAXIS1']+1,1:hdu0.header['NAXIS2']+1]
    #print(py,px)
    pix_img = regions.PixCoord(px, py)
    pix_img_mask = np.zeros(px.shape, dtype=bool)
    
    # get pix_scale
    pix_scale = np.mean(astropy.wcs.utils.proj_plane_pixel_scales(wcs0)*3600) # arcsec
    
    # Convert pos to reg
    combined_regions = []
    combined_sky_regions = []
    for i in range(0,len(input_points),2):
        combined_regions.append(PointPixelRegion(center=regions.PixCoord(x=np.round(cenx+input_points[i]), y=np.round(ceny+input_points[i+1]))))
    for i in range(0,len(input_sky_points),2):
        combined_regions.append(PointPixelRegion(center=regions.PixCoord(x=np.round(cenx+input_sky_points[i]), y=np.round(ceny+input_sky_points[i+1]))))
    for i in range(0,len(input_circles),3):
        combined_regions.append(CirclePixelRegion(center=regions.PixCoord(x=np.round(input_circles[i]), y=np.round(input_circles[i+1])), radius=input_circles[i+2]))
    for i in range(0,len(input_sky_circles),3):
        # 
        # deal with the input RA string
        if input_sky_circles[i].find(":") >= 0:
            tposra = Angle(input_sky_circles[i]+" hours")
        else:
            tposra = Angle(input_sky_circles[i]+" degrees")
        # 
        # deal with the input Dec string
        if input_sky_circles[i+1].find(":") >= 0:
            tposdec = Angle(input_sky_circles[i+1]+" degrees")
        else:
            tposdec = Angle(input_sky_circles[i+1]+" degrees")
        # 
        #print('tposra', tposra, 'tposdec', tposdec)
        tposcoord = wcs0.wcs_world2pix(tposra.degree, tposdec.degree, 1)
        #print('tposcoord', tposcoord)
        tposx = tposcoord[0]
        tposy = tposcoord[1]
        # 
        # deal with the input radius string
        if input_sky_circles[i+2].find("\"") >= 0:
            tradius = float(input_sky_circles[i+2].replace("\"", ""))
        elif input_sky_circles[i+2].find("\'") >= 0:
            tradius = float(input_sky_circles[i+2].replace("\'", "")) * 60.0 # arcmin -> arcsec
        elif input_sky_circles[i+2].find("deg") >= 0:
            tradius = float(input_sky_circles[i+2].replace("deg", "")) * 3600.0 # degree -> arcsec
        else:
            tradius = float(input_sky_circles[i+2]) # assuming arcsec
        # 
        combined_regions.append(CirclePixelRegion(center=regions.PixCoord(x=np.round(tposx), y=np.round(tposy)), radius=tradius/pix_scale))
        # 
        combined_sky_regions.append(CircleSkyRegion(center=SkyCoord(tposra.degree, tposdec.degree, unit=u.deg), radius=tradius * u.arcsec))
        # 
    for i in range(0,len(input_regions),1):
        # 
        # <TODO>
        if type(input_regions[i]) is regions.SkyRegion:
            combined_regions.append(input_regions[i].to_pixel(wcs0)) # to_pixel converts sky coordinates to pixel coordinates
        else:
            #input_regions[i].radius = input_regions[i].radius / pix_scale # arcsec -> pixel
            combined_regions.append(input_regions[i])
    
    # Loop each regions
    for i in range(len(combined_regions)):
        # 
        pix_reg = combined_regions[i]
        print('------')
        print(pix_reg)
        print('area:', pix_reg.area)
        
        # compute mask boolean array
        #print(pix_reg.to_mask()) # NotImplementedError as of 20190503
        if pix_reg.area > 0:
            pix_reg_mask = pix_reg.contains(pix_img)
            pix_img_mask = np.logical_or(pix_img_mask, pix_reg_mask)
            print('mask:', np.count_nonzero(pix_reg_mask))
            #print('pix_reg.contains(pix_img)', pix_reg.contains(regions.PixCoord([300,],[300,])))
        else:
            pix_i = int(pix_reg.center.x-1)
            pix_j = int(pix_reg.center.y-1)
            pix_img_mask[pix_j, pix_i] = True # note that Python array subscription first y then x
            print('mask:', 1)
            #print('pix_img_mask[%d, %d] = True'%(pix_reg.center.y-1, pix_reg.center.x-1))
    print('------')
    
    pix_img_mask_count = np.count_nonzero(pix_img_mask)
    print('Total mask:', pix_img_mask_count)
    
    
    # now extend the mask to the data cube shape
    if len(hdu0.data.shape) >= 4:
        data_cube = hdu0.data[0,:,:,:]
    else:
        data_cube = hdu0.data
    data_cube_channel_number = data_cube.shape[0]
    data_cube_mask = np.repeat(pix_img_mask[np.newaxis, :, :], data_cube_channel_number, axis=0)
    print('pix_img_mask.shape', pix_img_mask.shape)
    print('data_cube.shape', data_cube.shape)
    print('data_cube_mask.shape', data_cube_mask.shape)
    data_cube_masked = data_cube[data_cube_mask].reshape((data_cube_channel_number,pix_img_mask_count))
    print('data_cube_masked.shape', data_cube_masked.shape)
    if extract_method == 'sum':
        extracted_spectrum = np.sum(data_cube_masked, axis=1)
    elif extract_method == 'mean':
        extracted_spectrum = np.mean(data_cube_masked, axis=1)
    elif extract_method == 'median':
        extracted_spectrum = np.median(data_cube_masked, axis=1)
    print('extracted_spectrum.shape', extracted_spectrum.shape)
    
    
    
    # now calculate the 3rd axis coordinate
    wcs3 = WCS(hdu0.header, naxis=3)
    #astropy.wcs.utils.pixel_to_skycoord(xp, yp, wc)
    pixcoord3d = np.zeros((data_cube_channel_number,3), dtype=int) # pairs of x,y,v
    pixcoord3d[:,0] = cenx
    pixcoord3d[:,1] = ceny
    pixcoord3d[:,2] = np.arange(0,data_cube_channel_number)+1
    skycoord3d = wcs3.wcs_pix2world(pixcoord3d, 1) # 1-based
    skycoord3 = skycoord3d[:,2]
    
    
    # output to ascii file
    if re.match(r'^.*\.txt$', output_name, re.IGNORECASE):
        output_name = re.sub(r'\.txt$', r'', output_name, re.IGNORECASE)
    
    output_X_column_name = 'coordinate'
    output_Y_column_name = 'value'
    output_notes = []
    if 'CTYPE3' in hdu0.header: 
        output_X_column_name = hdu0.header['CTYPE3'].strip()
    if 'CUNIT3' in hdu0.header: 
        output_X_column_name = output_X_column_name + '_' + re.sub(r'[\/^.-]', r'_', hdu0.header['CUNIT3'].strip())
    
    if 'BTYPE' in hdu0.header: 
        output_Y_column_name = hdu0.header['BTYPE'].strip()
    if 'BUNIT' in hdu0.header: 
        # if 'BUNIT' is 'Jy/beam' and method is 'sum', we have to take care of beam area vs pixel area flux conversion
        
        if hdu0.header['BUNIT'].strip().lower().startswith('jy/beam') and extract_method == 'sum':
            if not ('BMAJ' in hdu0.header and 'BMIN' in hdu0.header) and \
               not (len(beam_size)>=2):
                print('Error! Could not find BMAJ and BMIN in the fits header when computing beam area for the sum with BUNIT Jy/beam!')
                print('Please input the corresponding beam size with the argument -beam XXX XXX, where XXX is the beam size in units of arcsec.')
                sys.exit()
            else:
                if (len(beam_size)>=2):
                    beam_major = beam_size[0]
                    beam_minor = beam_size[1]
                else:
                    beam_major = hdu0.header['BMAJ']*3600
                    beam_minor = hdu0.header['BMIN']*3600
            # 
            beam_area = np.pi / (4*np.log(2)) * beam_major * beam_minor # arcsec^2
            pixel_area = astropy.wcs.utils.proj_plane_pixel_area(wcs0)*3600*3600 # arcsec^2
            extracted_spectrum = extracted_spectrum / (beam_area / pixel_area)
            output_notes.append('beam_area = %s'%(beam_area))
            output_notes.append('pixel_area = %s'%(pixel_area))
            output_notes.append('applied flux conversion: extracted_spectrum = extracted_spectrum / (beam_area / pixel_area)')
            
            output_Y_column_name = output_Y_column_name + '_' + re.sub(r'[\/^.-]', r'_', re.sub(r'^Jy/beam', r'Jy', hdu0.header['BUNIT'].strip(), re.IGNORECASE) )
            
        else:
            
            output_Y_column_name = output_Y_column_name + '_' + re.sub(r'[\/^.-]', r'_', hdu0.header['BUNIT'].strip())
    
    output_dict = {}
    output_dict[output_X_column_name] = skycoord3
    output_dict[output_Y_column_name] = extracted_spectrum
    output_table = Table(output_dict)
    output_table.write(output_name+'.txt', format='ascii.fixed_width', delimiter=' ', bookend=True, overwrite=True)
    with open(output_name+'.txt', 'r+') as ofp:
        ofp.seek(0)
        ofp.write('#')
    print('Output to "%s"!'%(output_name+'.txt'))
    
    
    # output combined_regions as well
    write_ds9(combined_regions, output_name+'.regions.txt', coordsys='image', radunit='')
    print('Output to "%s"!'%(output_name+'.regions.txt'))
    
    
    # output readme file
    with open(output_name+'.readme.txt', 'w') as ofp:
        ofp.write('Extracted the spectrum from the following fits cube file at %s:\n'%(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')))
        ofp.write('    %s\n'%(input_fits_file))
        ofp.write('\n')
        ofp.write('within regions listed in:\n')
        ofp.write('    %s\n'%(output_name+'.regions.txt'))
        ofp.write('\n')
        ofp.write('with the method:\n')
        ofp.write('    %s\n'%(extract_method))
        ofp.write('\n')
        ofp.write('by the code:\n')
        ofp.write('    %s\n'%(os.path.abspath(__file__)))
        ofp.write('\n')
        if len(output_notes) > 0:
            ofp.write('\n')
            ofp.write('Notes: \n')
            for output_note in output_notes:
                ofp.write('    %s\n'%(output_note))
            ofp.write('\n')
    print('Output to "%s"!'%(output_name+'.readme.txt'))
    
    
    
    # make plot if the user said so
    if make_plot:
        
        import matplotlib
        import matplotlib.pyplot as plt
        
        fig = plt.figure(figsize=(15.0, 4.0))
        ax = fig.add_subplot(1,1,1)
        ax.plot(skycoord3, skycoord3*0.0, linestyle='solid', linewidth=0.9, color='#555555')
        ax.step(skycoord3, extracted_spectrum)
        ax.tick_params(axis='both', which='major', direction='in', labelsize=13)
        for i in range(np.min([10,len(combined_sky_regions)])):
            ax.text(0.015, 0.915 - i*0.045, 'Region %s, radius %s'%(combined_sky_regions[i].center.to_string('hmsdms'), combined_sky_regions[i].radius), transform=ax.transAxes, fontsize=14)
        ax.xaxis.set_ticks_position('both')
        ax.yaxis.set_ticks_position('both')
        ax.set_xlabel(output_X_column_name, fontsize=15, labelpad=10)
        ax.set_ylabel(output_Y_column_name, fontsize=15, labelpad=10)
        fig.tight_layout()
        fig.savefig(output_name+'.pdf', dpi=250, overwrite=True)
        
        print('Output to "%s"!'%(output_name+'.pdf'))
        
        os.system('open "%s"'%(output_name+'.pdf'))
    
    
    if fit_gaussian:
        
        import scipy









