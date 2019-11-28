#!/usr/bin/env python
# 
# This needs to be run in CASA
# 
# CASA modules/functions used:
#     tb, casalog, mstransform, inp, saveinputs, exportfits, tclean
# 
# Example:
#     import a_dzliu_code_level_4_clean; reload(a_dzliu_code_level_4_clean); from a_dzliu_code_level_4_clean import dzliu_clean; dzliu_clean()
# 
from __future__ import print_function
import os, sys, re, json, copy, timeit, shutil
import numpy as np
#from taskinit import casalog, tb #, ms, iatool
#from taskinit import casac
#tb = casac.table
#from __casac__.table import table as tb
#from recipes import makepb, pixelmask2cleanmask
#import casadef

try:
    import dzliu_clean
except:
    print('Please run "alma_archive_run_tclean_for_cube.sh" instead of "alma_archive_run_tclean_for_cube.py"!')
    sys.exit()


def go(vis):
    
    paths = os.path.abspath(vis).split(os.sep)
    if len(paths) < 7:
        raise Exception('Error! The absolute path of the input data "%s" seems do not contain project, SB, GB, MB paths!'%(vis))
    project = paths[-7]
    SB = paths[-6].split('_')[-1]
    GB = paths[-5].split('_')[-1]
    MB = paths[-4].split('_')[-1]
    calibrated_dir = paths[-3] # projec/SB/GB/MB/calibrated/run_tclean/vis.ms
    
    fields, phasecenters = dzliu_clean.get_all_fields(vis)
    
    spw_ids, spw_names, spw_nchan, spw_ref_freqs = dzliu_clean.get_all_spws(vis)
    print('spw_ids = %s'%(str(spw_ids)))
    print('spw_names = %s'%(str(spw_names)))
    print('spw_nchan = %s'%(str(spw_nchan)))
    print('spw_ref_freqs = %s'%(str(spw_ref_freqs)))
    
    list_of_cubes = []
    if os.path.isfile('list_of_cubes.json'):
        shutil.move('list_of_cubes.json', 'list_of_cubes.json.backup')
    #if os.path.isfile('list_of_cubes.json'):
    #    with open('list_of_cubes.json', 'r') as fp:
    #        list_of_cubes = json.load(fp)
    
    # 
    failed_fields = []
    for field in fields:
        
        #field = str(field).strip()
        
        for spw_id in spw_ids:
            
            final_output_name = '%s_SB_%s_GB_%s_MB_%s_%s_sci.spw%d'%(project, SB, GB, MB, field, spw_id)
            print('final_output_name = %s'%(final_output_name))
            
            if not os.path.isfile(final_output_name+'.cube.I.image.fits'):
                
                if not os.path.isfile('%s_cube_spw%d_clean.image.fits'%(field, spw_id)):
                    dzliu_clean.dzliu_clean(vis, 
                                            output_image = '%s'%(field), 
                                            galaxy_name = field, 
                                            make_line_cube = True, 
                                            make_continuum = False, 
                                            line_name = 'cube_spw%d'%(spw_id), 
                                            line_velocity = 0, 
                                            line_velocity_width = 0, 
                                            line_velocity_resolution = 30.0, 
                                            beamsize = 'common', 
                                            robust = 2.0, 
                                           )
                    # 
                    # output will be:
                    #   '%s_cube_spw%d.ms'%(field, spw_id)
                    #   '%s_cube_spw%d_clean.image.fits'%(field, spw_id)
                    # 
                    if not os.path.isfile('%s_cube_spw%d_clean.image.fits'%(field, spw_id)):
                        print('Error! Failed to produce "%s/%s"! Will skip this one and try to continue..'%(os.path.abspath(os.getcwd()), '%s_cube_spw%d_clean.image.fits'%(field, spw_id)))
                        failed_fields.append(field)
                        continue
                
                shutil.copy('%s_cube_spw%d_clean.image.fits'%(field, spw_id), final_output_name+'.cube.I.image.fits')
                shutil.copy('%s_cube_spw%d_clean.image.pbcor.fits'%(field, spw_id), final_output_name+'.cube.I.pbcor.fits')
                shutil.copy('%s_cube_spw%d_clean.pb.fits'%(field, spw_id), final_output_name+'.cube.pb.fits')
                shutil.copy('%s_cube_spw%d_clean.psf.fits'%(field, spw_id), final_output_name+'.cube.psf.fits')
                print('Output to "%s"'%(final_output_name+'.cube.I.image.fits'))
                
            else:
                print('Found existing "%s"'%(final_output_name+'.cube.I.image.fits'))
            # 
            list_of_cubes.append(final_output_name+'.cube.I.image.fits')
    
    # 
    if len(failed_fields) > 0:
        print('Error occurred. These fields were not successfully imaged from vis "%s": '%(vis))
        for field in failed_fields:
            print('  %s'%(field))
    
    # 
    if len(list_of_cubes) > 0:
        with open('list_of_cubes.json', 'w') as fp:
            json.dump(list_of_cubes, fp, indent=4, sort_keys=True)
        print('Output to "list_of_cubes.json"')
    else:
        print('Error! No cube was cleaned!')







