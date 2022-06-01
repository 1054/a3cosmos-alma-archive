#!/usr/bin/env python
# 

from __future__ import print_function
import os, sys, re, time, datetime, json, shutil
# pkg_resources
#pkg_resources.require('astroquery')
#pkg_resources.require('keyrings.alt')
import keyring
import astroquery
import requests
import subprocess
from astroquery.alma.core import Alma
import astropy.io.ascii as asciitable
from astropy.table import Table, Column
from operator import itemgetter, attrgetter
from collections import OrderedDict
import glob
import numpy as np





# 
# read input argument, which should be Member_ous_id
# 
if len(sys.argv) <= 1:
    print('Usage: alma_archive_download_data_according_to_meta_table.py "meta_table_file.txt" [--user dzliu] [--eso] [--out project_code.cache]')
    sys.exit()

meta_table_file = ''
some_option = ''
Login_user_name = ''
Use_alma_site = 'nrao'
Use_astroquery_download = False
output_dir = ''
overwrite = False
verbose = 0
i = 1
while i < len(sys.argv):
    tmp_arg = re.sub(r'^[-]+', r'-', sys.argv[i].lower())
    if tmp_arg == '-some-option': 
        i = i+1
        if i < len(sys.argv):
            some_option = sys.argv[i]
    elif tmp_arg == '-user': 
        i = i+1
        if i < len(sys.argv):
            Login_user_name = sys.argv[i]
    elif tmp_arg == '-out': 
        i = i+1
        if i < len(sys.argv):
            output_dir = sys.argv[i]
    elif tmp_arg == '-eso': 
        Use_alma_site = 'eso'
    elif tmp_arg == '-use-astroquery-download': 
        Use_astroquery_download = True
    elif tmp_arg == '-overwrite': 
        overwrite = True
    elif tmp_arg == '-verbose': 
        verbose = verbose + 1
    else:
        meta_table_file = sys.argv[i]
    i = i+1
if meta_table_file == '':
    print('Error! No meta table file given!')
    sys.exit()



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

for t in meta_table.colnames:
    if t.find(' ')>=0:
        meta_table.rename_column(t, t.replace(' ','_')) # replace white space in column name

if not ('Project_code' in meta_table.colnames) or \
   not ('Member_ous_id' in meta_table.colnames) or \
   not ('Source_name' in meta_table.colnames) or \
   not ('Array' in meta_table.colnames):
    print('Error! The input meta data table should contain at least the following four columns: "Project_code" "Member_ous_id" "Source_name" "Array"!')
    sys.exit()






