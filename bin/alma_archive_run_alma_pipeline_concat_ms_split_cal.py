
# Please run this code with CASA
# 
# casa -c 
# 

import os, sys, glob

def alma_archive_run_alma_pipeline_concat_ms_split_cal(locals_dict):
    
    # 
    # find uid___ * .ms.split.cal
    uid_dirs = []
    for uid_dir in os.listdir('.'):
        if uid_dir.endswith(os.sep):
            uid_dir = uid_dir[0:len(uid_dir)-1]
        if uid_dir.startswith('uid___') and uid_dir.endswith('.ms.split.cal'):
            uid_dirs.append(uid_dir)
    
    if len(uid_dirs) == 0:
        print('Warning! No "uid___*.ms.split.cal" was found! Trying to find "uid___*.ms"')
        
        for uid_dir in os.listdir('.'):
            if uid_dir.endswith(os.sep):
                uid_dir = uid_dir[0:len(uid_dir)-1]
            if uid_dir.startswith('uid___') and uid_dir.endswith('.ms'):
                uid_dirs.append(uid_dir)
        
        if len(uid_dirs) == 0:
            print('Error! No "uid___*.ms.split.cal" or "uid___*.ms" was found!')
            sys.exit()
    
    
    # 
    # Set parameter or read from locals dict
    freqtol = '20MHz'
    if 'freqtol' in locals_dict:
        if locals_dict['freqtol'] != '':
            freqtol = locals_dict['freqtol']
    
    concatvis = 'calibrated.ms'
    if 'concatvis' in locals_dict:
        if locals_dict['concatvis'] != '':
            concatvis = locals_dict['concatvis']
    
    
    #i = 1
    #while i < len(sys.argv):
    #    temp_argv = sys.argv[i].lower()
    #    if temp_argv.find('--') == 0:
    #        temp_argv = '-'+temp_argv.lstrip('-')
    #    if temp_argv == '-freqtol':
    #        if i+1 < len(sys.argv):
    #            i = i + 1
    #            freqtol = sys.argv[i]
    #    if temp_argv == '-out' or temp_argv == '-output' or temp_argv == '-concatvis':
    #        if i+1 < len(sys.argv):
    #            i = i + 1
    #            concatvis = sys.argv[i]
    #    i = i + 1
    
    
    concat = locals_dict['concat']
    concat(vis = uid_dirs,
           concatvis = concatvis, 
           freqtol = freqtol)
    
    
    
    #sourcevis = 'calibrated_final.ms'
    #split(vis=concatvis,
    #      intent='*TARGET*',
    #      outputvis=sourcevis,
    #      datacolumn='data')
    #
    #os.system('rm -rf '+concatvis)
    #os.system('rm -rf '+concatvis+'.flagversions')


