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
    
    fields, phasecenters = dzliu_clean.get_all_fields(vis)
    
    for field in fields:
        dzliu_clean.dzliu_clean(vis, 
                                output_image = '', 
                                galaxy_name = '', 
                                make_line_cube = False, 
                                make_continuum = True, 
                                beamsize = 'common', 
                               ) 
        # output will be:
        #   output_image_cont.ms
        #   output_image_cont.image.fits


