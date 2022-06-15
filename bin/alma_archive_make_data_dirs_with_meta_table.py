#!/usr/bin/env python
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
#if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 5):
#    #import formic
#    import glob2

# EVLA_pipeline_path = '' # default
# CASA_path = ''
# #t_EVLA_calib_script = os.getenv('HOME')+os.sep+'Software/CASA/Portable/EVLA_pipeline1.4.0_CASA5.0.0/EVLA_pipeline.py' # must first modify it and set the absolute path therein
# #t_CASA_setup_script = os.getenv('HOME')+os.sep+'Software/CASA/SETUP.bash'
# #t_CASA_dir = os.getenv('HOME')+os.sep+'Software/CASA/Portable/casa-release-5.0.0-218.el6'
# #t_CASA_version = '5.0.0'



# define functions
def find_items_in_folder_with_name_pattern(name_pattern, recursive=True, verbose=0, search_dir='.'):
    if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 5):
        ##t_found_fileset = formic.FileSet(include=name_pattern)
        ##t_found_items = []
        ##for t_found_fileitem in t_found_fileset.qualified_files(absolute=False):
        ##    t_found_items.append(t_found_fileitem)
        #t_found_items = glob2.glob(name_pattern, recursive=recursive) # could not solve symbolic link
        t_found_items = []
        for m_root, m_dirs, m_files in os.walk(search_dir, followlinks = True):
            for m_file in m_files:
                if verbose >= 3:
                    print('Searching with the name pattern "%s": checking "%s"'%(name_pattern, m_file))
                if re.match('^'+name_pattern.replace('*','.*')+'$', m_root+os.sep+m_file):
                    t_found_items.append(m_root+os.sep+m_file)
                else:
                    if recursive == True:
                        if os.path.islink(m_file):
                            if verbose >= 3:
                                print('Searching with the name pattern "%s": searching inside "%s" (symlink)'%(name_pattern, m_file))
                            t_found_items_in_subdir = find_items_in_folder_with_name_pattern(name_pattern, recursive=recursive, verbose=verbose, search_dir=m_file)
                            if len(t_found_items_in_subdir) > 0:
                                t_found_items.extend(t_found_items_in_subdir)
            # 
            for m_dir in m_dirs:
                if verbose >= 3:
                    print('Searching with the name pattern "%s": checking "%s" (dir)'%(name_pattern, m_dir))
                if re.match('^'+name_pattern.replace('*','.*')+'$', m_root+os.sep+m_dir):
                    t_found_items.append(m_root+os.sep+m_dir)
                elif re.match('^'+name_pattern.replace('*','.*')+'$', m_root+os.sep+m_dir+os.sep):
                    t_found_items.append(m_root+os.sep+m_dir+os.sep)
                else:
                    if recursive == True:
                        if os.path.isdir(m_dir):
                            if verbose >= 3:
                                print('Searching with the name pattern "%s": searching inside "%s" (dir)'%(name_pattern, m_dir))
                            t_found_items_in_subdir = find_items_in_folder_with_name_pattern(name_pattern, recursive=recursive, verbose=verbose, search_dir=m_dir)
                            if len(t_found_items_in_subdir) > 0:
                                t_found_items.extend(t_found_items_in_subdir)
            # 
    else:
        t_found_items = glob.glob(name_pattern, recursive=recursive)
    # 
    if verbose >= 1 :
        print('Searching with the name pattern "%s": found %s'%(name_pattern, t_found_items))
        #print(t_found_items)
    # 
    return t_found_items







# 
# read input argument, which should be Member_ous_id
# 
if len(sys.argv) <= 1:
    print('Usage: alma_archive_make_data_dirs_with_meta_table.py "meta_table.txt" [-out "meta_table_with_dataset_names.txt"]')
    sys.exit()

