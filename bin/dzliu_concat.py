#!/usr/bin/env python
# 
# This needs to be run in CASA
# 
# CASA modules/functions used:
#     tb, casalog, concat, inp, saveinputs
# 
# Example:
#     sys.path.append('/Users/dzliu/Cloud/Github/Crab.Toolkit.CASA/lib/python')
#     import dzliu_concat; reload(dzliu_concat); dzliu_concat.dzliu_concat(dataset_ms)
# 
from __future__ import print_function
import os, sys, re, json, copy, timeit, shutil
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
    from concat_cli import concat_cli_
    concat = concat_cli_()
    from split_cli import split_cli_
    split = split_cli_()
    from imstat_cli import imstat_cli_
    imstat = imstat_cli_()
else:
    # see CASA 6 updates here: https://alma-intweb.mtk.nao.ac.jp/~eaarc/UM2018/presentation/Nakazato.pdf
    from casatasks import tclean, mstransform, exportfits, concat, split, imstat
    #from casatasks import sdbaseline
    #from casatools import ia



# 
# def print2
# 
def print2(message):
    print(message)
    casalog.post(message, 'INFO')









def dzliu_concat(vis, 
                 concatvis, 
                 overwrite = False):
    # 
    casalog.origin('dzliu_concat')
    
    # 
    # Prepare output dir and name
    if concatvis == '':
        output_dir = 'run_concat'
    elif concatvis.find(os.sep) >= 0:
        output_dir = os.path.dirname(concatvis)
    else:
        output_dir = '.'
    
    if output_dir != '.':
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
    
    # then concatenate
    concat_parameters = {}
    concat_parameters['vis'] = vis
    concat_parameters['concatvis'] = concatvis
    print2('concat_parameters = %s'%(concat_parameters))
    
    with open(output_dir+os.sep+'saved_concat_inputs.json', 'w') as fp:
        json.dump(concat_parameters, fp, indent = 4)
    
    concat(**concat_parameters)
    
    if not os.path.isdir(concatvis):
        raise Exception('Error! Failed to run concat and produce "%s"!'%(concatvis))
    else:
        print2('Output to "%s"!'%(concatvis))











############
#   main   #
############

dzliu_main_func_name = 'dzliu_concat' # make sure this is the right main function in this script file

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




