#!/usr/bin/env python
# 
# This needs to be run in CASA
# 
# CASA modules/functions used:
#     tb, casalog, mstransform, inp, saveinputs, exportfits, tclean
# 
# Example:
#     sys.path.append('/Users/dzliu/Cloud/Github/Crab.Toolkit.CASA/lib/python')
#     import dzliu_clean; reload(dzliu_clean); dzliu_clean.dzliu_clean(dataset_ms)
# 
# Notes:
#     20200312: numpy too old in CASA 5. np.full not there yet. 
#     20210218: added max_imsize, restoringbeam='common'
#     20210315: added fix_zero_rest_frequency
# 
from __future__ import print_function
import os, sys, re, json, copy, timeit, shutil
import numpy as np
try:
    from taskinit import casalog, tbtool, tb #, ms, iatool
except:
    from casatasks import casalog
    from casatools import table
    tbtool = table
    tb = tbtool()
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
    from impbcor_cli import impbcor_cli_
    impbcor = impbcor_cli_()
    from imsmooth_cli import imsmooth_cli_
    imsmooth = imsmooth_cli_()
else:
    # see CASA 6 updates here: https://alma-intweb.mtk.nao.ac.jp/~eaarc/UM2018/presentation/Nakazato.pdf
    from casatasks import tclean, mstransform, exportfits, concat, split, imstat, impbcor, imsmooth
    #from casatasks import sdbaseline
    #from casatools import ia



# 
# global casalog_origin2
# 
global casalog_origin2
global casalog_origin
casalog_origin2 = 'dzliu_clean'
casalog_origin = 'dzliu_clean'
def set_casalog_origin(origin):
    global casalog_origin2
    global casalog_origin
    casalog_origin2 = casalog_origin
    casalog_origin = origin
    casalog.origin(casalog_origin)
def restore_casalog_origin():
    global casalog_origin2
    global casalog_origin
    casalog_origin = casalog_origin2
    casalog.origin(casalog_origin)



# 
# def print2
# 
def print2(message):
    print(message)
    casalog.post(message, 'INFO')



# 
# def parseSpw()
# 
#   based on https://stackoverflow.com/questions/712460/interpreting-number-ranges-in-python
#   returns a set of selected values when a string in the form:
#   '1~4,6,8,10~12'
#   would return:
#   (1,2,3,4,6,7,10,11,12)
# 
def parseSpw(input_str="", no_chan=False):
    selection = {'spw':[], 'chan':[], 'spw+chan':[]}
    invalid = []
    # tokens are comma seperated values
    tokens = [t.strip() for t in input_str.split(',')]
    for token in tokens:
        # a token could be a spw, a spw+chan (separated with comma), or a range of spw
        # 
        # check if the input spw expression contains channels or not
        chan_expression = ''
        chan_selection = None
        chan_list = []
        if token.find(':') >= 0:
            tokens2 = [t.strip() for t in token.split(':')]
            if len(tokens2) > 1:
                token = tokens2[0]
                chan_expression = tokens2[1]
                chan_selection = parseSpw(chan_expression, no_chan=True)
                chan_list = chan_selection['chan']
        # 
        # check the input spw expression when split out any channel selection
        if len(token) > 0:
            if token[:1] == "<":
                token = "1~%s"%(token[1:])
        try:
            # typically tokens are plain old integers
            selection['spw'].append(int(token))
            selection['chan'].append(chan_list)
            if chan_expression != '':
                selection['spw+chan'].append(token+':'+chan_expression)
            else:
                selection['spw+chan'].append(token)
        except:
            # if not, then it might be a range
            try:
                tokens2 = [int(k.strip()) for k in token.split('~')]
                if len(tokens2) > 1:
                    tokens2.sort()
                    # we have items seperated by a dash
                    # try to build a valid range
                    first = tokens2[0]
                    last = tokens2[len(tokens2)-1]
                    for t in range(first, last+1):
                        selection['spw'].append(t)
                        selection['chan'].append(chan_list)
                        if chan_expression != '':
                            selection['spw+chan'].append(token+':'+chan_expression)
                        else:
                            selection['spw+chan'].append(token)
            except:
                # not an int and not a range...
                invalid.append(token)
    # Report invalid tokens before returning valid selection
    if len(invalid) > 0:
        print("Error! Invalid inputs: " + str(invalid))
        sys.exit()
    # 
    return selection


# 
# def group_consecutives
# 
def group_consecutives(vals, step=1):
    # Return list of consecutive lists of numbers from vals (number list).
    # from https://stackoverflow.com/questions/7352684/how-to-find-the-groups-of-consecutive-elements-from-an-array-in-numpy
    run = []
    result = [run]
    expect = None
    for v in vals:
        if (v == expect) or (expect is None):
            run.append(v)
        else:
            run = [v]
            result.append(run)
        expect = v + step
    return result


# 
# def encodeSpwChannelSelection
# 
#   input [0,1,2,3,4,5,10,11,12,13,14,100,101,102]
#   output '0~5,10~14,100~102'
# 
def encodeSpwChannelSelection(input_spw_chan_selection):
    spw_chan_groups = group_consecutives(input_spw_chan_selection)
    spw_chan_selection_str = ''
    for i in range(len(spw_chan_groups)):
        spw_chan_group = spw_chan_groups[i]
        if len(spw_chan_group) > 1:
            spw_chan_selection_str += '%d~%d'%(spw_chan_group[0], spw_chan_group[-1])
        else:
            spw_chan_selection_str += '%d'%(spw_chan_group[0])
        if i != len(spw_chan_groups)-1:
            spw_chan_selection_str += ';'
    return spw_chan_selection_str








# 
# def get_optimized_imsize
# 
def get_optimized_imsize(imsize, return_decomposed_factors = False):
    # 
    # No CASA module/function used here.
    # 
    #set_casalog_origin('get_optimized_imsize')
    # 
    # try to make imsize be even and only factorizable by 2,3,5,7
    imsize = int(imsize)
    decomposed_factors = []
    # 
    # if imsize is 1, then return it
    if imsize == 1:
        if return_decomposed_factors == True:
            return 1, [1]
        else:
            return 1
    # 
    # make it even
    if imsize % 2 != 0:
        imsize += 1
    # 
    # factorize by 2,3,5,7
    for k in [2, 3, 5, 7]:
        while imsize % k == 0:
            imsize = int(imsize / k)
            decomposed_factors.append(k)
    # 
    # make the non-factorizable number factorizable by 2, 3, 5, or 7
    while imsize != 1 and int( np.prod( [ (imsize % k) for k in [2, 3, 5, 7] ] ) ) != 0:
        # as long as it is factorizable by any of the [2, 3, 5, 7], the mod ("%") will be zero, so the product will also be zero
        #print('imsize', imsize, '(imsize % k)', [ (imsize % k) for k in [2, 3, 5, 7] ], 
        #                               np.prod( [ (imsize % k) for k in [2, 3, 5, 7] ] ) )
        imsize += 1
        #print('imsize', imsize, '(imsize % k)', [ (imsize % k) for k in [2, 3, 5, 7] ], 
        #                               np.prod( [ (imsize % k) for k in [2, 3, 5, 7] ] ) )
        
    # 
    imsize2, decomposed_factors2 = get_optimized_imsize(imsize, return_decomposed_factors = True)
    # 
    imsize = imsize2
    # 
    decomposed_factors.extend(decomposed_factors2)
    # 
    if return_decomposed_factors == True:
        return np.prod(decomposed_factors), decomposed_factors
    else:
        return np.prod(decomposed_factors)



# 
# def get antenna diameter
# 
def get_antenn_diameter(vis):
    # 
    # Requires CASA module/function tb.
    # 
    set_casalog_origin('get_antenn_diameter')
    # 
    tb.open(vis+os.sep+'ANTENNA')
    ant_names = tb.getcol('NAME')
    ant_diams = tb.getcol('DISH_DIAMETER') # meter
    tb.close()
    # 
    minantdiam = np.min(ant_diams) # meter
    print2('ant_diams = %s'%(ant_diams))
    print2('minantdiam = %s [m]'%(minantdiam))
    # 
    restore_casalog_origin()
    # 
    return minantdiam



# 
# def get field phasecenters
#
def get_field_phasecenters(vis, galaxy_name = '', column_name = 'DELAY_DIR'):
    """
    Get Measurement Set phase centers ('DELAY_DIR'). 
    
    Return 3 lists: matched_field_name, matched_field_indices, and matched_field_phasecenters. 
    
    The 3rd return is a list of two lists: a RA_deg and a Dec_deg list.
    
    If galaxy_name is '', then all field phase centers will be returned.
    """
    #
    # Requires CASA module/function tb.
    #
    set_casalog_origin('get_field_phasecenters')
    #
    tb.open(vis+os.sep+'FIELD')
    field_names = tb.getcol('NAME')
    field_phasecenters = [tb.getcell(column_name, i) for i in range(tb.nrows())] # rad,rad
    tb.close()
    #
    if galaxy_name != '':
        galaxy_name_cleaned = re.sub(r'[^a-zA-Z0-9]', r'', galaxy_name).lower() #<TODO># What if someone use "_" as a field name?
    else:
        galaxy_name_cleaned = '' # if the user has input an empty string, then we will get all fields in this vis data.
    #
    matched_field_name = ''
    matched_field_indices = []
    matched_field_phasecenters = []
    for i, field_name in enumerate(field_names):
        # find galaxy_name in field_names:
        field_name_cleaned = re.sub(r'[^a-zA-Z0-9]', r'', field_name).lower()
        field_RA_rad, field_Dec_rad = field_phasecenters[i]
        field_RA_rad = field_RA_rad[0]
        field_Dec_rad = field_Dec_rad[0]
        if field_RA_rad < 0:
            field_RA_rad += 2.0 * np.pi
        field_RA_deg = field_RA_rad / np.pi * 180.0
        field_Dec_deg = field_Dec_rad / np.pi * 180.0
        if galaxy_name_cleaned == '' or field_name_cleaned.startswith(galaxy_name_cleaned):
            matched_field_name = field_name
            matched_field_indices.append(i)
            matched_field_phasecenters.append([field_RA_deg, field_Dec_deg])
    #
    if '' == matched_field_name:
        raise ValueError('Error! Target source %s was not found in the "FIELD" table of the input vis "%s"!'%(galaxy_name, vis))
    #
    matched_field_indices = np.array(matched_field_indices)
    matched_field_phasecenters = np.array(matched_field_phasecenters).T # two columns, nrows
    # 
    restore_casalog_origin()
    # 
    return matched_field_name, matched_field_indices, matched_field_phasecenters



# 
# def get spectral windows
#
def get_spectral_windows(vis, user_min_freq=None, user_max_freq=None):
    """
    Get Measurement Set spectral windows ('SPECTRAL_WINDOW'). 
    
    Return 3 lists: matched_spw_index, matched_spw_num_chan, matched_spw_freq_min_max
    
    The 2nd return is a list of two-element list: a min and a max.
    
    Options:
        user_min_freq, select spw that contains channels with frequency above this value, in Hz.
        user_max_freq, select spw that contains channels with frequency below this value, in Hz.
    
    """
    #
    # Requires CASA module/function tb.
    #
    set_casalog_origin('get_spectral_windows')
    #
    tb.open(vis+os.sep+'SPECTRAL_WINDOW')
    matched_spw_index = []
    matched_spw_num_chan = []
    matched_spw_freq_min_max = []
    for i in range(len(tb.nrows())):
        num_chan = tb.getcell('NUM_CHAN', i)
        chan_freq = tb.getcell('CHAN_FREQ', i)
        min_freq = np.min(chan_freq)
        max_freq = np.max(chan_freq)
        if user_min_freq is not None:
            if max_freq < user_min_freq:
                continue
        if user_max_freq is not None:
            if min_freq > user_max_freq:
                continue
        matched_spw_index.append(i)
        matched_spw_num_chan.append(num_chan)
        matched_spw_freq_min_max.append([min_freq, max_freq])
    tb.close()
    return matched_spw_index, matched_spw_num_chan, matched_spw_freq_min_max




