#!/usr/bin/env python
# 
# Last update: 2021-03-28
# 

from __future__ import print_function
import os, sys, re, time, json, shutil
# pkg_resources
#pkg_resources.require('astroquery')
#pkg_resources.require('keyrings.alt')
import astroquery
import requests
from astroquery.alma.core import Alma
import astropy.io.ascii as asciitable
from astropy.table import Table, Column
from datetime import datetime
from operator import itemgetter, attrgetter
import glob
import numpy as np

# try to overcome glob.glob recursive search issue
if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 5):
    #import formic
    import glob2


# 
# read input argument, which should be Member_ous_id
# 
if len(sys.argv) <= 1:
    print('Usage: alma_archive_run_vla_pipeline_with_meta_table.py "meta_table_file.txt"')
    print('Options: [-vla-pipeline-path] [-casa-path] [-dataset] [-verbose]')
    print('Notes: the "meta_table_file.txt" must have following columns: ')
    sys.exit()

meta_table_file = ''
some_option = ''
output_full_table = True
EVLA_pipeline_path = '' # default
CASA_path = ''
Dataset_selection = ''
verbose = 0
i = 1
while i < len(sys.argv):
    tmp_arg = re.sub(r'^-+', r'', sys.argv[i].lower())
    if tmp_arg == 'some-option': 
        i = i+1
        if i < len(sys.argv):
            some_option = sys.argv[i]
    elif tmp_arg == 'vla-pipeline-path': 
        i = i+1
        if i < len(sys.argv):
            EVLA_pipeline_path = sys.argv[i]
    elif tmp_arg == 'casa-path': 
        i = i+1
        if i < len(sys.argv):
            CASA_path = sys.argv[i]
    elif tmp_arg == 'data-set' or tmp_arg == 'dataset': 
        i = i+1
        if i < len(sys.argv):
            Dataset_selection = sys.argv[i]
    elif tmp_arg == 'verbose': 
        verbose = verbose + 1
    else:
        meta_table_file = sys.argv[i]
    i = i+1
if meta_table_file == '':
    print('Error! No meta table file given!')
    sys.exit()


# 
# deal with sys.path
# 
#print(sys.path)
#sys.path.insert(0,os.path.dirname(os.path.abspath(sys.argv[0]))+'/Python/2.7/site-packages')
#print(sys.path)
#sys.exit()



# 
# check VLA Scripted Calibration Pipeline in ~/Softwares/CASA/Portable/EVLA_pipeline*
# see https://science.nrao.edu/facilities/vla/data-processing/pipeline/scripted-pipeline
# do not forget to make sure pipepath is set correctly in EVLA_pipeline.py
# 
if EVLA_pipeline_path == '':
    #EVLA_pipeline_path = os.path.expanduser('~')+'/Software/CASA/Portable/EVLA_pipeline1.4.0_CASA5.0.0' # try this path
    EVLA_pipeline_path = os.path.expanduser('~/Software/CASA/Portable/EVLA_pipeline1.4.2_CASA5.3.0') # 2023-09
    if not os.path.isdir(EVLA_pipeline_path):
        EVLA_pipeline_path = ''
if EVLA_pipeline_path == '':
    print('Error! EVLA_pipeline_path not given! Please input -vla-pipeline-path!')
    sys.exit(255)

if CASA_path == '':
    #CASA_path = os.path.expanduser('~')+'/Software/CASA/Portable/casa-release-5.0.0-218.el6' # try this path
    CASA_path = os.path.expanduser('~/Software/CASA/Portable/casa-release-5.3.0-143.el7')
    if not os.path.isdir(CASA_path):
        CASA_path = ''
if CASA_path == '':
    print('Error! CASA_path not given! Please input -casa-path!')
    sys.exit(255)




# 
# read meta table file
# 
meta_table = None
if meta_table_file.endswith('.fits'):
    meta_table = Table.read(meta_table_file)
else:
    try:
        meta_table = Table.read(meta_table_file, format='ascii.commented_header')
    except:
        try:
            meta_table = Table.read(meta_table_file, format='ascii')
        except:
            pass
