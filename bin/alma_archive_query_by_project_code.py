#!/usr/bin/env python
# 
from __future__ import print_function
import os, sys, re, copy, shutil, time, json, pkg_resources
pkg_resources.require('astroquery')
pkg_resources.require('keyrings.alt')
if sys.version_info[0] >= 3:
    unicode = str
import numpy as np
import astroquery
import requests
from astroquery.alma.core import Alma
from astropy.table import Table, Column
from astropy.time import Time
from datetime import datetime
from operator import itemgetter, attrgetter


# 
# read input argument, which should be Member_ous_id
# 
if len(sys.argv) <= 1:
    print('Usage: ')
    print('    alma_archive_query_by_project_code.py "2013.1.00034.S" [--user yourusername]')
    print('Notes:')
    print('    The output will be a file named "alma_archive_query_by_project_code_2013.1.00034.S.txt"')
    print('    If the data is proprietary, please input --user XXX"')
    print('    If we want to use nrao server, please input --server nrao"')
    print('    If we want to overwrite existing output file, please input --overwrite"')
    sys.exit()

project_codes = []
ALMA_user_name = ''
ALMA_server_name = ''
overwrite = False
output_full_table = True
i = 1
while i < len(sys.argv):
    argstr = sys.argv[i].lower()
    if argstr.startswith('--'):
        argstr = re.sub(r'^[-]+', r'-', argstr)
    if argstr == '-user': 
        i = i+1
        if i < len(sys.argv):
            ALMA_user_name = sys.argv[i]
    if argstr == '-server': 
        i = i+1
        if i < len(sys.argv):
            ALMA_server_name = sys.argv[i]
    elif argstr == '-overwrite': 
        overwrite = True
    #elif argstr == '-full': 
    #    output_full_table = True
    else:
        project_codes.append(sys.argv[i])
    i = i+1
if len(project_codes) == 0:
    print('Error! No project code given!')
    sys.exit()


# 
# deal with sys.path
# 
#print(sys.path)
#sys.path.insert(0,os.path.dirname(os.path.abspath(sys.argv[0]))+'/Python/2.7/site-packages')
#print(sys.path)
#sys.exit()