def get_datacolumn(vis):
    # 
    # Requires CASA module/function tb.
    # 
    set_casalog_origin('get_datacolumn')
    # 
    tb.open(vis)
    if 'CORRECTED_DATA' in tb.colnames():
        datacolumn = 'CORRECTED'
    else:
        datacolumn = 'DATA'
    tb.close()
    # 
    restore_casalog_origin()
    # 
    return datacolumn




def fix_zero_rest_frequency(vis):
    # 
    # Requires CASA module/function tb.
    # 
    set_casalog_origin('fix_zero_rest_frequency')
    # 
    do_fix_zero_rest_frequency = False
    tb.open(vis+os.sep+'SOURCE')
    if 'REST_FREQUENCY' in tb.colnames():
        for i in range(tb.nrows()):
            rest_frequency_cell_data = tb.getcell('REST_FREQUENCY', i)
            if rest_frequency_cell_data is not None:
                #print2('Checking REST_FREQUENCY column: %s'%(re.sub(r'\s+', r' ', str(rest_frequency_column_data))))
                if np.any(np.isclose(np.array([rest_frequency_cell_data]), 0)):
                    do_fix_zero_rest_frequency = True
                    break
    tb.close()
    # 
    if do_fix_zero_rest_frequency:
        print2('Found zero REST_FREQUENCY in %s/SOURCE table. Fixing zero rest frequency.'%(vis))
        #ref_frequency_list = None
        #ref_frequency = np.nan
        tb.open(vis+os.sep+'SPECTRAL_WINDOW')
        ref_frequency_list = tb.getcol('REF_FREQUENCY')
        ref_frequency = np.nanmean(ref_frequency_list)
        tb.close()
        # 
        tb.open(vis+os.sep+'SOURCE', nomodify=False)
        for i in range(tb.nrows()):
            if np.isclose(tb.getcell('REST_FREQUENCY', i), 0):
                tb.putcell('REST_FREQUENCY', i, ref_frequency)
                print2('Fixing vis/SOURCE table row %d REST_FREQUENCY to %s'%(i, ref_frequency))
        tb.close()
    # 
    restore_casalog_origin()
    # 
    return
    






# 
# def find_lab_line_name_and_freq
# 
def find_lab_line_name_and_freq(line_name = ''):
    # 
    # No CASA module/function used here.
    # 
    lab_line_dict = {}
    lab_line_dict['HI21cm'] = {'rest-freq': 1.420405751}
    lab_line_dict['[CI]370um'] = {'rest-freq': 809.34197}
    lab_line_dict['[CI]609um'] = {'rest-freq': 492.16065}
    lab_line_dict['CO(1-0)'] = {'rest-freq': 115.2712018}
    lab_line_dict['CO(2-1)'] = {'rest-freq': 230.5380000}
    lab_line_dict['CO(3-2)'] = {'rest-freq': 345.7959899}
    lab_line_dict['CO(4-3)'] = {'rest-freq': 461.0407682}
    lab_line_dict['CO(5-4)'] = {'rest-freq': 576.2679305}
    lab_line_dict['CO(6-5)'] = {'rest-freq': 691.4730763}
    if line_name == '':
        found_lab_line_names = []
        found_lab_line_freqs = []
        for lab_line_name in lab_line_dict.keys():
            found_lab_line_names.append(str(lab_line_name))
            found_lab_line_freqs.append(lab_line_dict[lab_line_name]['rest-freq'])
        found_lab_line_names = np.array(found_lab_line_names)
        found_lab_line_freqs = np.array(found_lab_line_freqs)
        return found_lab_line_names, found_lab_line_freqs
    else:
        line_name_cleaned = re.sub(r'[^a-zA-Z0-9]', r'', line_name).lower()
        found_lab_line_name = None
        found_lab_line_freq = None
        for lab_line_name in lab_line_dict.keys():
            lab_line_name_cleaned = re.sub(r'[^a-zA-Z0-9]', r'', str(lab_line_name)).lower()
            #print('line_name_cleaned', line_name_cleaned, 'lab_line_name_cleaned', lab_line_name_cleaned)
            if line_name_cleaned == lab_line_name_cleaned:
                found_lab_line_name = lab_line_name
                found_lab_line_freq = lab_line_dict[lab_line_name]['rest-freq']
        if found_lab_line_name is None:
            raise Exception('Error! Could not find line name "%s" in our lab line dict! Please update the code!'%(line_name))
        return found_lab_line_name, found_lab_line_freq





# 
# def split_continuum_visibilities
# 
#   NOTE: mstransform does not support multiple channel ranges per spectral window (';'). -- https://casa.nrao.edu/docs/taskref/mstransform-task.html
#   so now I use split() and average bins in each spw, then produce a ms with multiple spws, each spw has only single channel. 
# 
def split_continuum_visibilities(dataset_ms, output_ms, galaxy_name, galaxy_redshift = None, line_name = None, line_velocity = None, line_velocity_width = None):
    # 
    # Requires CASA module/function tb, default, inp, saveinputs, mstransform.
    # 
    set_casalog_origin('split_continuum_visibilities')
    
    # 
    # check existing file
    if os.path.isdir(output_ms):
        print2('Found existing "%s"! Will not overwrite it! Skipping split_continuum_visibilities()!'%(output_ms))
        return
    
    # 
    # get spectral_window and ref_freq
    tb.open(dataset_ms+os.sep+'SPECTRAL_WINDOW')
    spw_names = tb.getcol('NAME')
    spw_chan_freq_col = [tb.getcell('CHAN_FREQ', i) for i in range(tb.nrows())]
    spw_chan_width_col = [tb.getcell('CHAN_WIDTH', i) for i in range(tb.nrows())]
    spw_ref_freq_col = tb.getcol('REF_FREQUENCY')
    spw_ref_chan_col = tb.getcol('MEAS_FREQ_REF')
    tb.close()
    
    valid_spw_indicies = np.argwhere([re.match(r'.*FULL_RES.*', t) is not None for t in spw_names]).flatten().tolist()
    if len(valid_spw_indicies) == 0:
        valid_spw_indicies = np.argwhere([re.match(r'.*WVR.*', t) is None for t in spw_names]).flatten().tolist()
    if len(valid_spw_indicies) == 0:
        raise Exception('Error! No valid spw in the input dataset "%s"! spw_names = %s'%(dataset_ms, spw_names))
    
    # 
    # check user input
    default_velocity = np.nan
    default_velocity_width = np.nan
    do_find_line_free_channels = True
    if galaxy_redshift is None and line_velocity is None:
        # if no galaxy_redshift and line_velocity, we can not find line-free channels!
        do_find_line_free_channels = False
        print2('Warning! No galaxy redshift or velocity information was given! We will assume no line within the bandwidth!')
    elif line_name is not None and (line_velocity is None or line_velocity_width is None):
        # if has line_name but no line velocity or line velocity width, raise error
        raise ValueError('Error! Please input both line_name and line_velocity and line_velocity_width for the line_name "%s"!'%(line_name))
    elif galaxy_redshift is not None and line_velocity is None:
        # if has redshift but no line velocity, use redshift to compute the line velocity
        default_velocity = 2.99792458e5 * galaxy_redshift # km/s, cz (optical definition)
    
    # 
    # make input a list if has input, and update the default velocity values with the mean of the inputs. The default values will be applied for all lines.
    if do_find_line_free_channels:
        
        if line_name is not None:
            if np.isscalar(line_name):
                line_name = [line_name]
        if line_velocity is not None:
            if np.isscalar(line_velocity):
                line_velocity = [line_velocity]
        if line_velocity_width is not None:
            if np.isscalar(line_velocity_width):
                line_velocity_width = [line_velocity_width]
        if line_name is not None:
            if len(line_name) != len(line_velocity) or len(line_name) != len(line_velocity_width):
                raise ValueError('Error! Please input both line_name and line_velocity and line_velocity_width for the line_name "%s"!'%(line_name))
        if line_velocity is not None:
            if np.isnan(default_velocity):
                default_velocity = np.mean(line_velocity)
        if line_velocity_width is not None:
            if np.isnan(default_velocity_width):
                default_velocity_width = np.mean(line_velocity_width)
        else:
            default_velocity_width = 500.0
        
        # 
        # list all lines in lab line list
        lab_line_names, lab_line_freqs = find_lab_line_name_and_freq()
        all_line_velocity = lab_line_freqs*0.0 + default_velocity
        all_line_velocity_width = lab_line_freqs*0.0 + default_velocity_width
        print2('lab_line_names = %s'%(lab_line_names))
        print2('lab_line_freqs = %s'%(lab_line_freqs))
        print2('all_line_velocity = %s'%(all_line_velocity))
        print2('all_line_velocity_width = %s'%(all_line_velocity_width))
        print2('input_line_velocity = %s'%(line_velocity))
        print2('input_line_velocity_width = %s'%(line_velocity_width))
        
        # 
        # update line info with user input
        if line_name is not None:
            for i in range(len(line_name)):
                if line_name[i] == 'cube' or line_name[i] == 'full_cube':
                    continue
                else:
                    lab_line_name, lab_line_freq = find_lab_line_name_and_freq(line_name[i])
                    matched_index = (np.argwhere(lab_line_names==lab_line_name)).tolist()[0]
                    all_line_velocity[matched_index] = line_velocity[i]
                    all_line_velocity_width[matched_index] = line_velocity_width[i]
        
        # 
        # compute obs-frame line frequency
        #all_line_frequency = lab_line_freqs*(1.0-(all_line_velocity/2.99792458e5))*1e9 # Hz, for velocity with radio definition
        all_line_frequency = lab_line_freqs/(1.0+(all_line_velocity/2.99792458e5))*1e9 # Hz, for velocity with optical definition
        print2('all_line_frequency = %s'%(all_line_frequency))
        
        # 
        # find line-free channels
        all_spw_chan_selection_str = ''
        all_spw_chan_selection_mask = []
        for i in valid_spw_indicies:
            spw_chan_freq_list = spw_chan_freq_col[i]
            spw_chan_width_list = spw_chan_width_col[i]
            spw_ref_freq = spw_ref_freq_col[i]
            spw_ref_chan = spw_ref_chan_col[i]
            print2('spw_%d, ref_chan %d, ref_freq %.3e Hz, chan_freq %.3e .. %.3e Hz (%d), chan_width %.3e Hz'%(i, spw_ref_chan, spw_ref_freq, np.max(spw_chan_freq_list), np.min(spw_chan_freq_list), len(spw_chan_freq_list), np.min(spw_chan_width_list) ) )
            # find the target line in these spw
            spw_chan_selection_mask = np.array([True]*len(spw_chan_width_list)) # np.full(len(spw_chan_width_list), True)
            for k in range(len(all_line_frequency)):
                ref_freq_Hz = spw_chan_freq_list[0]
                width_freq_Hz = spw_chan_width_list[0]
                start_freq_Hz = all_line_frequency[k] - 0.5*(all_line_velocity_width[k]/2.99792458e5)*spw_ref_freq #<TODO># lowest freq (as document says) or left-most freq (depending on positive/negative chanwidth)?
                start = (start_freq_Hz - ref_freq_Hz) / width_freq_Hz + ref_chan - 1 # 0-based, see tclean-task.html
                start = int(np.round(start))
                nchan = (all_line_velocity_width[k]/2.99792458e5)*spw_ref_freq / width_freq_Hz # the output number of channels, covering the full line_velocity_width
                nchan = int(np.round(nchan))
                ending_chan = start + nchan - 1
                if start <= len(spw_chan_width_list)-1 and ending_chan >= 0:
                    if start < 0:
                        start = 0
                    if ending_chan > len(spw_chan_width_list)-1:
                        ending_chan = len(spw_chan_width_list)-1
                    spw_chan_selection_mask[start:ending_chan+1] = False
                    print2('found lab_line_name %s, line_frequency %.3e'%(lab_line_names[k], all_line_frequency[k]))
            # 
            # store the chan selection mask and econde into one spw expression, e.g., spw = '0:0~55,1:0~10;11~55' 
            # -- however, mstransform does not support multiple channel range!! see https://casa.nrao.edu/docs/taskref/mstransform-task.html
            # so we will have to loop the valid spw again and do mstransform one spw by one spw. 
            # 
            spw_chan_selection_str = encodeSpwChannelSelection(np.nonzero(spw_chan_selection_mask)[0])
            all_spw_chan_selection_str += '%d:%s'%(i, spw_chan_selection_str)
            if i != valid_spw_indicies[-1]:
                all_spw_chan_selection_str += ','
            # 
            # store the chan selection mask
            all_spw_chan_selection_mask.append(spw_chan_selection_mask)
        # 
        if len(all_spw_chan_selection_mask) == 0:
            raise ValueError('Error! No line free channels with all_line_frequency %s in the input vis "%s"!'%(all_line_frequency, dataset_ms))
        
        print2('spw = %s'%(all_spw_chan_selection_str))
        
    else:
        
        # 
        # simply loop all spws and use all channels therein
        all_spw_chan_selection_str = ''
        all_spw_chan_selection_mask = []
        for i in valid_spw_indicies:
            spw_chan_freq_list = spw_chan_freq_col[i]
            spw_chan_width_list = spw_chan_width_col[i]
            spw_ref_freq = spw_ref_freq_col[i]
            spw_ref_chan = spw_ref_chan_col[i]
            print2('spw_%d, ref_chan %d, ref_freq %.3e Hz, chan_freq %.3e .. %.3e Hz (%d), chan_width %.3e Hz'%(i, spw_ref_chan, spw_ref_freq, np.max(spw_chan_freq_list), np.min(spw_chan_freq_list), len(spw_chan_freq_list), np.min(spw_chan_width_list) ) )
            # 
            spw_chan_selection_mask = np.array([True]*len(spw_chan_width_list)) # np.full(len(spw_chan_width_list), True) # select all channels
            # 
            all_spw_chan_selection_str += '%d'%(i)
            if i != valid_spw_indicies[-1]:
                all_spw_chan_selection_str += ','
            # 
            # store the chan selection mask
            all_spw_chan_selection_mask.append(spw_chan_selection_mask)
    
    
    # 
    # select galaxy name
    matched_field_name, matched_field_indices, matched_field_phasecenters = get_field_phasecenters(dataset_ms, galaxy_name)
    
    # 
    # check data column
    datacolumn = get_datacolumn(dataset_ms)
    
    # 
    # loop and split each chan range of each spw
    all_split_spw_ms = [] # to store temporary splitted spw ms
    for i in valid_spw_indicies:
        # 
        # spw_chan_selection_mask
        spw_chan_selection_mask = all_spw_chan_selection_mask[i]
        if np.count_nonzero(spw_chan_selection_mask) <= 0:
            continue
        # 
        spw_chan_groups = group_consecutives(np.nonzero(spw_chan_selection_mask)[0])
        for k in range(len(spw_chan_groups)):
            # 
            # output_ms_spw
            chan0 = spw_chan_groups[k][0]
            chan1 = spw_chan_groups[k][-1]
            chan_selection_str = '%d~%d'%(chan0, chan1) if chan0 != chan1 else '%d'%(chan0)
            split_spw_ms = re.sub(r'\.ms$', r'', output_ms) + '_spw%d_chan%d_%d.ms'%(i, chan0, chan1)
            all_split_spw_ms.append(split_spw_ms)
            # 
            # check existing data
            if os.path.isdir(split_spw_ms):
                shutil.rmtree(split_spw_ms)
            # 
            # mstransform
            split_parameters = {}
            split_parameters['vis'] = dataset_ms
            split_parameters['outputvis'] = split_spw_ms
            split_parameters['field'] = ','.join(matched_field_indices.astype(str))
            split_parameters['spw'] = '%d:%s'%(i, chan_selection_str)
            split_parameters['datacolumn'] = datacolumn
            split_parameters['width'] = chan1-chan0+1
            split_parameters['keepflags'] = False
            split_parameters['timebin'] = '30s'
            print2('split_parameters = %s'%(split_parameters))
            
            with open(os.path.dirname(output_ms)+os.sep+'saved_split_continuum_visibilities_task_split_inputs_for_continuum_spw%d_chan%d_%d.json'%(i, chan0, chan1), 'w') as fp:
                json.dump(split_parameters, fp, indent = 4)
            
            split(**split_parameters)
            
            if not os.path.isdir(split_spw_ms):
                raise Exception('Error! Failed to run split and produce "%s"!'%(split_spw_ms))
            else:
                print2('Output to "%s"!'%(split_spw_ms))
        
    # 
    # then concatenate
    concat_parameters = {}
    concat_parameters['vis'] = all_split_spw_ms
    concat_parameters['concatvis'] = output_ms
    print2('concat_parameters = %s'%(concat_parameters))
    
    with open(os.path.dirname(output_ms)+os.sep+'saved_split_continuum_visibilities_task_concat_inputs_for_continuum.json', 'w') as fp:
        json.dump(concat_parameters, fp, indent = 4)
    
    concat(**concat_parameters)
    
    if not os.path.isdir(output_ms):
        raise Exception('Error! Failed to run concat and produce "%s"!'%(output_ms))
    else:
        print2('Output to "%s"!'%(output_ms))
    
    # 
    restore_casalog_origin()
    
    #raise NotImplementedError()
    
    return





