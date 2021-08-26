#!/usr/bin/env python
# 
# This needs to be run in CASA
# 
# We will find "calibrated.ms" under "Level_2_Calib/DataSet_*/calibrated/"
# 
# Example:
#     vis = 'aaa.ms'
#     import a_dzliu_code_level_3_concat_task_1_casa_concat; reload(a_dzliu_code_level_3_concat_task_1_casa_concat); from a_dzliu_code_level_3_concat_task_1_casa_concat import dzliu_list_observing_targets; dzliu_list_observing_targets(globals())
# 
from __future__ import print_function
import os, sys, re, json, copy, glob, shutil
import numpy as np
from taskinit import casalog, tb #, ms, iatool



def print2(message):
    print(message)
    casalog.post(message, 'INFO')



def dzliu_listobs(globals_dict):
    # 
    if 'casalog' not in globals_dict:
        raise ValueError('The \'casalog\' module is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        casalog = globals_dict['casalog']
        casalog.origin('dzliu_listobs')
    # 
    if 'listobs' not in globals_dict:
        raise ValueError('The \'listobs\' function is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        listobs = globals_dict['listobs']
    # 
    if 'vis' not in globals_dict:
        raise ValueError('The \'vis\' argument is not in the input globals_dict! Please see the usage of CASA listobs!')
    else:
        vis = globals_dict['vis']
    
    # 
    if 'listfile' not in globals_dict:
        listfile = ''
    else:
        listfile = globals_dict['listfile']
    # 
    if listfile == '':
        listfile = vis+'.listobs.txt'
    # 
    listobs(vis = vis, listfile = listfile, overwrite = True)



def dzliu_read_ms_meta_table(meta_table_name, globals_dict):
    # 
    if 'casalog' not in globals_dict:
        raise ValueError('The \'casalog\' module is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        casalog = globals_dict['casalog']
        casalog.origin('dzliu_read_ms_meta_table')
    # 
    if 'tb' not in globals_dict:
        raise ValueError('The \'tb\' module is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        tb = globals_dict['tb']
    # 
    if 'vis' not in globals_dict:
        raise ValueError('The \'vis\' argument is not in the input globals_dict! Please see the usage of CASA listobs!')
    else:
        vis = globals_dict['vis']
    # 
    allowed_meta_table_names = ['ANTENNA', 'FIELD', 'SPECTRAL_WINDOW', 'STATE', 'DATA_DESCRIPTION']
    if meta_table_name.upper() not in allowed_meta_table_names:
        raise ValueError('The \'meta_table_name\' should be one of %s!'%(str(allowed_meta_table_names)))
    # 
    output_meta_table = {}
    # 
    tb.open(vis+os.sep+meta_table_name.upper())
    for key in tb.colnames():
        try:
            output_meta_table[key] = tb.getcol(key)
        except:
            try:
                output_meta_table[key] = [tb.getcell(key, i) for i in range(tb.nrows())]
            except:
                pass
    tb.close()
    # 
    return output_meta_table



def dzliu_list_observing_targets(globals_dict):
    # 
    print('globals_dict', globals_dict)
    # 
    if 'casalog' not in globals_dict:
        raise ValueError('The \'casalog\' module is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        casalog = globals_dict['casalog']
        casalog.origin('dzliu_list_observing_targets')
    # 
    if 'tb' not in globals_dict:
        raise ValueError('The \'tb\' module is not in the input globals_dict! Please pass the globals() dict as an argument to this function when calling it!')
    else:
        tb = globals_dict['tb']
    # 
    if 'vis' not in globals_dict:
        raise ValueError('The \'%s\' argument is not in the input globals_dict!'%('vis'))
    else:
        vis = globals_dict['vis']
    # 
    if 'listfile' not in globals_dict:
        listfile = ''
    else:
        listfile = globals_dict['listfile']
    # 
    if listfile == '':
        listfile = vis+'.fields.json'
    # 
    if not listfile.endswith('.json'):
        raise ValueError('The listfile argument \"%s\" should ends with \".json\"!'%(listfile))
    # 
    if os.path.isfile(listfile):
        raise Exception('Error! The listfile \"%s\" already exists!'%(listfile))
    # 
    # 
    # read ms meta table 'ANTENNA'
    antenna_table = dzliu_read_ms_meta_table('ANTENNA', globals_dict)
    antenna_names = antenna_table['NAME']
    antenna_IDs = np.arange(len(antenna_names))
    # 
    # read ms meta table 'FIELD'
    field_table = dzliu_read_ms_meta_table('FIELD', globals_dict)
    field_names = field_table['NAME']
    field_IDs = np.arange(len(field_names))
    unique_field_names = list(set(sorted(field_names)))
    # 
    # read ms meta table 'STATE'
    state_table = dzliu_read_ms_meta_table('STATE', globals_dict)
    state_obs_mode = state_table['OBS_MODE']
    state_IDs = np.arange(len(state_obs_mode))
    # 
    # read ms meta table 'SPECTRAL_WINDOW'
    spw_table = dzliu_read_ms_meta_table('SPECTRAL_WINDOW', globals_dict)
    spw_names = spw_table['NAME']
    spw_IDs = np.arange(len(spw_names))
    # 
    # query ms data table
    tb.open(vis)
    observing_targets = {}
    for unique_field_name in unique_field_names:
        observing_targets[unique_field_name] = {}
        observing_targets[unique_field_name]['STATE_ID'] = ''
        observing_targets[unique_field_name]['OBS_MODE'] = ''
        querying_field_IDs = field_IDs[np.argwhere(field_names == unique_field_name).flatten()]
        print2('tb.query(\'FIELD_ID in [%s]\', \'STATE_ID, DATA_DESC_ID, EXPOSURE, FLAG\')'%(', '.join(querying_field_IDs.astype(str))))
        result = tb.query('FIELD_ID in [%s]'%(', '.join(querying_field_IDs.astype(str))), 'STATE_ID, DATA_DESC_ID, EXPOSURE, FLAG')
        queried_state_IDs = result.getcol('STATE_ID')
        queried_data_desc_IDs = result.getcol('DATA_DESC_ID')
        queried_exposures = result.getcol('EXPOSURE')
        queried_flags = [result.getcell('FLAG', i) for i in range(result.nrows())]
        unique_queried_state_IDs = np.unique(queried_state_IDs)
        unique_queried_data_desc_IDs = np.unique(queried_data_desc_IDs)
        integration_time_per_spw = []
        visibilities_per_spw = []
        nonflag_rate_per_spw = []
        # print(queried_data_desc_IDs, unique_queried_data_desc_IDs)
        # data_desc_ID corresponds to the row in DATA_DESCRIPTION meta table and indicates the spw_ID in SPECTRAL_WINDOW meta table.
        for unique_queried_data_desc_ID in unique_queried_data_desc_IDs:
            matched_data_desc_ID_rows = np.argwhere(queried_data_desc_IDs == unique_queried_data_desc_ID).flatten()
            #print('matched_data_desc_ID_rows.shape', matched_data_desc_ID_rows.shape)
            integration_time_per_spw.append(np.sum(queried_exposures[matched_data_desc_ID_rows]))
            visibilities_per_spw.append(len(matched_data_desc_ID_rows))
            matched_data_desc_ID_flags = np.array([queried_flags[i] for i in matched_data_desc_ID_rows]) # get the 'FLAG' column's rows with current spw_ID or data_desc_ID
            #print('matched_data_desc_ID_flags.shape', matched_data_desc_ID_flags.shape)
            matched_data_desc_ID_flags_flattened = matched_data_desc_ID_flags.flatten()
            nonflag_rate_per_spw.append(np.count_nonzero(matched_data_desc_ID_flags_flattened) / float(len(matched_data_desc_ID_flags_flattened)))
        integration_time_per_spw = np.array(integration_time_per_spw)
        visibilities_per_spw = np.array(visibilities_per_spw)
        nonflag_rate_per_spw = np.round(np.array(nonflag_rate_per_spw), 6)
        #non_flagged_fraction = np.count_nonzero(queried_flags) / len(queried_flags)
        # 
        num_antenna = len(antenna_names)
        num_baseline = np.int64(len(antenna_names)) * np.int64(len(antenna_names)-1)
        integration_time_per_spw = integration_time_per_spw / float(num_baseline)
        # 
        observing_targets[unique_field_name]['FIELD_ID'] = ', '.join(querying_field_IDs.astype(str))
        observing_targets[unique_field_name]['STATE_ID'] = ', '.join(state_IDs[unique_queried_state_IDs].astype(str))
        observing_targets[unique_field_name]['OBS_MODE'] = '; '.join(state_obs_mode[unique_queried_state_IDs].astype(str))
        observing_targets[unique_field_name]['NUM_ANTENNA'] = num_antenna
        observing_targets[unique_field_name]['NUM_BASELINE'] = num_baseline
        observing_targets[unique_field_name]['SPW_ID'] = ', '.join(spw_IDs[unique_queried_data_desc_IDs].astype(str))
        observing_targets[unique_field_name]['INT_TIME'] = np.sum(queried_exposures) / float(len(spw_IDs[unique_queried_data_desc_IDs])) / float(num_baseline)
        observing_targets[unique_field_name]['INT_TIME_UNITS'] = 'seconds'
        observing_targets[unique_field_name]['INT_TIME_PER_SPW'] = ', '.join(integration_time_per_spw.astype(str))
        observing_targets[unique_field_name]['VISIBILITIES_PER_SPW'] = ', '.join(visibilities_per_spw.astype(str))
        observing_targets[unique_field_name]['NONFLAG_RATE_PER_SPW'] = ', '.join(nonflag_rate_per_spw.astype(str))
        print2('observing_targets[\'%s\'] = %s'%(unique_field_name, observing_targets[unique_field_name]))
    with open(listfile, 'w') as fp:
        json.dump(observing_targets, fp, indent = 4)
        print2('Output to "%s"!'%(listfile))
    tb.close()
    
    



def dzliu_concat(globals_dict):
    MeasurementSet_list = glob.glob("Level_2_Calib/DataSet_*/calibrated/calibrated.ms")
    print('MeasurementSet_list', MeasurementSet_list)
    unique_field_name_dict = {}
    for MeasurementSet_dir in MeasurementSet_list:
        # 
        globals()['vis'] = MeasurementSet_dir
        globals()['listfile'] = ''
        # 
        # run casa listobs
        if not os.path.isfile(MeasurementSet_dir+'.listobs.txt'):
            print2('Preparing '+MeasurementSet_dir+'.listobs.txt')
            dzliu_listobs(globals_dict)
            #break
        # 
        # get fields (field_id, field_name, state_id, obs_mode)
        if not os.path.isfile(MeasurementSet_dir+'.fields.json'):
            print2('Preparing '+MeasurementSet_dir+'.fields.json')
            dzliu_list_observing_targets(globals_dict)
        # 
        with open(MeasurementSet_dir+'.fields.json') as fp:
            observing_targets = json.load(fp)
        # 
        unique_field_names = np.array(observing_targets.keys())
        print2('%s contains following %d sources: %s'%(MeasurementSet_dir, len(unique_field_names), ', '.join(unique_field_names.astype(str))))
        for key in unique_field_names:
            # <TODO> we want to process science targets only
            if observing_targets[key]['OBS_MODE'].find('TARGET') >= 0:
                if key not in unique_field_name_dict:
                    unique_field_name_dict[key] = []
                unique_field_name_dict[key].append(MeasurementSet_dir)
    # 
    for key in unique_field_name_dict:
        print2(str(key))
        if str(key) != "pointing6":
            continue
        do_concat = True
        ms_to_concat = unique_field_name_dict[key]
        ms_output = 'Level_3_Concat'+os.sep+str(key)+'.ms'
        json_output = 'Level_3_Concat'+os.sep+str(key)+'.concatenated.measurementsets.json'
        if not os.path.isdir('Level_3_Concat'):
            os.makedirs('Level_3_Concat')
        # check existing files and check consistency
        if os.path.isfile(json_output) and os.path.isdir(ms_output):
            with open(json_output, 'r') as fp:
                ms_concatenated = json.load(fp)
            if set(ms_concatenated) == set(ms_to_concat):
                do_concat = False
        # 
        if do_concat:
            print2('concat(vis = %s, concatvis = \'%s\')'%(ms_to_concat, ms_output))
            concat(vis = ms_to_concat, concatvis = ms_output, freqtol = '30MHz', dirtol = '0.5arcsec')
            print2('Output to "%s"!'%(ms_output))
            with open(json_output, 'w') as fp:
                json.dump(ms_to_concat, fp, sort_keys=True, indent=4)
                print('Output to "%s"!'%(json_output))



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