# 
# loop inputs
# 
for project_code in project_codes:
    
    output_name = 'alma_archive_query_by_project_code_%s' % (project_code)
    
    if (not os.path.isfile(output_name+'.txt')) or overwrite:
        
        # 
        # login
        # 
        Has_login = False
        Query_public = True
        if ALMA_user_name != '' and Has_login == False:
            Alma.login(ALMA_user_name, store_password=True)
            Query_public = False
            Has_login = True
        
        # 
        # set server
        # 
        if ALMA_server_name != '':
            if ALMA_server_name.upper() == 'NRAO':
                Alma.archive_url = "https://almascience.nrao.edu/"
            elif ALMA_server_name.upper() == 'ESO':
                Alma.archive_url = "https://almascience.eso.org/"
            elif ALMA_server_name.upper() == 'EA':
                Alma.archive_url = "https://almascience.nao.ac.jp/"
            else:
                raise Exception('Error! The input ALMA server must be either NRAO, ESO or EA!')
        
        # 
        # query
        # 
        print('Querying with project_code %r'%(project_code))
        query_result = Alma.query(payload = {'project_code':project_code}, public = Query_public)
        query_datetime = datetime.today().strftime('%Y-%m-%d %H:%M:%S %Z')

        
        #print("query_result.colnames:")
        #print(query_result.colnames)
        #-- new since the end of 2020: 
        #   ['access_url', 'access_format', 'proposal_id', 'data_rights', 'gal_longitude', 'gal_latitude', 
        #    'obs_publisher_did', 'obs_collection', 'facility_name', 'instrument_name', 'obs_id', 
        #    'dataproduct_type', 'calib_level', 'target_name', 's_ra', 's_dec', 's_fov', 's_region', 
        #    's_resolution', 't_min', 't_max', 't_exptime', 't_resolution', 'em_min', 'em_max', 'em_res_power', 
        #    'pol_states', 'o_ucd', 'band_list', 'em_resolution', 'authors', 'pub_abstract', 'publication_year', 
        #    'proposal_abstract', 'schedblock_name', 'proposal_authors', 'sensitivity_10kms', 'cont_sensitivity_bandwidth', 
        #    'pwv', 'group_ous_uid', 'member_ous_uid', 'asdm_uid', 'obs_title', 'type', 'scan_intent', 'science_observation', 
        #    'spatial_scale_max', 'bandwidth', 'antenna_arrays', 'is_mosaic', 'obs_release_date', 'spatial_resolution', 
        #    'frequency_support', 'frequency', 'velocity_resolution', 'obs_creator_name', 'pub_title', 'first_author', 
        #    'qa2_passed', 'bib_reference', 'science_keyword', 'scientific_category', 'lastModified']
        
        #query_result_backup = query_result
        #query_result = sorted(query_result_backup, key=itemgetter('Project code'))
        #query_result = query_result.group_by(['Project code', 'Member ous id']) # http://docs.astropy.org/en/stable/table/operations.html#table-operations
        #print(type(query_result))
        #print(query_result)
        #print(query_result.groups.keys)
        #print(query_result[['proposal_id','target_name','band_list','t_min','t_max','t_exptime', 't_resolution']])
        if len(query_result) == 0:
            print('\nError! No result found for the input project_code %s!\n'% (project_code) )
            continue
            #sys.exit()
        
        
        #print(query_result) 
        #<debug><20170926> directly print it can get error like "UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3 in position"
        #<debug><20210122> check all columns
        for colname in query_result.colnames:
            #if colname == 'Proposal authors' or \
            #   colname == 'proposal_authors' or colname == 'proposal_abstract' or \
            #   colname == 'authors' or colname == 'pub_abstract' or colname == 'pub_title':
            #print('type(query_result[colname][0])', type(query_result[colname][0]))
            #print('isinstance(query_result[colname][0], bytes)', isinstance(query_result[colname][0], bytes))
            #print('isinstance(query_result[colname][0], str)', isinstance(query_result[colname][0], str))
            #print('isinstance(query_result[colname][0], unicode)', isinstance(query_result[colname][0], unicode))
            if isinstance(query_result[colname][0], unicode):
                query_result[colname]._sharedmask = False
                for rownumb in range(len(query_result[colname])):
                    query_result[colname][rownumb] = query_result[colname][rownumb].encode('ascii','xmlcharrefreplace')
            elif isinstance(query_result[colname][0], bytes):
                query_result[colname]._sharedmask = False
                for rownumb in range(len(query_result[colname])):
                    query_result[colname][rownumb] = query_result[colname][rownumb].decode('utf-8').encode('ascii','xmlcharrefreplace')
            #if isinstance(query_result[colname][0], unicode):
            #    query_result[colname]._sharedmask = False
            #    for rownumb in range(len(query_result[colname])):
            #        #print('-------------------------------')
            #        #print(query_result[colname][rownumb])
            #        #print(query_result[colname][rownumb].decode('utf-8'))
            #        #try:
            #        #    query_result[colname][rownumb] = query_result[colname][rownumb].decode('utf-8').encode('ascii','xmlcharrefreplace')
            #        #except:
            #        #    pass
        
        
        # debug print
        #for key in query_result.colnames:
        #    print('%s: %s'%(key, query_result[key][0]))
        
        # fix colnames
        # 'Project code','Member ous id','Source name','Observation date','Integration','Band','Array','Mosaic'
        if 'Project code' in query_result.colnames and 'Observation date' in query_result.colnames and \
           'Member ous id' in query_result.colnames and 'Source name' in query_result.colnames:
           pass
        elif 'proposal_id' in query_result.colnames and 'obs_id' in query_result.colnames:
            query_result['Project code'] = query_result['proposal_id']
            query_result['Member ous id'] = query_result['member_ous_uid']
            query_result['Source name'] = query_result['target_name']
            query_result['Observation date'] = Time(query_result['t_min'], format='mjd').to_value(format='isot') # MJD to ISO
            query_result['Integration'] = query_result['t_exptime'] # seconds
            query_result['Band'] = query_result['band_list']
            query_result['Array'] = ['7m' if t.split(' ')[0].split(':')[1][0:2] in ['CM'] else '12m' for t in query_result['antenna_arrays']] # 12m DA DV, 7m CM
            query_result['Mosaic'] = ['True' if (t == 'T' or t == True) else 'False' for t in query_result['is_mosaic']]
        else:
            print('Error! query_result columns are not recognized! The souce code needs to be updated!')
            print('query_result.colnames: ')
            print(query_result.colnames)
            raise Exception('Error! query_result columns are not recognized! The souce code needs to be updated!')
        
        # sort
        try:
            query_result.sort(['Observation date', 'Member ous id', 'Source name'])
        except:
            pass
        
        # output the full table
        if output_full_table:
            #pass
            # fix ValueError: Illegal format `object`.
            # see https://github.com/astropy/astropy/issues/7480
            output_table = query_result
            output_table.meta['Query datetime'] = query_datetime
            for col in output_table.itercols():
                if col.dtype.kind == 'O':
                    output_table[col.name] = Column(col.tolist(), col.name)
            #output_table = Table([Column(col.tolist(),col.name) if col.dtype.kind == 'O' else col for col in query_result.itercols()])
            if os.path.isfile(output_name+'.fits'):
                print('Found existing "%s", backing up as "%s".'%(output_name+'.fits', output_name+'.fits.backup'))
                shutil.move(output_name+'.fits', output_name+'.fits.backup')
            output_table.write(output_name+'.fits', format='fits', overwrite=overwrite)
            print('Output to "%s"!' % (output_name+'.fits'))
            #try:
            #    output_table.write(output_name+'.fits', format='fits', overwrite=overwrite)
            #    print('Output to "%s"!' % (output_name+'.fits'))
            #except:
            #    print('Error! Failed to save the full table to "%s"!'%(output_name+'.fits'))
            #    pass
            
            # also output csv
            if os.path.isfile(output_name+'.csv'):
                print('Found existing "%s", backing up as "%s".'%(output_name+'.csv', output_name+'.csv.backup'))
                shutil.move(output_name+'.csv', output_name+'.csv.backup')
            output_table.write(output_name+'.csv', format='csv', overwrite=overwrite)
            print('Output to "%s"!' % (output_name+'.csv'))
            #try:
            #    output_table.write(output_name+'.csv', format='fits', overwrite=overwrite)
            #    print('Output to "%s"!' % (output_name+'.csv'))
            #except:
            #    print('Error! Failed to save the full table to "%s"!'%(output_name+'.csv'))
            #    pass
        
        
        # fix white space in source name
        for i in range(len(query_result['Source name'])):
            if query_result['Source name'][i].find(' ') >= 0:
                query_result['Source name'][i] = re.sub(r'[^a-zA-Z0-9_+-]', r'_', query_result['Source name'][i])
        
        
        # output selected columns
        output_table = query_result[['Project code','Member ous id','Source name','Observation date','Integration','Band','Array','Mosaic']]
        output_table['Observation date'] = [t.replace(' ','T') for t in output_table['Observation date']]
        output_table['Mosaic'] = [re.sub(r'^$',r'False',t) for t in output_table['Mosaic']]
        output_table['Band'] = [re.sub(r' ',r'+',t) for t in output_table['Band']]
        for colname in output_table.colnames:
            output_table.rename_column(colname, colname.replace(' ','_'))
        output_table.meta = None
        output_table.write(output_name+'.txt', format='ascii.fixed_width', delimiter=' ', bookend=True, overwrite=overwrite)
        with open(output_name+'.txt', 'r+') as fp:
            fp.seek(0)
            fp.write('#')
        print('Output to "%s"!' % (output_name+'.txt'))
        
        #with open(output_name+'.meta.txt', 'w') as fp:
        #    json.dump(output_table.meta, fp, sort_keys=True, indent=4)
        #print('Output to "%s"!' % (output_name+'.meta.txt'))
        
        with open(output_name+'.readme.txt', 'w') as fp:
            fp.write('Queried on %s with the script "%s".'%(query_datetime, os.path.abspath(__file__)))
        print('Output to "%s"!' % (output_name+'.readme.txt'))
    
    else:
        
        print('Using existing file %s'%(output_name+'.txt'))
    
    table = Table.read(output_name+'.txt', format='ascii.commented_header')
    print(table)