# 
# def split_line_visibilities
# 
def split_line_visibilities(dataset_ms, output_ms, galaxy_name, line_name, line_velocity, line_velocity_width, line_velocity_resolution):
    # 
    # Requires CASA module/function tb, default, inp, saveinputs, mstransform.
    # 
    set_casalog_origin('split_line_visibilities')
    
    # 
    # check existing file
    # 
    if os.path.isdir(output_ms):
        print2('Found existing "%s"! Will not overwrite it! Skipping split_line_visibilities()!'%(output_ms))
        return
    
    # 
    # check data column
    # 
    datacolumn = get_datacolumn(dataset_ms)
    
    # 
    # get spectral_window and ref_freq
    # 
    tb.open(dataset_ms+os.sep+'SPECTRAL_WINDOW')
    spw_names = tb.getcol('NAME')
    spw_chan_freq_col = [tb.getcell('CHAN_FREQ', i) for i in range(tb.nrows())]
    spw_chan_width_col = [tb.getcell('CHAN_WIDTH', i) for i in range(tb.nrows())]
    spw_ref_freq_col = tb.getcol('REF_FREQUENCY')
    spw_ref_chan_col = tb.getcol('MEAS_FREQ_REF')
    tb.close()
    
    #print('spw_names:', spw_names)
    valid_spw_indicies = np.argwhere([re.match(r'.*FULL_RES.*', t) is not None for t in spw_names]).flatten().tolist()
    if len(valid_spw_indicies) == 0:
        valid_spw_indicies = np.argwhere([(re.match(r'.*WVR.*', t) is None and re.match(r'.*CH_AVG.*', t) is None) for t in spw_names]).flatten().tolist()
    #ref_freq_Hz = np.nan
    
    
    # 
    # calc linefreq
    # 
    # <20200122> we now allow user to input line_name = 'cube', so that it cleans the whole cube
    lineSpwIds = [] # the target line may be contained in multiple spws
    lineSpwChanWidths = [] # a list of of list of channel widths in Hz for each matched line spw, for all matched line spws
    lineSpwChanFreqs = [] # a list of list of channel freqs in Hz for each matched line spw, for all matched line spws
    lineSpwRefFreqs = [] # a list of channel reference freqs in Hz for each matched line spw, for all matched line spws
    lineSpwRefChans = [] # a list of channel reference channel number (1-based) for each matched line spw, for all matched line spws
    if line_name == 'cube' or line_name == 'full_cube':
        for i in valid_spw_indicies:
            spw_chan_freq_list = spw_chan_freq_col[i]
            spw_chan_width_list = spw_chan_width_col[i]
            spw_ref_freq = spw_ref_freq_col[i]
            spw_ref_chan = spw_ref_chan_col[i]
            print2('spw_%d, ref_chan %d, ref_freq %.3e Hz, chan_freq %.3e .. %.3e Hz (%d), chan_width %.3e Hz'%(i, spw_ref_chan, spw_ref_freq, np.max(spw_chan_freq_list), np.min(spw_chan_freq_list), len(spw_chan_freq_list), np.min(spw_chan_width_list) ) )
            # add this spw to our output
            lineSpwIds.append(i)
            lineSpwChanWidths.append(spw_chan_width_list) # append all valid spw 
            lineSpwChanFreqs.append(spw_chan_freq_list)
            lineSpwRefFreqs.append(spw_ref_freq)
            lineSpwRefChans.append(spw_ref_chan)
        #ref_freq_Hz = (np.max(lineSpwChanFreqs) + np.min(lineSpwChanFreqs)) / 2.0 # set to the center of all selected spws
        #ref_chan = 
        #t_max_freq = np.max([np.max(t) for t in lineSpwChanFreqs])
        #t_min_freq = np.min([np.min(t) for t in lineSpwChanFreqs])
        #linefreq = (t_max_freq + t_min_freq) / 2.0 # set to the center of all selected spws
        linefreq = np.nan
        #line_velocity_width = (np.max(lineSpwChanFreqs) - np.min(lineSpwChanFreqs)) / ref_freq_Hz * 2.99792458e5 # set to full frequency range of all selected spws
        #line_velocity_width = (np.max(lineSpwChanFreqs) - np.min(lineSpwChanFreqs)) / linefreq * 2.99792458e5 # set to full frequency range of all selected spws
        #line_velocity_resolution = -1
    else:
        # 
        # find line name from lab line list
        lab_line_name, lab_line_freq = find_lab_line_name_and_freq(line_name)
        #linefreq = lab_line_freq*(1.0-(line_velocity/2.99792458e5))*1e9 # Hz, for velocity with radio definition
        linefreq = lab_line_freq/(1.0+(line_velocity/2.99792458e5))*1e9 # Hz, for velocity with optical definition
        # 
        # find which spw(s) contain(s) the target line
        for i in valid_spw_indicies:
            spw_chan_freq_list = spw_chan_freq_col[i]
            spw_chan_width_list = spw_chan_width_col[i]
            spw_ref_freq = spw_ref_freq_col[i]
            spw_ref_chan = spw_ref_chan_col[i]
            print2('spw_%d, ref_chan %d, ref_freq %.3e Hz, chan_freq %.3e .. %.3e Hz (%d), chan_width %.3e Hz'%(i, spw_ref_chan, spw_ref_freq, np.max(spw_chan_freq_list), np.min(spw_chan_freq_list), len(spw_chan_freq_list), np.min(spw_chan_width_list) ) )
            # find the target line in these spw
            if linefreq >= np.min(spw_chan_freq_list) and linefreq <= np.max(spw_chan_freq_list):
                # found our target line within this spw
                #ref_freq_Hz = spw_ref_freq
                lineSpwIds.append(i)
                lineSpwChanWidths.append(spw_chan_width_list)
                lineSpwChanFreqs.append(spw_chan_freq_list)
                lineSpwRefFreqs.append(spw_ref_freq)
                lineSpwRefChans.append(spw_ref_chan)
    # 
    if len(lineSpwIds) == 0:
        print2('Error! Target line %s at rest-frame %.3f GHz was not covered by the "SPECTRAL_WINDOW" of the input vis "%s"!'%(lab_line_name, lab_line_freq, dataset_ms))
        raise Exception('Error! Target line %s at rest-frame %.3f GHz was not covered by the "SPECTRAL_WINDOW" of the input vis "%s"!'%(lab_line_name, lab_line_freq, dataset_ms))
    
    # if user has not input a line_velocity_resolution, then we take the best line_velocity_resolution
    #if line_velocity_resolution <= 0.0:
    
    # if there are multiple line spws, we need to make sure that have velocity resolution of spws should be better than the line_velocity_width
    valid_linespws_indicies = []
    linechanwidth = np.min([np.min(np.abs(t)) for t in lineSpwChanWidths])
    for i in range(len(lineSpwIds)):
        linechanwidth_i = np.min(np.abs(lineSpwChanWidths[i]))
        if np.isclose(linechanwidth_i, linechanwidth):
            valid_linespws_indicies.append(i)
        else:
            print2('Warning! Discared spw %d due to coarse channel width of %.3e Hz than the finest channel width of %.3e Hz.'%(i, linechanwidth_i, linechanwidth))
    
    # select valid spws
    lineSpwIds = [lineSpwIds[i] for i in valid_linespws_indicies]
    lineSpwChanWidths = [lineSpwChanWidths[i] for i in valid_linespws_indicies]
    lineSpwChanFreqs = [lineSpwChanFreqs[i] for i in valid_linespws_indicies]
    lineSpwRefFreqs = [lineSpwRefFreqs[i] for i in valid_linespws_indicies]
    lineSpwRefChans = [lineSpwRefChans[i] for i in valid_linespws_indicies]
    
    # if more than one spws are selected, then take the average REF_FREQUENCY
    #if len(lineSpwIds) >= 2:
    #    print2('Warning! More than one spws contain the line, we will take the average REF_FREQUENCY.')
    #    ref_freq_Hz = np.mean(lineSpwRefFreqs)
    
    # if linefreq is not given by the line_name, then set it to the center of bandwidth
    t_max_freq = np.max([np.max(t) for t in lineSpwChanFreqs])
    t_min_freq = np.min([np.min(t) for t in lineSpwChanFreqs])
    if np.isnan(linefreq):
        linefreq = (t_max_freq + t_min_freq) / 2.0 # set to the center of all selected spws
    
    # convert channel width from frequency to velocity
    linechanwidth = np.min([np.min(t) for t in lineSpwChanWidths])
    #linechanwidth_kms = linechanwidth / ref_freq_Hz * 2.99792458e5 # km/s
    #linechanwidths_kms = lineSpwChanWidths / ref_freq_Hz * 2.99792458e5 # km/s
    linechanwidth_kms = np.min([np.min(t/q*2.99792458e5) for t,q in list(zip(lineSpwChanWidths,lineSpwRefFreqs))]) # km/s
    
    print2('lineSpwIds = %s'%(lineSpwIds))
    print2('lineSpwRefFreqs = %s'%(lineSpwRefFreqs))
    print2('lineSpwRefChans = %s'%(lineSpwRefChans))
    print2('linefreq = %s'%(linefreq))
    print2('linechanwidth = %.3e Hz'%(linechanwidth))
    print2('linechanwidth_kms = %s km/s'%(linechanwidth_kms))
    print2('line_velocity_width = %s km/s, for output, a negative value means full bandwidth'%(line_velocity_width))
    print2('line_velocity_resolution = %s km/s, for output, a negative value means original channel width'%(line_velocity_resolution))
    
    # 
    # chanbin
    # 
    #chanbin = line_velocity_resolution / np.min(linechanwidth_kms)
    #chanbin = int(np.round(chanbin))
    #print2('chanbin = %s'%(chanbin))
    #chanaverage = True
    #chanbin = chanbin
    
    # 
    # nchan and start and width
    # 
    regridms = True
    if line_velocity_resolution > 0.0 or line_velocity_width > 0.0:
        # if the user has input a positive line_velocity_resolution, then we convert it to channel width factor,
        # or if the user has input a positive line_velocity_width, then we also need freuquency mode to adjust the channel selection.
        mode = 'frequency'
        if line_velocity_resolution <= 0.0:
            line_velocity_resolution = np.abs(linechanwidth_kms)
        width_channel_number = line_velocity_resolution / np.abs(linechanwidth_kms)
        width_channel_number = int(np.round(width_channel_number)) # in units of channel number, like a rebin factor
        width_freq_Hz = width_channel_number * np.abs(linechanwidth)
        width = '%.0fHz'%(width_freq_Hz)
        if line_velocity_width > 0.0:
            start_freq_Hz = linefreq - 0.5*(line_velocity_width/2.99792458e5)*linefreq #<TODO># lowest freq (as document says) or left-most freq (depending on positive/negative chanwidth)?
            start = '%.0fHz'%(start_freq_Hz)
            nchan = (line_velocity_width/2.99792458e5)*linefreq / width_freq_Hz # the output number of channels, covering the full line_velocity_width
            nchan = int(np.round(nchan))
        else:
            # if user has input a negative line_velocity_width, then we use the full bandwidth
            #t_max_freq = np.max([np.max(t) for t in lineSpwChanFreqs])
            #t_min_freq = np.min([np.min(t) for t in lineSpwChanFreqs])
            start_freq_Hz = t_min_freq
            start = '%.0fHz'%(start_freq_Hz)
            nchan = (t_max_freq-t_min_freq) / width_freq_Hz + 1
            nchan = int(np.round(nchan))
        #start_chan = (linefreq - ref_freq_Hz) / width_freq_Hz + ref_chan - 1 #<20210511><BUG><FIXED># 0-based, see tclean-task.html 
        #start_chan = int(np.round(start_chan))
        #restfreq = '%.0fHz'%(ref_freq_Hz)
    else:
        # otherwise keep the original channel width and full bandwidth
        mode = 'channel'
        regridms = False
        width_channel_number = 1
        width_freq_Hz = width_channel_number * np.abs(linechanwidth) #<20210511><BUG><FIXED># linechanwidth -> np.abs(linechanwidth). This affects datasets with negative chan freq width, and results into truncated channel ranges.
        width = 1
        start_freq_Hz = linefreq - 0.5*(line_velocity_width/2.99792458e5)*linefreq #<TODO># lowest freq (as document says) or left-most freq (depending on positive/negative chanwidth)?
        if line_velocity_width > 0.0:
            # well this should not happen because we will use frequency mode if line_velocity_width > 0.0, see above.
            nchan = (line_velocity_width/2.99792458e5)*linefreq / width_freq_Hz # the output number of channels, covering the full line_velocity_width
            nchan = int(np.round(nchan))
            start_chan_list = []
            for i in range(len(lineSpwIds)):
                start_chan_one = (start_freq_Hz - lineSpwRefFreqs[i]) / np.mean(lineSpwChanWidths[i]) + lineSpwRefChans[i] - 1 #<20210511><BUG><FIXED># 0-based, see tclean-task.html 
                start_chan_one = int(np.round(start_chan_one))
                #<TODO># note that if we do not use frequency mode this is inaccurate and can not deal with negative chan freq width
            start = ','.join(np.array(start_chan_list).astype(str)) #<TODO># can we really input multiple start?
        else:
            # if user has input a negative line_velocity_width, then we use the full bandwidth
            #t_max_freq = np.max([np.max(t) for t in lineSpwChanFreqs])
            #t_min_freq = np.min([np.min(t) for t in lineSpwChanFreqs])
            start = ''
            nchan = (t_max_freq-t_min_freq) / width_freq_Hz + 1
            nchan = int(np.round(nchan))
        #restfreq = '%.0fHz'%(ref_freq_Hz)
        #<20210511><BUG><FIXED># This bug affects all previous image cubes which have negative channel frequency width. 
        #<20210511><BUG><FIXED># Coincidentally image cubes with positive channel frequency width are unaffected because
        #<20210511><BUG><FIXED># previously start = (start_freq_Hz - ref_freq_Hz) / width_freq_Hz which is negative and . 
        #<20210511><BUG><FIXED># treated as 0. 
    
    # 
    # select galaxy name
    # 
    matched_field_name, matched_field_indices, matched_field_phasecenters = get_field_phasecenters(dataset_ms, galaxy_name)
    
    # 
    # check whether we can combinespws
    # 
    combinespws = False
    if len(lineSpwIds) >= 2:
        first_chan_num = 0
        check_chan_num_consistency = True
        for i in range(len(lineSpwIds)):
            if first_chan_num == 0:
                first_chan_num = len(lineSpwChanFreqs[i])
            elif first_chan_num != len(lineSpwChanFreqs[i]):
                check_chan_num_consistency = False
                break
        # 
        if not check_chan_num_consistency:
            # try to fix different chan num issue
            #raise NotImplementedError()
            combinespws = False
            print2('Warning! There are multiple line spws and their channel numbers are different! mstransform has to use combinespws = False.')
        # 
        if check_chan_num_consistency:
            combinespws = True
    
    
    # 
    # mstransform
    # 
    mstransform_parameters = {}
    mstransform_parameters['vis'] = dataset_ms
    mstransform_parameters['outputvis'] = output_ms
    mstransform_parameters['field'] = ','.join(matched_field_indices.astype(str))
    mstransform_parameters['spw'] = ','.join(np.array(lineSpwIds).astype(str))
    mstransform_parameters['datacolumn'] = datacolumn
    mstransform_parameters['regridms'] = regridms
    mstransform_parameters['mode'] = mode
    mstransform_parameters['start'] = start
    mstransform_parameters['width'] = width
    mstransform_parameters['nchan'] = nchan
    mstransform_parameters['nspw'] = 1 # it means, do not separate the spws.
    mstransform_parameters['combinespws'] = combinespws
    mstransform_parameters['outframe'] = 'LSRK'
    mstransform_parameters['veltype'] = 'radio'
    mstransform_parameters['timeaverage'] = True
    mstransform_parameters['timebin'] = '30s'
    # 
    # Reset tclean parameters
    # 
    #default(mstransform)
    # 
    # Apply to global variables
    # 
    #for t in mstransform_parameters:
    #    globals()[t] = mstransform_parameters[t]
    #    locals()[t] = mstransform_parameters[t]
    
    #inp(mstransform)
    
    #saveinputs('mstransform', os.path.dirname(output_ms)+os.sep+'saved_mstransform_inputs.txt')
    
    #mstransform()
    
    with open(os.path.dirname(output_ms)+os.sep+'saved_mstransform_inputs.json', 'w') as fp:
        json.dump(mstransform_parameters, fp, indent = 4)
    
    mstransform(**mstransform_parameters)
    
    if not os.path.isdir(output_ms):
        raise Exception('Error! Failed to run mstransform and produce "%s"!'%(output_ms))
    
    # 
    restore_casalog_origin()