# 
# Loop each row
# 
output_dir_path_list = []
failed_downloads_dict = OrderedDict()
for i in range(len(meta_table)):
    # 
    # get mem_ous_id
    # 
    Member_ous_id = meta_table['Member_ous_id'][i]
    Member_ous_name = Member_ous_id.replace(':','_').replace('/','_').replace('+','_') # alternative?: Alma.clean_uid(Member_ous_id)
    Output_name = 'alma_archive_download_tar_files_by_Mem_ous_id_%s'%(Member_ous_name)
    # 
    # prepare output dir
    # 
    if output_dir == '':
        output_dir_path = meta_table['Project_code'][i]+'.cache'
    else:
        output_dir_path = output_dir
    # 
    # append to output_dir_path_list
    # 
    output_dir_path = os.path.abspath(output_dir_path)
    if output_dir_path not in output_dir_path_list:
        output_dir_path_list.append(output_dir_path)
    # 
    # check exist output and do not overwrite
    # 
    if os.path.isdir(output_dir_path) and \
       os.path.isfile(output_dir_path+'.done') and \
       (not os.path.isfile(output_dir_path+'.touch')) and \
       (not os.path.isfile(output_dir_path+'.error')) and \
       (not overwrite):
        print('Found existing "%s" and "%s". Will not overwrite!'%(output_dir_path, output_dir_path+'.done'))
        continue
    # 
    # make directory
    # 
    if not os.path.isdir(output_dir_path):
        os.makedirs(output_dir_path)
    # 
    # change directory
    # 
    current_dir_path = os.getcwd()
    print('os.chdir("%s")' % (output_dir_path) )
    os.chdir(output_dir_path)
    print('os.getcwd()', os.getcwd())
    # 
    # check exist log file and make sure it does not contain "ERROR" stuff
    # 
    has_error_in_previous_run = False
    if os.path.isfile(Output_name+'.log'):
        print('Checking previous log file "%s"...'%(Output_name+'.log'))
        has_successfully_downloaded = False
        with open(Output_name+'.log', 'r') as fp:
            for line in fp:
                #print('line', line) # debug 20220524
                if re.match('.*error.*', line.strip(), re.IGNORECASE):
                    has_error_in_previous_run = True
                    break
                elif re.match('.*successfully downloaded.*', line.strip(), re.IGNORECASE):
                    has_successfully_downloaded = True
                    #continue, do not break
    if has_error_in_previous_run or (not has_successfully_downloaded):
        print('Found error in "%s"! Will re-run the script "%s"!'%(Output_name+'.log', Output_name+'.sh'))
        if os.path.isfile(Output_name+'.touch'):
            os.remove(Output_name+'.touch')
        if os.path.isfile(Output_name+'.sh.done'):
            os.remove(Output_name+'.sh.done')
        #if os.path.isfile(Output_name+'.log'):
        #    os.remove(Output_name+'.log')
    # 
    # check previous runs
    # 
    if os.path.isfile(Output_name+'.sh'): 
        if os.path.isfile('%s.sh.done'%(Output_name)): 
            print('Found exisiting "%s" and "%s"! Will not re-run it!'%(Output_name+'.sh', Output_name+'.sh.done'))
            # 
            # cd back and continue
            # 
            print('os.chdir("%s")' % (current_dir_path) )
            os.chdir(current_dir_path)
            print('os.getcwd()', os.getcwd())
            continue
        else:
            print('Found exisiting "%s" but it is not finished! Will re-run it!'%(Output_name+'.sh'))
    
    # 
    # Set if use shell or astroquery module
    # 
    Use_Shell = (not Use_astroquery_download)
    Logged_In = False
    
    # 
    # do Alma.login
    # 
    if (Use_Shell and (not os.path.isfile(Output_name+'.txt'))) or ((not Use_Shell) and (not Logged_In)): 
        
        # prepare download script and run os.system
        
        # archive url
        # 'http://almascience.org',
        # 'https://almascience.eso.org',
        # 'https://almascience.nrao.edu',
        # 'https://almascience.nao.ac.jp',
        # 'https://beta.cadc-ccda.hia-iha.nrc-cnrc.gc.ca'
        if Use_alma_site == 'eso':
            Alma.archive_url = u'https://almascience.eso.org'
        else:
            Alma.archive_url = u'https://almascience.nrao.edu'
        
        # login
        if Login_user_name != '':
            print('Logging in as ALMA User "%s"'%(Login_user_name))
            Alma.login(Login_user_name, store_password = True, reenter_password = False)
            Logged_In = True
    
    # 
    # prepare list or Urls
    # 
    if os.path.isfile(Output_name+'.txt'):
        has_valid_lines = 0
        with open(Output_name+'.txt', 'r') as fp:
            for line in fp:
                if re.match(r'.*[a-zA-Z0-9]+.*', line.strip()):
                    has_valid_lines += 1
        if has_valid_lines <= 1:
            os.remove(Output_name+'.txt') # no valid line, delete it
    
    if not os.path.isfile(Output_name+'.txt'):
        
        print('Staging data for Member ObservingUnitSet ID "%s"'%(Member_ous_id))
        uid_url_table = Alma.stage_data(Member_ous_id)
        print(uid_url_table)
        
        #filelist = Alma.download_and_extract_files(uid_url_table['URL'], regex='.*README$')
        #print(filelist)
        
        asciitable.write(uid_url_table, Output_name+'.txt', Writer=asciitable.FixedWidthTwoLine)
        
    else:
        
        uid_url_table = asciitable.read(Output_name+'.txt', format='fixed_width_two_line')
        print(uid_url_table)
        
    # 
    # prepare shell script to download the data
    # 
    if Use_Shell and (not os.path.isfile(Output_name+'.sh')):
        with open(Output_name+'.sh', 'w') as fp:
            fp.write("#!/bin/bash\n")
            fp.write("#\n")
            fp.write("\n")
            fp.write("set -e\n")
            fp.write("\n")
            fp.write('date +"%%Y-%%m-%%d %%H:%%M:%%S %%Z')
            fp.write("\n")
            fp.write('echo "${BASH_SOURCE[0]}"')
            fp.write("\n")
            fp.write("export PATH=\"$PATH:%s\"\n"%(os.path.dirname(sys.argv[0])))
            fp.write("\n")
            if Login_user_name != '':
                fp.write("export INPUT_USERNAME=\"%s\"\n"%(Login_user_name))
                fp.write("export INPUT_PASSWORD=$(python -c \"from __future__ import print_function; import keyring; print(keyring.get_password('astroquery:asa.alma.cl','%s'))\")\n"%(Login_user_name))
                fp.write("\n")
            else:
                fp.write("export INPUT_USERNAME=\"\"\n")
                fp.write("export INPUT_PASSWORD=\"\"\n")
            for i in range(len(uid_url_table)):
                fp.write("\n")
                fp.write("alma_archive_download_data_via_http_link.sh \"%s\"\n"%(uid_url_table[i]['URL']))
            fp.write("\n")
            fp.write("date +\"%%Y-%%m-%%d %%H:%%M:%%S %%Z\" > \"%s\"\n"%(Output_name+'.sh.done'))
            fp.write("\n")
        
        # 
        # Old method
        #for i in range(len(uid_url_table)):
        #    if i == 0:
        #        os.system('echo "#!/bin/bash" > %s.sh'%(Output_name)) # creating new file
        #        os.system('echo "" >> %s.sh'%(Output_name))
        #        os.system('echo "set -e" >> %s.sh'%(Output_name))
        #        os.system('echo "" >> %s.sh'%(Output_name))
        #        os.system('echo "export PATH=\\\"\$PATH:%s\\\"" >> %s.sh'%(os.path.dirname(sys.argv[0]), Output_name))
        #        if Login_user_name != '':
        #            os.system('echo "export INPUT_USERNAME=\\\"%s\\\"" >> %s.sh'%(Login_user_name, Output_name))
        #            os.system('echo "echo \"\" > /dev/tty" >> %s.sh'%(Output_name))
        #            
        #            os.system('echo "echo -n \"Please enter the password for ALMA account \"%s\": \" > /dev/tty" >> %s.sh'%(Login_user_name, Output_name))
        #            os.system('echo "read -s INPUT_PASSWORD" >> %s.sh'%(Output_name))
        #            os.system('echo "echo \"\" > /dev/tty" >> %s.sh'%(Output_name))
        #            os.system('echo "export INPUT_PASSWORD" >> %s.sh'%(Output_name))
        #        else:
        #            os.system('echo "export INPUT_USERNAME=\\\"\\\"" >> %s.sh'%(Output_name))
        #            os.system('echo "export INPUT_PASSWORD=\\\"\\\"" >> %s.sh'%(Output_name))
        #    # 
        #    os.system('echo "" >> %s.sh'%(Output_name))
        #    # 
        #    os.system('echo "alma_archive_download_data_via_http_link.sh \"%s\"" >> %s.sh'%(uid_url_table[i]['URL'], Output_name))
        #    # 
        #    if i == len(uid_url_table)-1:
        #        os.system('echo "" >> %s.sh'%(Output_name))
        #        os.system('echo \"date +\\\"%%Y-%%m-%%d %%H:%%M:%%S %%Z\\\" > %s.sh.done\" >> %s.sh'%(Output_name, Output_name))
        #        os.system('echo "" >> %s.sh'%(Output_name))
        # 
        
        print('Now prepared a shell script "%s" to download the Tar files!'%(Output_name+'.sh'))
    
    
    
    # 
    # append progress in the touch file
    # 
    start_time = datetime.datetime.now()
    start_time_stamp = start_time.strftime("%Y-%m-%d %H:%M:%S") + ' ' + time.strftime('%Z')
    with open(output_dir_path+'.touch', 'a') as fp:
        fp.write('START: ' + start_time_stamp + '\n')
        fp.write('EXEC:  ' + Output_name+'.sh' + '\n')
    
    
    # 
    # run download script or astroquery module
    # 
    has_successfully_downloaded = False
    if Use_Shell:
        print('Running "%s >> %s" in terminal!'%(Output_name+'.sh', Output_name+'.log'))
        #os.system('date +"%%Y-%%m-%%d %%H:%%M:%%S %%Z" > %s'%(Output_name+'.log'))
        #os.system('echo "%s %s" >> %s'%(sys.argv[0], sys.argv[1], Output_name+'.log'))
        #os.system('echo "" >> %s'%(Output_name+'.log'))
        #os.system('echo "chmod +x %s; ./%s 2>&1" >> %s'%(Output_name+'.sh', Output_name+'.sh', Output_name+'.log'))
        #os.system('echo "" >> %s'%(Output_name+'.log'))
        #ret = os.system('chmod +x %s; ./%s 2>&1 >> %s'%(Output_name+'.sh', Output_name+'.sh', Output_name+'.log'))
        proc = subprocess.run('/bin/bash %s'%(Output_name+'.sh') ,shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with open(Output_name+'.log', 'w') as fp:
            fp.write(proc.stdout)
        ret = proc.returncode
        if ret == 0:
            has_successfully_downloaded = True
        else:
            has_successfully_downloaded = False
            with open(Output_name+'.log', 'a') as fp:
                fp.write('\nFinished with error!\n')
            with open(output_dir_path+'.error', 'a') as fp:
                fp.write('ERROR:  ' + Output_name+'.sh' + '\n')
    
    else:
        
        #myAlma = Alma()
        #myAlma.cache_location = os.getcwd() + os.path.sep + 'cache'
        #myAlma.download_files(uid_url_table['URL'], cache=True)
        with open(Output_name+'.log', 'a') as fp:
            fp.write('Executing astroquery.Alma.retrieve_data_from_uid("%s").\n'%(Member_ous_id))
        Alma.retrieve_data_from_uid(Member_ous_id, cache = False) # <TODO> how to log into Output_name+'.log' ?
        with open(Output_name+'.log', 'a') as fp:
            fp.write('Successfully downloaded files with astroquery.Alma.retrieve_data_from_uid("%s").\n'%(Member_ous_id))
        has_successfully_downloaded = True
    
    if not has_successfully_downloaded:
        if output_dir_path not in failed_downloads_dict:
            failed_downloads_dict[output_dir_path] = []
        failed_downloads_dict[output_dir_path].append(Output_name)
    
    # 
    # Re-using Alma repeatedly causes cache problem. Calling Alma.__init__() fixes the problem.  
    # 
    #Alma.__init__()
    
    
    # 
    # cd back
    # 
    print('os.chdir("%s")' % (current_dir_path) )
    os.chdir(current_dir_path)
    print('os.getcwd()', os.getcwd())
    
    
    # 
    # finish
    # 
    finish_time = datetime.datetime.now()
    finish_time_stamp = finish_time.strftime("%Y-%m-%d %H:%M:%S") + ' ' + time.strftime('%Z')
    with open(output_dir_path+'.touch', 'a') as fp:
        fp.write('FINISH:  ' + finish_time_stamp + '\n')
        fp.write('ELAPSED: ' + str(finish_time-start_time) + '\n')
        fp.write('\n')


    
# 
# finish all
# 
has_error = False
for output_dir_path in output_dir_path_list:
    if output_dir_path not in failed_downloads_dict:
        if os.path.isfile(output_dir_path+'.error'):
            os.remove(output_dir_path+'.error')
        if os.path.isfile(output_dir_path+'.touch'):
            shutil.move(output_dir_path+'.touch', output_dir_path+'.done') # rename touch file as done file
    else:
        has_error = True

if has_error:
    print('Done with error!')
    sys.exit(1)
else:
    print('Done!')
    sys.exit(0)
    


