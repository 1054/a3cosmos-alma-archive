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
    print('Please run "alma_archive_run_tclean_for_continuum.sh" instead of "alma_archive_run_tclean_for_continuum.py"!')
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
    
    list_of_images = []
    if os.path.isfile('list_of_images.json'):
        shutil.move('list_of_images.json', 'list_of_images.json.backup')
    #if os.path.isfile('list_of_images.json'):
    #    with open('list_of_images.json', 'r') as fp:
    #        list_of_images = json.load(fp)
    
    # 
    failed_fields = []
    for field in fields:
        
        field = str(field).strip()
        
        final_output_image = '%s_SB_%s_GB_%s_MB_%s_%s_sci.spw%s.cont.I.image.fits'%(project, SB, GB, MB, field, '_'.join(np.array(spw_ids).astype(str).tolist()))
        print('final_output_image = %s'%(final_output_image))
        
        if not os.path.isfile(final_output_image):
            
            if not os.path.isfile('%s_cont_clean.image.fits'%(field)):
                dzliu_clean.dzliu_clean(vis, 
                                        output_image = '%s'%(field), 
                                        galaxy_name = field, 
                                        make_line_cube = False, 
                                        make_continuum = True, 
                                        beamsize = 'common', 
                                        robust = 2.0, 
                                       )
                # 
                # output will be:
                #   '%s_cont.ms'%(field)
                #   '%s_cont.image.fits'%(field)
                # 
                if not os.path.isfile('%s_cont_clean.image.fits'%(field)):
                    print('Error! Failed to produce "%s/%s"! Will skip this one and try to continue..'%(os.path.abspath(os.getcwd()), '%s_cont_clean.image.fits'%(field)))
                    failed_fields.append(field)
                    continue
            
            shutil.copy('%s_cont_clean.image.fits'%(field), final_output_image)
            print('Output to "%s"'%(final_output_image))
            
        else:
            print('Found existing "%s"'%(final_output_image))
        # 
        list_of_images.append(final_output_image)
    
    # 
    if len(failed_fields) > 0:
        print('Error occurred. These fields were not successfully imaged from vis "%s": '%(vis))
        for field in failed_fields:
            print('  %s'%(field))
    
    # 
    if len(list_of_images) > 0:
        with open('list_of_images.json', 'w') as fp:
            json.dump(list_of_images, fp, indent=4, sort_keys=True)
        print('Output to "list_of_images.json"')
    else:
        print('Error! No image was cleaned!')