# 
# def arcsec2float
# 
def arcsec2float(arcsec_str):
    arcsec_value = np.nan
    if re.match(r'^.*arcsec$', arcsec_str.strip().lower()):
        arcsec_value = float(re.sub(r'arcsec$', r'', arcsec_str.strip().lower()))
    elif re.match(r'^.*arcmin$', arcsec_str.strip().lower()):
        arcsec_value = float(re.sub(r'arcmin$', r'', arcsec_str.strip().lower())) * 60.0
    elif re.match(r'^.*(deg|degree)$', arcsec_str.strip().lower()):
        arcsec_value = float(re.sub(r'(deg|degree)$', r'', arcsec_str.strip().lower())) * 3600.0
    else:
        try:
            arcsec_value = float(arcsec_str)
        except:
            raise ValueError('Error! Could not convert the input string "%s" to a float value in units of arcsec!'%(arcsec_str))
    return arcsec_value





# 
# def prepare_clean_parameters
# 
def prepare_clean_parameters(vis, imagename, imcell = None, imsize = None, niter = 30000, calcres = True, calcpsf = True, 
                             phasecenter = '', field = '', pbmask = 0.2, pblimit = 0.1, threshold = 0.0, specmode = 'cube', 
                             beamsize = '', max_imsize = None):
    # 
    # Requires CASA module/function tb.
    # 
    set_casalog_origin('prepare_clean_parameters')
    
    # 
    # check field, makes sure there is only one field -- not exactly true, because for mosaics there are multiple fields but they are the same galaxy.
    # 
    #tb.open(vis+os.sep+'FIELD')
    #field_count = tb.nrows()
    #tb.close()
    #if field_count > 1:
    #    raise Exception('Error! The input vis has multiple fields! Please split the target field before calling prepare_clean_parameters()!')
    
    # 
    # check field, makes sure there is only one spw
    # 
    tb.open(vis+os.sep+'SPECTRAL_WINDOW')
    spw_count = tb.nrows()
    spw_ref_chan_col = tb.getcol('MEAS_FREQ_REF')
    spw_ref_freq_col = tb.getcol('REF_FREQUENCY')
    tb.close()
    # 
    check_spw_ref_freq_consistency = True
    if spw_count > 1 and specmode != 'mfs':
        for ispw in range(len(spw_ref_freq_col)):
            if spw_ref_freq_col[ispw] != spw_ref_freq_col[0]:
                check_spw_ref_freq_consistency = False
                break
        if check_spw_ref_freq_consistency == False:
            raise Exception('Warning! The input vis "%s" has multiple spws and they do not have the same REF_FREQUENCY! We will recalculate ref_freq as the bandwidth center!'%(vis))
            #'Please split/mstransform the target line channels into one spw before calling prepare_clean_parameters()!'
    # 
    ref_freq_Hz = spw_ref_freq_col[0]
    ref_chan = spw_ref_chan_col[0]
    
    # 
    # if user has input a beamsize, then use it
    # 
    if beamsize != '':
        synbeam = arcsec2float(beamsize)
        if imcell is None:
            oversampling = 5.0
            imcell_arcsec = synbeam / oversampling
            imcell = '%sarcsec'%(imcell_arcsec)
        else:
            imcell_arcsec = arcsec2float(imcell)
        # 
        print2('synbeam = %s [arcsec]'%(synbeam))
        print2('imcell_arcsec = %s'%(imcell_arcsec))
    # 
    # otherwise compute beamsize and imcell
    # 
    else:
        # 
        # check imcell
        # 
        if imcell is None:
            # 
            # get state and obs_mode
            # 
            #[20191018]#tb.open(vis+os.sep+'STATE')
            #[20191018]#state_ID_col = np.arange(tb.nrows())
            #[20191018]#state_obs_mode_col = tb.getcol('OBS_MODE')
            #[20191018]#tb.close()
            #[20191018]## 
            #[20191018]#if len(state_ID_col) > 0:
            #[20191018]#    valid_state_indices = []
            #[20191018]#    for i,obs_mode in enumerate(state_obs_mode_col):
            #[20191018]#        if obs_mode.find('ON_SOURCE') >= 0 or obs_mode.find('OBSERVE_TARGET') >= 0:
            #[20191018]#            valid_state_indices.append(i)
            #[20191018]#    # 
            #[20191018]#    if 0 == len(valid_state_indices):
            #[20191018]#        raise ValueError('Error! No valid state "ON_SOURCE" in the "STATE" of the input vis "%s"! The "STATE" table contains following "OBS_MODE": %s'%(vis, str(state_obs_mode_col)))
            #[20191018]#    # 
            #[20191018]#    valid_state_indices = np.array(valid_state_indices)
            #[20191018]#else:
            #[20191018]#    valid_state_indices = np.array([-1])
            # 
            # get data_desc_id to spw_id mapper
            # 
            #tb.open(vis+os.sep+'DATA_DESCRIPTION')
            #data_desc_spw_col = tb.getcol('SPECTRAL_WINDOW_ID')
            #tb.close()
            #
            #valid_data_desc_indicies = []
            #for i,data_desc_spw in enumerate(data_desc_spw_col):
            #    if data_desc_spw in lineSpwIds:
            #        valid_data_desc_indicies.append(i)
            #
            #if 0 == len(valid_data_desc_indicies):
            #    raise ValueError('Error! No valid data desc spw in the "DATA_DESCRIPTION" of the input vis "%s"!'%(vis))
            #
            #valid_data_desc_indicies = np.array(valid_data_desc_indicies)
            
            # 
            # get uvdist
            # 
            tb.open(vis)
            uvw = tb.getcol('UVW') # shape (3, nrows), each row is a (u,v,w) array
            ##print2('tb.query(\'FIELD_ID in [%s] AND DATA_DESC_ID in [%s] AND STATE_ID in [%s]\', \'UVW\')'%(','.join(matched_field_indices.astype(str)), ','.join(valid_data_desc_indicies.astype(str)), ','.join(valid_state_indices.astype(str))))
            ##result = tb.query('FIELD_ID in [%s] AND DATA_DESC_ID in [%s] AND STATE_ID in [%s]'%(','.join(matched_field_indices.astype(str)), ','.join(valid_data_desc_indicies.astype(str)), ','.join(valid_state_indices.astype(str))), 'UVW')
            #print2('tb.query(\'FIELD_ID in [%s] AND STATE_ID in [%s]\', \'UVW\')'%(','.join(matched_field_indices.astype(str)), ','.join(valid_state_indices.astype(str))))
            #result = tb.query('FIELD_ID in [%s] AND STATE_ID in [%s]'%(','.join(matched_field_indices.astype(str)), ','.join(valid_state_indices.astype(str))), 'UVW')
            #uvw = result.getcol('UVW')
            tb.close()
            # 
            uvdist = np.sqrt(np.sum(np.square(uvw[0:2, :]), axis=0))
            maxuvdist = np.max(uvdist)
            print2('maxuvdist = %s [m]'%(maxuvdist))
            L80uvdist = np.percentile(uvdist, 80) # np.max(uvdist) # now I am using 90-th percentile of baselies, same as used by 'analysisUtils.py' pickCellSize() getBaselineStats(..., percentile=...)
            print2('L80uvdist = %s [m] (80-th percentile)'%(L80uvdist))
            # 
            synbeam = 2.99792458e8 / ref_freq_Hz / maxuvdist / np.pi * 180.0 * 3600.0 # arcsec
            synbeam = 0.574 * 2.99792458e8 / ref_freq_Hz / L80uvdist / np.pi * 180.0 * 3600.0 # arcsec # .574lambda/L80, see 'analysisUtils.py' estimateSynthesizedBeamFromASDM()
            synbeam_nprec = 2 # keep 2 valid 
            synbeam_ndigits = (synbeam_nprec-1) - int(np.floor(np.log10(synbeam))) # keep to these digits (precision) after point, e.g., 0.1523 -> nprec 2 -> round(0.1523*100)/100 = 0.15
            synbeam = (np.round(synbeam * 10**(synbeam_ndigits))) / 10**(synbeam_ndigits)
            oversampling = 5.0
            imcell_arcsec = synbeam / oversampling
            imcell = '%sarcsec'%(imcell_arcsec)
            print2('synbeam = %s [arcsec]'%(synbeam))
            print2('imcell_arcsec = %s'%(imcell_arcsec))
            # 
        else:
            imcell_arcsec = arcsec2float(imcell)
        
    # 
    # check imsize
    # 
    if imsize is None:
        # 
        # get antdiam
        # 
        minantdiam = get_antenn_diameter(vis)
        # 
        # get field and phase centers
        # 
        matched_field_name, matched_field_indices, matched_field_phasecenters = get_field_phasecenters(vis, field)
        matched_field_min_RA_deg = np.min(matched_field_phasecenters[0, :])
        matched_field_max_RA_deg = np.max(matched_field_phasecenters[0, :])
        matched_field_min_Dec_deg = np.min(matched_field_phasecenters[1, :])
        matched_field_max_Dec_deg = np.max(matched_field_phasecenters[1, :])
        #print('matched_field_phasecenters.shape', matched_field_phasecenters.shape)
        #print('matched_field_phasecenters:', matched_field_phasecenters)
        #raise NotImplementedError()
        # 
        # calc primary beam
        # 
        pribeam = 1.13  * (2.99792458e8 / ref_freq_Hz / minantdiam / np.pi * 180.0 ) # in units of degrees, see -- https://help.almascience.org/index.php?/Knowledgebase/Article/View/90
        print2('minantdiam = %s [meter]'%(minantdiam))
        print2('pribeam = %s [arcsec]'%(pribeam * 3600.0))
        print2('matched_field_min_RA_deg = %s'%(matched_field_min_RA_deg))
        print2('matched_field_max_RA_deg = %s'%(matched_field_max_RA_deg))
        print2('matched_field_min_Dec_deg = %s'%(matched_field_min_Dec_deg))
        print2('matched_field_max_Dec_deg = %s'%(matched_field_max_Dec_deg))
        imsize_RA_deg = (matched_field_max_RA_deg - matched_field_min_RA_deg) * np.cos(np.deg2rad((matched_field_max_Dec_deg+matched_field_min_Dec_deg)/2.0)) + 2.0*pribeam
        imsize_Dec_deg = (matched_field_max_Dec_deg - matched_field_min_Dec_deg) + 2.0*pribeam
        imsize_RA = imsize_RA_deg / (imcell_arcsec / 3600.0) # pixels
        imsize_Dec = imsize_Dec_deg / (imcell_arcsec / 3600.0) # pixels
        print2('imsize_RA = %s [arcsec]'%(imsize_RA_deg * 3600.0))
        print2('imsize_Dec = %s [arcsec]'%(imsize_Dec_deg * 3600.0))
        imsize = [get_optimized_imsize(imsize_RA), get_optimized_imsize(imsize_Dec)]
    # 
    print2('imsize = %s'%(imsize))
    # 
    if max_imsize is not None:
        if np.isscalar(max_imsize):
            max_imsize = [max_imsize, max_imsize]
        else:
            if len(max_imsize) == 1:
                max_imsize = [max_imsize[0], max_imsize[0]]
        if imsize[0] > max_imsize[0]:
            imsize[0] = max_imsize[0]
            print2('imsize[0] = %s, as limited by max_imsize[0] %s.'%(imsize[0], max_imsize[0]))
        if imsize[1] > max_imsize[1]:
            imsize[1] = max_imsize[1]
            print2('imsize[1] = %s, as limited by max_imsize[1] %s.'%(imsize[1], max_imsize[1]))
    # 
    # We can also use analysisUtils, but the results are very similar to my above implementation.
    # 
    #au_cellsize, au_imsize, au_centralField = au.pickCellSize(vis, imsize=True, npix=5)
    #au.plotmosaic(vis, 'NGC_4321')
    # 
    # Prepare tclean parameters
    # 
    clean_parameters = {}
    clean_parameters['vis'] = vis
    clean_parameters['selectdata'] = True
    clean_parameters['field'] = '' # ','.join(matched_field_indices.astype(str))
    clean_parameters['spw'] = ''
    clean_parameters['phasecenter'] = phasecenter
    clean_parameters['cell'] = imcell # tclean parameter name
    clean_parameters['imsize'] = imsize # tclean parameter name
    clean_parameters['imagename'] = imagename # output_dir+os.sep+'%s_%s_cleaned'%(galaxy_name_cleaned, linename)
    clean_parameters['gridder'] = 'mosaic' # 'standard'
    clean_parameters['specmode'] = specmode # 'cube' # for spectral line cube
    clean_parameters['outframe'] = 'LSRK'
    clean_parameters['deconvolver'] = 'hogbom'
    clean_parameters['usemask'] = 'pb' # construct a 1/0 mask at the 0.2 level
    clean_parameters['pbmask'] = pbmask # data outside this pbmask will not be fitted
    clean_parameters['threshold'] = threshold
    #clean_parameters['usemask'] = 'user' #<TODO># 
    #clean_parameters['mask'] = '' #<TODO># 
    clean_parameters['pblimit'] = pblimit # data outside this pblimit will be output as NaN
    clean_parameters['pbcor'] = True # create both pbcorrected and uncorrected images
    clean_parameters['restoration'] = True
    clean_parameters['restoringbeam'] = 'common' # '%sarcsec'%(synbeam) # Automatically estimate a common beam shape/size appropriate for all planes.
    #clean_parameters['weighting'] = 'briggs'
    #clean_parameters['robust'] = '2.0' # robust = -2.0 maps to A=1,B=0 or uniform weighting. robust = +2.0 maps to natural weighting. (robust=0.5 is equivalent to robust=0.0 in AIPS IMAGR.)
    clean_parameters['nterms'] = 1 # nterms must be ==1 when deconvolver='hogbom' is chosen
    clean_parameters['chanchunks'] = -1 # This feature is experimental and may have restrictions on how chanchunks is to be chosen. For now, please pick chanchunks so that nchan/chanchunks is an integer. 
    clean_parameters['interactive'] = False
    #clean_parameters['savemodel'] = 'virtual' # 'none', 'virtual', 'modelcolumn'. 'virtual' for simple gridding, 'modelcolumn' for gridder='awproject'.
    #niter = 30000
    #calcres = True # calculate initial residual image at the beginning of the first major cycle
    #calcpsf = True
    if calcres==False and niter==0:
        print2('Note: Only the PSF will be made and no data will be gridded in the first major cycle of cleaning.')
    elif calcres==False and niter>0:
        print2('Note: We will assume that a "*.residual" image already exists and that the minor cycle can begin without recomputing it.')
    elif calcres==True:
        if calcpsf==False and not (os.path.isfile(imagename+'.psf') and os.path.isfile(imagename+'.sumwt')):
            calcpsf = True # calcres=True requires that calcpsf=True or that the .psf and .sumwt images already exist on disk (for normalization purposes)
    clean_parameters['niter'] = niter
    clean_parameters['calcres'] = calcres
    clean_parameters['calcpsf'] = calcpsf
    
    # 
    # Check mpicasa
    if 'processor_origin' in globals():
        global processor_origin
        if processor_origin.find('MPIClient') >= 0:
            print2('going parallel!')
            clean_parameters['parallel'] = True
    
    # 
    # Reset tclean parameters
    # 
    #default(tclean)
    
    # 
    # Apply to global variables
    # 
    #for t in clean_parameters:
    #    globals()[t] = clean_parameters[t]
    
    # 
    restore_casalog_origin()
    
    # 
    # Return
    # 
    return clean_parameters