meta_table_file = ''
some_option = ''
output_full_table = True
output_table_file = ''
#EVLA_pipeline_path = ''
#CASA_path = ''
verbose = 0
i = 1
while i < len(sys.argv):
    tmp_arg = re.sub(r'^[-]+', r'-', sys.argv[i].lower())
    if tmp_arg == '-some-option': 
        i = i+1
        if i < len(sys.argv):
            some_option = sys.argv[i]
    # elif tmp_arg == 'vla-pipeline-path': 
    #     i = i+1
    #     if i < len(sys.argv):
    #         EVLA_pipeline_path = sys.argv[i]
    # elif tmp_arg == 'casa-path': 
    #     i = i+1
    #     if i < len(sys.argv):
    #         CASA_path = sys.argv[i]
    elif tmp_arg == '-out': 
        i = i+1
        if i < len(sys.argv):
            output_table_file = sys.argv[i]
    elif tmp_arg == '-verbose': 
        verbose += 1
    else:
        meta_table_file = sys.argv[i]
    i = i+1
if meta_table_file == '':
    print('Error! No meta table file given!')
    sys.exit()
# if output_table_file == '':
#     output_table_file = re.sub(r'^(.*)(.txt|.fits)$', r'\1_with_dataset_names.txt', meta_table_file)

# 
# deal with sys.path
# 
#print(sys.path)
#sys.path.insert(0,os.path.dirname(os.path.abspath(sys.argv[0]))+'/Python/2.7/site-packages')
#print(sys.path)
#sys.exit()



# 
# check ~/Softwares/CASA/Portable/EVLA_pipeline1.4.0_for_CASA_5.0.0
# 
# if EVLA_pipeline_path == '':
#     EVLA_pipeline_path = os.path.expanduser('~')+'/Software/CASA/Portable/EVLA_pipeline1.4.0_CASA5.0.0' # try this path
#     if not os.path.isdir(EVLA_pipeline_path):
#         EVLA_pipeline_path = ''
# #if EVLA_pipeline_path == '':
# #    print('Error! EVLA_pipeline_path not given! Please input -vla-pipeline-path!')
# #    sys.exit(255)

# if CASA_path == '':
#     CASA_path = os.path.expanduser('~')+'/Software/CASA/Portable/casa-release-5.0.0-218.el6' # try this path
#     if not os.path.isdir(CASA_path):
#         CASA_path = ''
# if CASA_path == '':
#     CASA_path = os.path.expanduser('~')+'/Software/CASA/Portable/casa-release-5.7.2-4.el7' # try this path
#     if not os.path.isdir(CASA_path):
#         CASA_path = ''
# if CASA_path == '':
#     print('Error! CASA_path not given! Please input -casa-path!')
#     sys.exit(255)



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
    Source_name = meta_table['Source_name'].data.astype(np.str)

Dataset_dirname = None
if 'Dataset_dirname' in meta_table.colnames:
    Dataset_dirname = meta_table['Dataset_dirname']

Array = None
if 'Array' in meta_table.colnames:
    Array = meta_table['Array']

if Project_code is None or \
   Member_ous_id is None or \
   Source_name is None or \
   Array is None: 
    print('Error! The input meta data table should contain at least the following four columns: "Project_code" "Member_ous_id" "Source_name" "Array"!')
    sys.exit()



def my_function_to_make_symbolic_link(src, dst, verbose = 0):
    if os.path.exists(src):
        relpath = os.path.relpath(src, os.path.dirname(dst))
        if os.path.islink(dst):
            #print(os.readlink(dst))
            #print(os.path.exists(dst))
            if not os.path.exists(dst):
                os.remove(dst)
            elif os.readlink(dst) != relpath:
                print('Rewriting the link "%s" which was linked to "%s".'%(dst, os.readlink(dst)))
                os.remove(dst)
        if not os.path.islink(dst):
            if not os.path.isdir(os.path.dirname(dst)):
                os.makedirs(os.path.dirname(dst))
            if verbose >= 1 :
                print('Linking "%s" to "%s".'%(dst, relpath))
            os.symlink(relpath, dst)
            #print('ln -fsT "%s" "%s"'%(relpath, dst))
            #os.system('ln -fsT "%s" "%s"'%(relpath, dst))
        else:
            print('Found existing link "%s" to "%s".'%(dst, relpath))
    else:
        print('Cannot make a link to the non-existing src "%s".'%(src))