if meta_table is None:
    print('Error! Failed to read the meta table file! Is it a fits catalog or ascii catalog?')
    sys.exit()

#print(meta_table)
#print(meta_table.colnames)

Project_code = None
if 'Project_code' in meta_table.colnames:
    Project_code = meta_table['Project_code']

Member_ous_id = None
if 'Member_ous_id' in meta_table.colnames:
    Member_ous_id = meta_table['Member_ous_id']

Source_name = None
if 'Source_name' in meta_table.colnames:
    Source_name = meta_table['Source_name']

Array = None
if 'Array' in meta_table.colnames:
    Array = meta_table['Array']

Dataset_dirname = None
if 'Dataset_dirname' in meta_table.colnames:
    Dataset_dirname = meta_table['Dataset_dirname']

if Project_code is None or \
   Member_ous_id is None or \
   Source_name is None or \
   Array is None or \
   Dataset_dirname is None: 
    print('Error! The input meta data table should contain at least the following four columns: "Project_code" "Member_ous_id" "Source_name" "Array" "Dataset_dirname"!')
    sys.exit()



def my_function_to_make_symbolic_link(src, dst, verbose = 0):
    if os.path.islink(dst):
        #print(os.readlink(dst))
        #print(os.path.exists(dst))
        if not os.path.exists(dst):
            os.remove(dst)
        elif os.readlink(dst) != src:
            print('Rewriting the link "%s" which was linked to "%s".'%(dst, os.readlink(dst)))
            os.remove(dst)
    if not os.path.islink(dst):
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        if verbose >= 1 :
            print('Linking "%s" to "%s".'%(dst, src))
        os.symlink(src, dst)
        #print('ln -fsT "%s" "%s"'%(src, dst))
        #os.system('ln -fsT "%s" "%s"'%(src, dst))
    else:
        print('Found existing link "%s" to "%s".'%(dst, src))



# 
# check Level_2_Calib dir
# 
if not os.path.isdir('Level_2_Calib'):
    print('Error! Level_2_Calib does not exist! Please run \"alma_archive_make_data_dirs_with_meta_table.py\" first!')
    sys.exit()


# 
# cd Level_2_Calib and run EVLA_pipeline_path+os.sep+'EVLA_pipeline.py'
# 
output_table = meta_table.copy()
#output_table['Downloaded'] = [False]*len(output_table)
#output_table['Unpacked'] = [False]*len(output_table)
output_table['Calibrated'] = [False]*len(output_table)
#output_table['Imaged'] = [False]*len(output_table)