def run_tclean_with_clean_parameters(clean_parameters):
    # 
    # Requires CASA module/function default, inp, saveinputs, tclean.
    # 
    set_casalog_origin('run_tclean_with_clean_parameters')
    # 
    # Reset tclean parameters
    # 
    #default(tclean)
    # 
    # Apply to global variables
    # 
    #for t in clean_parameters:
    #    globals()[t] = clean_parameters[t]
    #    locals()[t] = clean_parameters[t]
    # 
    # Load vis, imagename
    # 
    vis = clean_parameters['vis']
    imagename = clean_parameters['imagename']
    # 
    # Check existing file
    # 
    if os.path.isdir(imagename+'.image'):
        raise Exception('Error! Found existing "%s"! Will not overwrite!'%(imagename+'.image'))
        return
    # 
    # Print and save inputs
    # 
    #inp(tclean)
    #saveinputs('tclean', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.txt')
    # 
    # Run tclean
    # 
    #tclean()
    # 
    # 
    # Print and save inputs (New method)
    # 
    with open(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.json', 'w') as fp:
        json.dump(clean_parameters, fp, indent = 4)
    # 
    print2('clean_parameters = %s'%(clean_parameters))
    # 
    # Run tcleans (New method)
    # 
    tclean(**clean_parameters)
    # 
    # Check outputs
    # 
    if os.path.isdir(imagename+'.image'):
        print2('Cleaning seems finished sucessfully.')
        exportfits(imagename+'.image', imagename+'.image.fits')
        exportfits(imagename+'.image.pbcor', imagename+'.image.pbcor.fits')
        exportfits(imagename+'.psf', imagename+'.psf.fits')
        exportfits(imagename+'.pb', imagename+'.pb.fits')
        exportfits(imagename+'.model', imagename+'.model.fits')
        exportfits(imagename+'.residual', imagename+'.residual.fits')
        if os.path.isdir(imagename+'.mask'):
            exportfits(imagename+'.mask', imagename+'.mask.fits')
    else:
        raise Exception('Error! tclean failed to produce the output image "%s"!'%(imagename+'.image'))
    # 
    restore_casalog_origin()




def make_dirty_image(vis, imagename, **kwargs):
    # 
    # Check existing file
    # 
    if os.path.isdir(imagename+'.image'):
        print2('Found existing "%s"! Will not overwrite it! Skipping make_dirty_image()!'%(imagename+'.image'))
        return
    else:
        # 
        # prepare_clean_parameters
        clean_parameters = prepare_clean_parameters(vis, imagename, niter = 0, **kwargs)
        # 
        # run_tclean_with_clean_parameters
        run_tclean_with_clean_parameters(clean_parameters)
        # 
        # copy saved_tclean_inputs.txt
        #shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.txt', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_dirty_cube.txt')
        shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.json', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_dirty_cube.json')