output_table = meta_table.copy()
output_table['Dataset_dirname'] = np.array(['']*len(output_table), dtype="object")
output_table['Downloaded'] = [False]*len(output_table)
output_table['Unpacked'] = [False]*len(output_table)
output_table['Calibrated'] = [False]*len(output_table)
output_table['Imaged'] = [False]*len(output_table)

t_Dataset_dict = {}
t_Dataset_id = 0
t_Dataset_processed = []

# 
# loop each meta table row to get dataset id
for i in range(len(output_table)):
    t_Project_code = Project_code[i]
    t_Member_ous_id = Member_ous_id[i]
    t_Member_ous_id = re.sub(r'[^a-zA-Z0-9._+-]', r'_', Member_ous_id[i])
    t_Source_name = re.sub(r'[^a-zA-Z0-9._+-]', r'_', Source_name[i])
    t_Source_name = re.sub(r'^_*(.*?)_*$', r'\1', t_Source_name)
    t_Array = Array[i]
    # 
    # reformat Source_name <TODO>
    if re.match(r'[0-9]$', t_Source_name):
        t_Galaxy_name = t_Source_name
    else:
        t_Galaxy_name = t_Source_name
    # 
    # determine t_Dataset_id, check t_Dataset_dict
    if t_Member_ous_id in t_Dataset_dict:
        t_Dataset_dirname = t_Dataset_dict[t_Member_ous_id]
    else:
        # 
        # got a new dataset not in previous t_Dataset_dict
        t_Dataset_id += 1
        # 
        # determine t_Dataset_dirname
        t_Dataset_digits = min(np.ceil(np.log10(len(output_table))), 2) # count digits and format the ID of each DataSet. 
        if t_Dataset_digits < 2: 
            t_Dataset_digits = 2
        t_Dataset_dirname = ('DataSet_%%0%dd'%(t_Dataset_digits))%(t_Dataset_id)
        # 
        # append to t_Dataset_dict
        t_Dataset_dict[t_Member_ous_id] = t_Dataset_dirname
    # 
    # store into output table
    output_table['Dataset_dirname'][i] = t_Dataset_dirname


# 
# prepare Level_1_Raw dir
if not os.path.isdir('Level_1_Raw'):
    os.mkdir('Level_1_Raw')
    if verbose >= 1:
        print('Created "Level_1_Raw" folder')