for i in range(len(output_table)):
    t_Project_code = Project_code[i]
    t_Dataset_name = re.sub(r'[^a-zA-Z0-9._+-]', r'_', Member_ous_id[i])
    t_Source_name = re.sub(r'[^a-zA-Z0-9._+-]', r'_', Source_name[i])
    t_Source_name = re.sub(r'^_*(.*?)_*$', r'\1', t_Source_name)
    t_Array = Array[i]
    # reformat Source_name
    if re.match(r'[0-9]$', t_Source_name):
        t_Galaxy_name = t_Source_name
    else:
        t_Galaxy_name = t_Source_name
    # 
    # prepare Dataset dirname
    #t_Dataset_ID_digits = np.ceil(np.log10(1.0*len(output_table))+1.0)
    #if t_Dataset_ID_digits < 2: t_Dataset_ID_digits = 2
    #t_Dataset_dirname = ('DataSet_%%0%dd'%(t_Dataset_ID_digits))%(i+1)
    # 
    # set Dataset_dirname
    t_Dataset_dirname = Dataset_dirname[i]
    # 
    # select by user input Dataset_selection
    if Dataset_selection != '':
        if re.match(r'[0-9]+', Dataset_selection) and re.match(r'.*_([0-9]+)$', t_Dataset_dirname):
            if int(re.sub(r'.*_([0-9]+)$', r'\1', t_Dataset_dirname)) != int(Dataset_selection):
                continue
        else:
            if t_Dataset_dirname != Dataset_selection:
                continue
    # 
    # check t_Dataset_dirname
    if not os.path.isdir('Level_2_Calib/'+t_Dataset_dirname):
        print('Error! Data folder/link not found: %r. Please run previous step "alma_archive_make_data_dirs_with_meta_table.py" first.'%('Level_2_Calib/'+t_Dataset_dirname))
        sys.exit(255)
    # 
    # set t_Dataset_dirpath
    t_Dataset_dirpath = 'Level_2_Calib/'+t_Dataset_dirname
    # 
    # write t_Dataset_dirpath/README_CASA_VERSION
    if not os.path.isfile(t_Dataset_dirpath+'/README_CASA_VERSION'):
        with open(t_Dataset_dirpath+'/README_CASA_VERSION', 'w') as fp:
            fp.write('CASA version 5.3.0\n') #<TODO><UPDATE>#
    # 
    # check calibrated/calibrated.ms
    t_calibrated_dir = 'Level_2_Calib/'+t_Dataset_dirname+'/calibrated'
    t_calibrated_ms = t_calibrated_dir+'/calibrated.ms'
    print('Checking '+t_calibrated_ms)
    if os.path.isdir(t_calibrated_ms):
        if len(os.listdir(t_calibrated_ms)) > 0:
            print('Found non-empty data folder: %r. Skip calibrating it.'%(t_calibrated_ms))
            output_table['Calibrated'][i] = True
            continue
    
    # 
    # link raw to calibrated dir
    t_raw_path = 'Level_1_Raw/'+t_Dataset_name
    t_calib_raw_path = 'Level_2_Calib/'+t_Dataset_dirname+'/raw'
    t_calib_sdm_path = t_calibrated_dir+os.sep+t_Dataset_name
    if not os.path.isdir(t_calib_raw_path) and not os.path.islink(t_calib_raw_path):
        #os.symlink('../../'+t_raw_path, t_calib_raw_path)
        my_function_to_make_symbolic_link('../../'+t_raw_path, t_calib_raw_path)
    if not os.path.isdir(t_calib_sdm_path) and not os.path.islink(t_calib_sdm_path):
        #os.symlink('../raw', t_calib_sdm_path)
        my_function_to_make_symbolic_link('../raw', t_calib_sdm_path)
    
    # 
    # 
    print('Ready to run VLA calibration pipeline under "%s"'%(t_calibrated_dir))
    current_dir = os.getcwd()
    
    os.chdir(t_calibrated_dir)
    
    t_run_script = 'run_vla_pipeline_in_casa.py'
    if os.path.isfile(t_run_script):
        shutil.move(t_run_script, t_run_script+'.backup')
    with open(t_run_script, 'w') as fp:
        fp.write('# RUN THIS SCRIPT INSIDE CASA AS: \n')
        fp.write('#     exec(open("%s").read())\n'%(t_run_script))
        fp.write('# \n')
        fp.write('\n')
        fp.write('SDM_name = "%s"\n'%(t_Dataset_name))
        fp.write('mymodel = "y"\n')
        fp.write('myHanning = "n"\n')
        fp.write('\n')
        fp.write('exec(open("%s").read())\n'%(EVLA_pipeline_path+'/EVLA_pipeline.py'))
        fp.write('\n')
        fp.write('import os\n')
        fp.write('os.symlink("%s", "calibrated.ms")\n'%(t_Dataset_name+'.ms'))
        fp.write('\n')
        fp.write('\n')
    
    t_casa_bin_path = CASA_path+'/bin'
    
    # Note: can not use: casa --nogui --log2term : because VLA pipeline needs GUI.
    t_command = 'cd "%s"; export PATH="%s:$PATH"; casa -c "exec(open(\\\"%s\\\").read())" | tee "log_run_vla_pipeline_in_casa.txt"'%(\
                    os.getcwd(), \
                    t_casa_bin_path, \
                    t_run_script \
                    )
    print('Command: '+t_command)
    os.system(t_command)
    
    os.chdir(current_dir)
                            




print(output_table)