def make_clean_image(vis, imagename, **kwargs):
    # 
    # Check existing file
    # 
    if os.path.isdir(imagename+'.image'):
        print2('Found existing "%s"! Will not overwrite it! Skipping make_clean_image()!'%(imagename+'.image'))
        return
    else:
        # 
        # prepare_clean_parameters
        clean_parameters = prepare_clean_parameters(vis, imagename, niter = 30000, **kwargs)
        # 
        # run_tclean_with_clean_parameters
        run_tclean_with_clean_parameters(clean_parameters)
        # 
        # copy saved_tclean_inputs.txt
        #shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.txt', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_clean_cube.txt')
        shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.json', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_clean_cube.json')




def make_dirty_image_of_continuum(vis, imagename, **kwargs):
    # 
    # Check existing file
    # 
    if os.path.isdir(imagename+'.image'):
        print2('Found existing "%s"! Will not overwrite it! Skipping make_dirty_image_of_continuum()!'%(imagename+'.image'))
        return
    else:
        # 
        # prepare_clean_parameters
        clean_parameters = prepare_clean_parameters(vis, imagename, niter = 0, specmode = 'mfs', **kwargs)
        # 
        # run_tclean_with_clean_parameters
        run_tclean_with_clean_parameters(clean_parameters)
        # 
        # copy saved_tclean_inputs.txt
        #shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.txt', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_dirty_cube_of_continuum.txt')
        shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.json', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_dirty_cube_of_continuum.json')




def make_clean_image_of_continuum(vis, imagename, **kwargs):
    # 
    # Check existing file
    # 
    if os.path.isdir(imagename+'.image'):
        print2('Found existing "%s"! Will not overwrite it! Skipping make_clean_image_of_continuum()!'%(imagename+'.image'))
        return
    else:
        # 
        # prepare_clean_parameters
        clean_parameters = prepare_clean_parameters(vis, imagename, niter = 30000, specmode = 'mfs', **kwargs)
        # 
        # run_tclean_with_clean_parameters
        run_tclean_with_clean_parameters(clean_parameters)
        # 
        # copy saved_tclean_inputs.txt
        #shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.txt', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_clean_cube_of_continuum.txt')
        shutil.copy(os.path.dirname(imagename)+os.sep+'saved_tclean_inputs.json', os.path.dirname(imagename)+os.sep+'saved_tclean_inputs_for_clean_cube_of_continuum.json')