# 
# loop each unique dataset
for t_Member_ous_id in t_Dataset_dict:
    
    table_mask = (output_table['Dataset_dirname'] == t_Dataset_dict[t_Member_ous_id])
    t_Dataset_dirname = output_table['Dataset_dirname'][table_mask][0]
    
    # 
    # try to find downloaded tar files
    t_found_files = find_items_in_folder_with_name_pattern('Level_1_Raw/*'+t_Member_ous_id+'*.tar', verbose=verbose)
    if len(t_found_files) == 0:
        t_found_files = find_items_in_folder_with_name_pattern('Level_1_Raw/**/*'+t_Member_ous_id+'*.tar', verbose=verbose)
    if len(t_found_files) > 1:
        print('Warning! Found multiple data files with the name pattern "Level_1_Raw/**/*'+t_Member_ous_id+'*.tar"!')
    if len(t_found_files) > 0:
        output_table['Downloaded'][table_mask] = True
    else:
        # 
        print('Warning! "Level_1_Raw" folder does not contain "*%s*.tar" files! Please download the raw data into this directory (any subdirectory is fine)!'%(t_Member_ous_id))
        # 
        # prepare download scripts
        if re.match(r'uid_.*', t_Member_ous_id):
            with open('Level_1_Raw/download_%s_via_Mem_ous_id.bash'%(t_Dataset_dirname), 'w') as fp:
                fp.write('#!/bin/bash\n#\n')
                if os.path.isfile('meta_user_info.txt'):
                    fp.write('user_info=($(cat $(dirname $(dirname $(dirname ${BASH_SOURCE[0]})))/meta_user_info.txt))\n')
                else:
                    fp.write('user_info=()\n')
                fp.write('%s/alma_archive_download_data_by_Mem_ous_id.py "%s" ${user_info[@]}\n'%(os.path.dirname(__file__), t_Member_ous_id))
                fp.write('\n')
            os.system('chmod +x "Level_1_Raw/download_%s_via_Mem_ous_id.bash"'%(t_Dataset_dirname))
            print('We created a "Level_1_Raw/download_%s_via_Mem_ous_id.bash" script for easy downloading of ALMA data by Member_ous_id.'%(t_Dataset_dirname))
        # 
        # continue
        #continue # do not continue here, still check the unpacked directories
    
    # 
    # try to find unpacked raw data dirs
    t_found_dirs = find_items_in_folder_with_name_pattern('Level_1_Raw/*'+t_Member_ous_id, verbose=verbose)
    if len(t_found_dirs) == 0:
        t_found_dirs = find_items_in_folder_with_name_pattern('Level_1_Raw/**/*'+t_Member_ous_id, verbose=verbose)
    if len(t_found_dirs) > 1:
        print('Error! Found multiple data folders with the name pattern "Level_1_Raw/**/*'+t_Member_ous_id+'"!')
        raise Exception('Error! Found multiple data folders with the same name pattern!')
    if len(t_found_dirs) > 0:
        output_table['Downloaded'][table_mask] = True
        output_table['Unpacked'][table_mask] = True
    else:
        print('Warning! "Level_1_Raw" folder does not contain "*%s*" folders! Please unpack the raw ALMA data into this directory (any subdirectory is fine)!'%(t_Member_ous_id))
        # 
        # continue
        continue
    
    # 
    # check Level_2_Calib dir
    if not os.path.isdir('Level_2_Calib'):
        os.mkdir('Level_2_Calib')
        if verbose >= 1:
            print('Created "Level_2_Calib" folder')
    
    # 
    # loop Level_2_Calib dirs
    #for t_found_dir in t_found_dirs:
    #    # 
    #    # set Dataset_dirname
    #    # -- if there are multiple dirs for each t_Member_ous_id
    #    if len(t_found_dirs) > 1:
    #        t_found_dir_index = t_found_dirs.index(t_found_dir)
    #        if t_found_dir_index == 0:
    #            t_Dataset_dirname0 = t_Dataset_dirname
    #        t_Dataset_dirname = '%s_%d'%(t_Dataset_dirname0, t_found_dirs.index(t_found_dir)+1)
    #    # 
    #    # set Dataset_dirname if it exists in the meta table
    #    if Dataset_dirname is not None:
    #        if len(Dataset_dirname) > i:
    #            if t_Dataset_dirname != '':
    #                t_Dataset_dirname = t_Dataset_dirname
    #    # 
    #    # update output_table['Dataset_dirname'][i]
    #    output_table['Dataset_dirname'][i] = t_Dataset_dirname
    
    # 
    # for each dataset we only have one Level_2_Calib dir
    if len(t_found_dirs) > 0:
        t_found_dir = t_found_dirs[0]
        # 
        # t_CASA_dir = CASA_path
        # 
        # -- if the project is VLA or ALMA
        if t_Project_code.startswith('VLA'):
            t_Dataset_link = 'Level_2_Calib/'+t_Dataset_dirname+'/raw'
            t_Dataset_link2 = 'Level_2_Calib/'+t_Dataset_dirname+'/calibrated/'+os.path.basename(t_found_dir)
            # make link (including parenet dirs)
            my_function_to_make_symbolic_link('../../'+t_found_dir, t_Dataset_link, verbose=verbose)
            my_function_to_make_symbolic_link('../../../'+t_found_dir, t_Dataset_link2, verbose=verbose)
            # 
            # make calibration script
            # <TODO> EVLA pipeline CASA version ??
            # if EVLA_pipeline_path == '':
            #     print('Error! EVLA_pipeline_path not given! Please input -vla-pipeline-path!')
            #     sys.exit(255)
            # t_EVLA_calib_script = os.path.join(EVLA_pipeline_path, 'EVLA_pipeline.py')
            # t_Dataset_calib_script = 'Level_2_Calib/'+t_Dataset_dirname+'/calibrated/'+'scriptForDatasetRecalibration.py'
            # Overwrite_calib_scripts = True
            # if not os.path.isfile(t_Dataset_calib_script) or Overwrite_calib_scripts == True:
            #     if os.path.isfile(t_EVLA_calib_script) and os.path.isdir(t_CASA_dir) and os.path.isfile(t_CASA_dir+'/bin/casa'):
            #         if verbose >= 1:
            #             print('Writing calibration script "%s"'%(t_Dataset_calib_script))
            #         with open(t_Dataset_calib_script, 'w') as fp:
            #             #fp.write('#!/usr/bin/env python\n')
            #             fp.write('# RUN THIS SCRIPT INSIDE CASA AS: \n')
            #             fp.write('#   exec(open("%s").read())\n'%(os.path.basename(t_Dataset_calib_script)))
            #             fp.write('# \n')
            #             fp.write('SDM_name = \'%s\'\n'%(os.path.basename(t_found_dir)))
            #             fp.write('mymodel = \'y\'\n')
            #             fp.write('myHanning = \'n\'\n')
            #             fp.write('exec(open(\'%s\').read())\n'%(t_EVLA_calib_script))
            #             fp.write('\n')
            #         with open(re.sub(r'\.py$', r'.sh', t_Dataset_calib_script), 'w') as fp:
            #             fp.write('#!/bin/bash\n')
            #             #fp.write('source \"%s\" %s\n'%(t_CASA_setup_script, t_CASA_version))
            #             fp.write('export PATH=\"%s:$PATH\"\n'%(t_CASA_dir+'/bin'))
            #             fp.write('export LANG=\"en_US.UTF-8\"\n')
            #             fp.write('export LC_ALL=\"C\"\n')
            #             fp.write('cd \"%s/\"\n'%(os.path.abspath(os.path.dirname(t_Dataset_calib_script))))
            #             fp.write('pwd\n')
            #             fp.write('casa --nogui --log2term -c \"%s\" | tee log_scriptForDatasetRecalibration.txt\n'%(os.path.basename(t_Dataset_calib_script)))
            #             fp.write('\n')
            #         os.system('chmod +x "%s"'%(re.sub(r'\.py$', r'.sh', t_Dataset_calib_script)))
            #         print('Prepared calibration pipeline to run: %r'%(t_Dataset_calib_script))
        else:
            t_Dataset_link = 'Level_2_Calib/'+t_Dataset_dirname
            # make link (including parenet dirs)
            my_function_to_make_symbolic_link('../'+t_found_dir, t_Dataset_link, verbose=verbose)
            # 
            # make calibration script
            # <TODO> ALMA pipeline mode or ??
            # t_Dataset_calib_script = 'Level_2_Calib/'+t_Dataset_dirname+'/script/'+'scriptForDatasetRecalibration.py'
            # Overwrite_calib_scripts = True
            # if not os.path.isfile(t_Dataset_calib_script) or Overwrite_calib_scripts == True:
            #     t_ALMA_calib_script = 'scriptForPI.py'
            #     if os.path.isfile(t_ALMA_calib_script) and os.path.isdir(t_CASA_dir) and os.path.isfile(t_CASA_dir+'/bin/casa'):
            #         if verbose >= 1:
            #             print('Writing calibration script "%s"'%(t_Dataset_calib_script))
            #         with open(t_Dataset_calib_script, 'w') as fp:
            #             fp.write('#!/usr/bin/env python\n')
            #             fp.write('SDM_name = \'%s\'\n'%(os.path.basename(t_found_dir)))
            #             fp.write('mymodel = \'y\'\n')
            #             fp.write('myHanning = \'n\'\n')
            #             fp.write('execfile(\'%s\')\n'%(t_EVLA_calib_script))
            #             fp.write('\n')
            #         with open(re.sub(r'\.py$', r'.sh', t_Dataset_calib_script), 'w') as fp:
            #             fp.write('#!/bin/bash\n')
            #             #fp.write('source \"%s\" %s\n'%(t_CASA_setup_script, t_CASA_version))
            #             fp.write('export PATH=\"%s:$PATH\"\n'%(t_CASA_dir+'/bin'))
            #             fp.write('cd \"%s/%s\"\n'%(os.getcwd(), os.path.dirname(t_Dataset_calib_script)))
            #             fp.write('pwd\n')
            #             fp.write('casa -c \"%s\"\n'%(os.path.basename(t_Dataset_calib_script)))
            #             fp.write('\n')
            #         os.system('chmod +x "%s"'%(re.sub(r'\.py$', r'.sh', t_Dataset_calib_script)))
            #         print('Prepared calibration pipeline to run: %r'%(t_Dataset_calib_script))
        
        # 
        # recheck Dataset raw dir
        if verbose >= 2:
            print('Checking '+'Level_2_Calib/'+t_Dataset_dirname+'/raw')
        if not os.path.isdir('Level_2_Calib/'+t_Dataset_dirname+'/raw'):
            output_table['Unpacked'][table_mask] = False
        elif len(os.listdir('Level_2_Calib/'+t_Dataset_dirname+'/raw')) == 0:
            output_table['Unpacked'][table_mask] = False
        else:
            output_table['Unpacked'][table_mask] = True
        
        # 
        # check Dataset calibrated dir
        if verbose >= 2:
            print('Checking '+'Level_2_Calib/'+t_Dataset_dirname+'/calibrated/*.ms')
        if os.path.isdir('Level_2_Calib/'+t_Dataset_dirname+'/calibrated'):
            t_found_ms = glob.glob('Level_2_Calib/'+t_Dataset_dirname+'/calibrated/*.ms')
            if len(t_found_ms) > 0:
                output_table['Calibrated'][table_mask] = True
        
        ## 
        ## check calibrated dir
        #t_found_dirs3 = glob.glob(Project_code+'/science_goal.*/group.*/member.'+t_Member_ous_id+'/'+'calibrated'+'/'+'*.ms')
        #if len(t_found_dirs3) > 0:
        #    output_table['Calibrated'][table_mask] = True
        
        ## 
        ## check imaged fits files
        #t_found_dirs3 = glob.glob('imaging/'+t_Galaxy_name.lower()+'/'+t_Galaxy_name+'_'+t_Array+'_*.fits')
        #if len(t_found_dirs3) > 0:
        #    output_table['Calibrated'][table_mask] = True



print(output_table)


if output_table_file != '':
    if os.path.isfile(output_table_file):
        print('Backing up "%s" as "%s"!'%(output_table_file, output_table_file+'.backup'))
        shutil.move(output_table_file, output_table_file+'.backup')
    if output_table_file.find(os.sep) >= 0:
        if not os.path.isdir(os.path.dirname(output_table_file)):
            os.makedirs(os.path.dirname(output_table_file))
    output_table.write(output_table_file, format='ascii.fixed_width', delimiter='  ', bookend=True)
    with open(output_table_file, 'r+') as fp:
        fp.seek(0)
        fp.write('#')
    print('Output to "%s"!'%(output_table_file))