# 
# def project_fits_cube
# 
def project_fits_cube(input_fits_cube, template_fits_cube, output_fits_cube, overwrite = False):
    # 
    # We will project the input_fits_cube to the pixel grid of the template_fits_cube_or_wcs
    # by matching the World Coordinate System (WCS). 
    # 
    # We can process both fits cubes and images. 
    # 
    # No CASA module required. 
    # 
    # Superseding part of the process_clean_mask() code
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.table import Table
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    from scipy.interpolate import griddata
    # 
    # Read template_fits_cube_or_wcs
    if type(template_fits_cube) is astropy.wcs.WCS:
        # If input is a fits wcs
        template_fits_header = template_fits_cube_or_wcs.to_header()
    elif type(template_fits_cube) is astropy.io.fits.Header:
        # If input is a fits wcs
        template_fits_header = template_fits_cube
    else:
        # If input is a fits file
        print('Reading "%s"'%(template_fits_cube))
        template_hdulist = fits.open(template_fits_cube)
        template_hdu = template_hdulist[0]
        template_fits_header = template_hdu.header
    # 
    # Read input_fits_cube
    print('Reading "%s"'%(input_fits_cube))
    input_hdulist = fits.open(input_fits_cube)
    input_hdu = input_hdulist[0]
    input_fits_header = input_hdu.header
    input_fits_data = input_hdu.data
    input_fits_data_shape = list(input_fits_data.shape)
    # 
    # Make sure the input is a 3D cube or at least a 2D image
    if int(input_fits_header['NAXIS']) < 2:
        raise Exception('Error! The input fits cube "%s" does not have more than 2 dimensions!'%(input_fits_cube))
    if int(template_fits_header['NAXIS']) < 2:
        raise Exception('Error! The input fits cube "%s" does not have more than 2 dimensions!'%(template_fits_cube))
    # 
    # Make sure the input fits data have at least equal dimensions as the template fits data. For extra higher dimensions, we will loop them over.
    #if int(input_fits_header['NAXIS']) < int(template_fits_header['NAXIS']):
    #    raise Exception('Error! The input fits cube "%s" has %d dimensions but the template "%s" has %d dimensions!'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
    # 
    # Take the template fits dimension.
    naxis = min(int(input_fits_header['NAXIS']), int(template_fits_header['NAXIS']))
    # 
    # Do velocity-to-frequency conversion before checking header consistency
    if naxis >= 3:
        if input_fits_header['CTYPE3'].strip().upper() == 'VRAD' and template_fits_header['CTYPE3'].strip().upper() == 'FREQ':
            ctype3 = input_fits_header['CTYPE3']
            cunit3 = input_fits_header['CUNIT3'].strip().replace(' ','').lower()
            crpix3 = input_fits_header['CRPIX3']
            crval3 = input_fits_header['CRVAL3']
            cdelt3 = input_fits_header['CDELT3']
            if cunit3 == 'km/s' or cunit3 == 'kms-1':
                c30 = 2.99792458e5
            else:
                c30 = 2.99792458e8
            input_fits_header['CRVAL3'] = (1.0-(crval3/c30))*input_fits_header['RESTFRQ'] # Hz, (nu0-nu)/nu0 = (v/c), so nu = (1-(v/c))*nu0
            input_fits_header['CDELT3'] = (-(cdelt3/c30))*input_fits_header['RESTFRQ'] # Hz, reversed order
            input_fits_header['CTYPE3'] = 'FREQ'
            input_fits_header['CUNIT3'] = 'Hz'
    # 
    # Check header consistency and record NAXISi
    inaxis = []
    tnaxis = []
    for i in range(1, naxis+1):
        if input_fits_header['CTYPE%d'%(i)].strip().upper() != template_fits_header['CTYPE%d'%(i)].strip().upper():
            raise Exception('Error! The input fits cube "%s" CTYPE%d is %s but the template "%s" CTYPE%d is %s!'%(\
                                input_fits_cube, i, input_fits_header['CTYPE%d'%(i)].strip(), \
                                template_fits_cube, i, template_fits_header['CTYPE%d'%(i)].strip() ) )
        inaxis.append(int(input_fits_header['NAXIS%d'%(i)]))
        tnaxis.append(int(template_fits_header['NAXIS%d'%(i)]))
    inaxis = np.array(inaxis[::-1]) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    tnaxis = np.array(tnaxis[::-1]) # [nx, ny, nchan, ....], it is inverted to the Python array dimension order
    inaxis_str = 'x'.join(inaxis.astype(str))
    tnaxis_str = 'x'.join(tnaxis.astype(str))
    # 
    # If input fits data have extra higher dimensions than the template data, we will condense the additional dimensions into one extra dimension, and later we will loop them over and do the interpolation slice-by-slice.
    idataslice = 0
    if int(input_fits_header['NAXIS']) > naxis:
        print2('Warning! The input fits cube "%s" has %d dimensions while the template "%s" has only %d dimensions! We will loop the extra higher dimensions of the input data slice-by-slice and project to template pixel grid.'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
        idatashape = copy.copy(input_fits_data_shape[::-1][0:naxis])
        idataslice = np.product(input_fits_data_shape[::-1][naxis:])
        idatashape.append(idataslice)
        idatashape = idatashape[::-1]
        input_fits_data.shape = idatashape
        output_fits_data_shape = copy.copy(tnaxis[::-1])
        # here we reshape the input data to shrink all higher dimensions into one extra dimension, 
        # e.g., from (m,n,a,b,c) to (x,a,b,c), when the template data shape is (a,b,c), and x = m*n. 
    # 
    # Otherwise if the template fits data have extra higher dimensions, we will only use the common dimensions, while pad extra dimensions with np.newaxis
    elif int(template_fits_header['NAXIS']) > naxis:
        print2('Warning! The input fits cube "%s" has %d dimensions while the template "%s" has %d dimensions! We will ignore the extra higher dimensions in the template for computation and simply reshape the output data to the template dimensions.'%(input_fits_cube, input_fits_header['NAXIS'], template_fits_cube, template_fits_header['NAXIS']))
        odatashape = []
        idataslice = -(int(template_fits_header['NAXIS']) - naxis)
        for i in range(naxis):
            odatashape.append(tnaxis[i]) # template_fits_header['NAXIS%d'(i+1)]
        for i in range(naxis, naxis-idataslice):
            odatashape.append(1) # template_fits_header['NAXIS%d'(i+1)]
        odatashape = odatashape[::-1]
        output_fits_data_shape = odatashape
    # 
    # Otherwise the output fits data shape is the same as the template fits data shape
    else:
        output_fits_data_shape = copy.copy(tnaxis[::-1])
    # 
    # Get input fits WCS
    iwcs = WCS(input_fits_header, naxis=naxis)
    idata = input_fits_data
    # 
    # Get template fits WCS
    twcs = WCS(template_fits_header, naxis=naxis)
    tdatashape = tnaxis[::-1] # this will also be the shape of (each slice of) the output data array
    # 
    # Make pixel mgrid
    timestart = timeit.default_timer()
    if naxis == 2:
        # 
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        iy, ix = np.mgrid[0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten()])
        # 
        print2('Generating pixel mgrid with %s pixels'%(tnaxis_str))
        ty, tx = np.mgrid[0:tnaxis[1], 0:tnaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten()])
        # 
    elif naxis == 3:
        # 
        print2('Generating pixel mgrid with %s pixels'%(inaxis_str))
        ichan, iy, ix = np.mgrid[0:inaxis[2], 0:inaxis[1], 0:inaxis[0]]
        ipixcoords = np.column_stack([ix.flatten(), iy.flatten(), ichan.flatten()])
        # 
        print2('Generating pixel mgrid with %s pixels'%(tnaxis_str))
        tchan, ty, tx = np.mgrid[0:tnaxis[2], 0:tnaxis[1], 0:tnaxis[0]]
        tpixcoords = np.column_stack([tx.flatten(), ty.flatten(), tchan.flatten()])
        # 
    else:
        raise NotImplementedError('Error! The cube projection and interpolation have not been implemented for an NAXIS of %d!'%(naxis))
    # 
    timestop = timeit.default_timer()
    print('Used %s seconds'%(timestop-timestart))
    # 
    #raise NotImplementedError() # debug point
    # 
    timestart = timeit.default_timer()
    # 
    # Convert each pixel coordinate to skycoordinate for the template pixel grid which is also the output pixel grid.
    print2('Computing wcs_pix2world for %s pixels'%(tnaxis_str))
    oskycoords = twcs.wcs_pix2world(tpixcoords, 0)
    print2('oskycoords.shape = %s'%(list(oskycoords.shape)))
    #tra, tdec, tfreq = oskycoords.T
    # 
    # Convert each pixel skycoordinate to the coordinate in the input mask cube, so that we can do interpolation. 
    print2('Computing wcs_world2pix for %s pixels'%(tnaxis_str))
    opixcoords = iwcs.wcs_world2pix(oskycoords, 0)
    print2('opixcoords.shape = %s'%(list(opixcoords.shape)))
    # 
    timestop = timeit.default_timer()
    print('Used %s seconds'%(timestop-timestart))
    # 
    # Loop each input data slice
    odata = []
    odataarray = None
    for i in range(max(1,idataslice)):
        # 
        # Do interpolation with scipy.interpolate.griddata
        timestart = timeit.default_timer()
        print2('Interpolating griddata...')
        if idataslice > 0:
            idataarray = idata[i].flatten()
        else:
            idataarray = idata.flatten()
        idatamask = ~np.isnan(idataarray)
        odataarray = griddata(ipixcoords[idatamask], \
                              idataarray[idatamask], \
                              opixcoords, \
                              method = 'nearest', \
                              fill_value = 0 )
        timestop = timeit.default_timer()
        print('Used %s seconds'%(timestop-timestart))
        # 
        # The interpolation is done with serialized arrays, so we reshape the output interpolated aray to 3D cube 
        odataarray = odataarray.reshape(tdata.shape).astype(idata.dtype)
        if idataslice > 0:
            odata.append(odataarray)
        else:
            odata = odataarray
    #odatashape = list(odataarray.shape)[::-1]
    #odatashape.append(input_fits_data_shape[::-1][naxis:])
    #odatashape = odatashape[::-1]
    output_fits_data_shape = output_fits_data_shape[::-1]
    output_fits_data_shape[0:naxis] = list(odata.shape)[::-1][0:naxis]
    output_fits_data_shape = output_fits_data_shape[::-1]
    print('input_fits_data_shape = %s'%(input_fits_data_shape))
    print('output_fits_data_shape = %s'%(output_fits_data_shape))
    print('odata.shape = %s'%(list(odata.shape)))
    odata.shape = output_fits_data_shape
    # 
    # Prepare output fits header
    output_fits_header = twcs.to_header()
    if idataslice > 0:
        output_fits_header['NAXIS'] = len(input_fits_data_shape)
        for i in range(naxis, len(input_fits_data_shape)):
            for keybase in ['NAXIS', 'CTYPE', 'CUNIT', 'CRPIX', 'CRVAL', 'CDELT']:
                key = keybase+'%d'%(i+1)
                if key in input_fits_header:
                    output_fits_header[key] = input_fits_header[key]
    elif idataslice < 0:
        output_fits_header['NAXIS'] = len(output_fits_data_shape)
        for i in range(naxis, len(output_fits_data_shape)):
            for keybase in ['NAXIS', 'CTYPE', 'CUNIT', 'CRPIX', 'CRVAL', 'CDELT']:
                key = keybase+'%d'%(i+1)
                if key in template_fits_header:
                    output_fits_header[key] = template_fits_header[key]
    # 
    # Output the interpolated mask cube as a fits file
    print2('Writing fits file...')
    output_hdu = fits.PrimaryHDU(data = odata, header = output_fits_header)
    if not re.match(r'.*\.fits$', output_fits_cube, re.IGNORECASE):
        output_fits_cube += '.fits'
    output_hdu.writeto(output_fits_cube, overwrite = overwrite)
    print2('Output to "%s"!'%(output_fits_cube))

# 
# def test_project_fits_cube
# 
def test_project_fits_cube():
    project_fits_cube(input_fits_cube = 'ngc4321_co21_clean_mask.fits', 
                      template_fits_cube = 'run_tclean_2015.1.00956.S._.12m._.1/ngc4321_co21_dirty.image.pbcor.fits', 
                      output_fits_cube = 'test_project_fits_cube.fits', 
                      overwrite = True)

# 
# test here!
# 
#test_project_fits_cube()
#raise NotImplementedError()




# 
# def process_clean_mask
# 
def process_clean_mask(input_mask_cube, template_image_cube, output_mask_cube):
    # 
    # We will read the input_mask_cube, register the cube to the template_image_cube WCS, 
    # and output the mask cube. 
    # 
    # No CASA module required
    # 
    # TODO: The user can supply some parameters to add some mask conditions using the template_image_cube
    # 
    import warnings
    from astropy.utils.exceptions import AstropyWarning
    warnings.simplefilter('ignore', category=AstropyWarning)
    from astropy.table import Table
    from astropy.io import fits
    from astropy import units as u
    from astropy import wcs
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_scales
    from astropy.coordinates import SkyCoord, FK5
    from scipy.interpolate import griddata
    # 
    # Read template_image_cube
    template_image_cube_file = template_image_cube
    for tempfile in [template_image_cube+'.image.pbcor.fits', template_image_cube+'.image.fits', template_image_cube+'.fits']:
        if os.path.isfile(tempfile):
            template_image_cube_file = tempfile
            break
    template_hdulist = fits.open(template_image_cube_file)
    template_hdu = template_hdulist[0]
    # 
    # Get WCS
    tnstokes, tnchan, tny, tnx = template_hdu.data.shape
    twcs = WCS(template_hdu.header, naxis=3)
    tdata = template_hdu.data
    # 
    # Read input_mask_cube
    input_hdulist = fits.open(input_mask_cube)
    input_hdu = input_hdulist[0]
    if input_hdu.header['CTYPE3'].strip() == 'VRAD':
        ctype3 = input_hdu.header['CTYPE3']
        cunit3 = input_hdu.header['CUNIT3'].strip().replace(' ','').lower()
        crpix3 = input_hdu.header['CRPIX3']
        crval3 = input_hdu.header['CRVAL3']
        cdelt3 = input_hdu.header['CDELT3']
        if cunit3 == 'km/s' or cunit3 == 'kms-1':
            c30 = 2.99792458e5
        else:
            c30 = 2.99792458e8
        input_hdu.header['CRVAL3'] = (1.0-(crval3/c30))*input_hdu.header['RESTFRQ'] # Hz, (nu0-nu)/nu0 = (v/c), so nu = (1-(v/c))*nu0
        input_hdu.header['CDELT3'] = (-(cdelt3/c30))*input_hdu.header['RESTFRQ'] # Hz, reversed order
        input_hdu.header['CTYPE3'] = 'FREQ'
        input_hdu.header['CUNIT3'] = 'Hz'
    inchan, iny, inx = input_hdu.data.shape
    iwcs = WCS(input_hdu.header, naxis=3)
    idata = input_hdu.data
    # 
    # Prepare pixel mgrid
    print2('generating pixel mgrid with %dx%dx%d pixels'%(inx, iny, inchan))
    igchan, igy, igx = np.mgrid[0:inchan, 0:iny, 0:inx]
    # 
    print2('generating pixel mgrid with %dx%dx%d pixels'%(tnx, tny, tnchan))
    tgchan, tgy, tgx = np.mgrid[0:tnchan, 0:tny, 0:tnx]
    # 
    #raise NotImplementedError() # debug point
    # 
    # Convert each pixel coordinate to skycoordinate for the template pixel grid which is also the output pixel grid.
    print2('computing wcs_pix2world for %dx%dx%d pixels'%(tnx, tny, tnchan))
    oskycoords = twcs.wcs_pix2world(np.column_stack([tgx.flatten(), tgy.flatten(), tgchan.flatten()]), 0)
    print2('oskycoords.shape = %s'%(list(oskycoords.shape)))
    #tra, tdec, tfreq = oskycoords.T
    # 
    # Convert each pixel skycoordinate to the coordinate in the input mask cube, so that we can do interpolation. 
    print2('computing wcs_world2pix for %dx%dx%d pixels'%(tnx, tny, tnchan))
    opixcoords = iwcs.wcs_world2pix(oskycoords, 0)
    print2('opixcoords.shape = %s'%(list(opixcoords.shape)))
    ogx, ogy, ogchan = opixcoords.T
    # 
    # Do interpolation with scipy.interpolate.griddata
    #imask = ~np.isnan(idata) <TODO> Is NaN a problem?
    print2('interpolating griddata...')
    odata = griddata(np.column_stack([igchan.flatten(), igy.flatten(), igx.flatten()]), idata.flatten(), \
                     np.column_stack([ogchan.flatten(), ogy.flatten(), ogx.flatten()]), \
                     method='nearest', fill_value=0)
    # 
    # The interpolation is done with serialized arrays, so we reshape the output interpolated aray to 3D cube 
    odata = odata.reshape(tdata.shape).astype(int)
    # 
    # <TODO> To implement some mask operations according to the input template_image_cube.
    #        for example, do an AND operation to combine current mask and all pixels with S/N>4 in the template image cube. 
    # <TODO> 
    # 
    # Output the interpolated mask cube as a fits file
    print2('writing fits file...')
    output_hdu = fits.PrimaryHDU(data = odata, header = twcs.to_header())
    if not re.match(r'.*\.fits$', output_mask_cube, re.IGNORECASE):
        output_mask_cube += '.fits'
    output_hdu.writeto(output_mask_cube, overwrite = True)
    print2('Output to "%s"!'%(output_mask_cube))















def dzliu_clean(dataset_ms, 
                output_image = '', 
                galaxy_name = '', 
                galaxy_redshift = None, 
                make_line_cube = True, 
                make_continuum = True, 
                phasecenter = '', 
                beamsize = '', 
                line_name = None, 
                line_velocity = None, 
                line_velocity_width = None, 
                line_velocity_resolution = None, 
                continuum_clean_threshold = 3.5, 
                line_clean_threshold = 3.5, 
                max_imsize = None, 
                skip_split = False, 
                overwrite = False):
    # 
    set_casalog_origin('dzliu_clean')
    
    # 
    # Check input paraameters
    if dataset_ms == '':
        raise ValueError('Error! The input \'dataset_ms\' is empty!')
    dataset_name = re.sub(r'\.ms$', r'', os.path.basename(dataset_ms))
    
    # 
    # Prepare output dir and name
    if output_image == '':
        output_dir = 'run_tclean_%s'%(dataset_name)
    elif output_image.find(os.sep) >= 0:
        output_dir = os.path.dirname(output_image)
    else:
        output_dir = '.'
    
    if output_dir != '.':
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
    
    if galaxy_name != '':
        galaxy_name_cleaned = re.sub(r'[^a-zA-Z0-9]', r'', galaxy_name).lower()
    else:
        galaxy_name_cleaned = dataset_name
    
    if output_image != '':
        output_name = output_dir+os.sep+re.sub(r'(\.image\.fits|\.pb\.fits|\.fits|\.image)', r'', os.path.basename(output_image))
    else:
        output_name = output_dir+os.sep+'%s'%(galaxy_name_cleaned)
    
    # 
    # Make lists
    if line_name is not None:
        if np.isscalar(line_name):
            line_name = [line_name]
    if line_velocity is not None:
        if np.isscalar(line_velocity):
            line_velocity = [line_velocity]
    if line_velocity_width is not None:
        if np.isscalar(line_velocity_width):
            line_velocity_width = [line_velocity_width]
    if line_velocity_resolution is not None:
        if np.isscalar(line_velocity_resolution):
            line_velocity_resolution = [line_velocity_resolution]
        
    # 
    # Check line info consistency
    num_lines = 0
    if make_line_cube:
        if line_name is not None:
            if line_velocity_resolution is None:
                line_velocity_resolution = [-1]*len(line_velocity) # if user has not input velocity resolution, set to -1 so as to keep original channel width
            if len(line_name) != len(line_velocity) or len(line_name) != len(line_velocity_width):
                raise ValueError('Error! Please input both \'line_name\' and \'line_velocity\' (optical definition, v=cz, km/s) and \'line_velocity_width\' (km/s)!')
            num_lines = len(line_name)
        #else:
        #    raise ValueError('Error! make_line_cube is True but no input \'line_name\', \'line_velocity\' (optical definition, v=cz, km/s), \'line_velocity_width\' (km/s) and \'line_velocity_resolution\' (km/s)!')
        # 
        #--> if user has input make_continuum then not necessary to input line info
    
    # 
    # 20210315 fix zero rest frequency
    fix_zero_rest_frequency(dataset_ms)
    
    # 
    # Make line cube
    for i in range(num_lines):
        # 
        # Set output name for each line
        line_ms = '%s_%s.ms'%(output_name, line_name[i])
        line_dirty_cube = '%s_%s_dirty'%(output_name, line_name[i])
        line_clean_cube = '%s_%s_clean'%(output_name, line_name[i])
        # 
        # Check existing files
        if overwrite:
            for check_dir in [line_ms, line_dirty_cube, line_clean_cube]:
                for check_type in ['', '.image', '.pb', '.mask', '.residual', '.image.pbcor', '.model', '.psf', '.sumwt', '.weight']:
                    if os.path.isdir(check_dir+check_type):
                        shutil.rmtree(check_dir+check_type)
                    if os.path.isfile(check_dir+check_type+'.fits'):
                        os.remove(check_dir+check_type+'.fits')
        # 
        # Check if skipping split
        if skip_split:
            if os.path.isdir(line_ms):
                if os.path.isdir(line_ms+'.backup'):
                    shutil.rmtree(line_ms+'.backup')
                shutil.move(line_ms, line_ms+'.backup')
            shutil.copytree(dataset_ms, line_ms)
        else:
            # 
            # Split line data and make channel averaging
            split_line_visibilities(dataset_ms, line_ms, galaxy_name, line_name[i], line_velocity[i], line_velocity_width[i], line_velocity_resolution[i])
        # 
        # Make dirty image
        make_dirty_image(line_ms, line_dirty_cube, phasecenter = phasecenter, beamsize = beamsize, max_imsize = max_imsize)
        #
        # Compute rms in the dirty image
        result_imstat_dict = imstat(line_dirty_cube+'.image')
        # 
        # Check error
        if len(result_imstat_dict['rms']) == 0:
            print('Error! Failed to determine rms from "%s"! The image data are problematic! We will skip it!'%(line_dirty_cube+'.image'))
            continue
        else:
            # 
            # Set threshold
            threshold = result_imstat_dict['rms'][0] * line_clean_threshold #<TODO># 3-sigma
            # 
            # Make clean image
            make_clean_image(line_ms, line_clean_cube, phasecenter = phasecenter, threshold = threshold, pblimit = 0.05, pbmask = 0.05, beamsize = beamsize, max_imsize = max_imsize)
    
    # 
    # Make continuum image
    if make_continuum:
        # 
        # Set output name for line-free continuum
        continuum_ms = '%s_%s.ms'%(output_name, 'cont')
        continuum_dirty_cube = '%s_%s_dirty'%(output_name, 'cont')
        continuum_clean_cube = '%s_%s_clean'%(output_name, 'cont')
        # 
        # Check existing files
        if overwrite:
            for check_dir in [continuum_ms, continuum_dirty_cube, continuum_clean_cube]:
                for check_type in ['', '.image', '.pb', '.mask', '.residual', '.image.pbcor', '.model', '.psf', '.sumwt', '.weight']:
                    if os.path.isdir(check_dir+check_type):
                        shutil.rmtree(check_dir+check_type)
                    if os.path.isfile(check_dir+check_type+'.fits'):
                        os.remove(check_dir+check_type+'.fits')
        # 
        # Check if skipping split
        if skip_split:
            if os.path.isdir(continuum_ms):
                if os.path.isdir(continuum_ms+'.backup'):
                    shutil.rmtree(continuum_ms+'.backup')
                shutil.move(continuum_ms, continuum_ms+'.backup')
            shutil.copytree(dataset_ms, continuum_ms)
        else:
            # 
            # we need to find out line-free channels
            split_continuum_visibilities(dataset_ms, continuum_ms, galaxy_name, galaxy_redshift = galaxy_redshift, line_name = line_name, line_velocity = line_velocity, line_velocity_width = line_velocity_width)
        # 
        # Make continuum
        make_dirty_image_of_continuum(continuum_ms, continuum_dirty_cube, phasecenter = phasecenter, beamsize = beamsize, max_imsize = max_imsize)
        #
        # Compute rms in the dirty image
        result_imstat_dict = imstat(continuum_dirty_cube+'.image')
        # 
        # Check error
        if len(result_imstat_dict['rms']) == 0:
            print('Error! Failed to determine rms from "%s"! The image data are problematic! We will skip it!'%(continuum_dirty_cube+'.image'))
        else:
            # 
            # Set threshold
            threshold = result_imstat_dict['rms'][0] * continuum_clean_threshold #<TODO># 3.5-sigma
            # 
            # Make clean image of the rough continuum 
            make_clean_image_of_continuum(continuum_ms, continuum_clean_cube, phasecenter = phasecenter, threshold = threshold, pblimit = 0.05, pbmask = 0.05, beamsize = beamsize, max_imsize = max_imsize)



def test_dzliu_clean():
    #cd /Users/dzliu/Work/DeepFields/Works_cooperated/2019_Emanuele_Daddi_RO1001/20191018_data/cube
    #sys.path.append('/Users/dzliu/Cloud/Github/Crab.Toolkit.CASA/lib/python')
    #import dzliu_clean
    #reload(dzliu_clean)
    #dzliu_clean.dzliu_clean('concat_1_ms.ms', 'run_tclean_concat_1_ms_test_1/concat_1_ms')
    #dzliu_clean.dzliu_clean('concat_1_ms.ms', 'run_tclean_concat_1_ms_test_2/concat_1_ms', galaxy_redshift = 0.653566, overwrite = True)
    #
    pass








############
#   main   #
############

dzliu_main_func_name = 'dzliu_clean' # make sure this is the right main function in this script file

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




