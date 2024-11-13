#!/usr/bin/env python
# 
# copied from "alma_archive_find_casa_version_in_qa_weblog.py", for html not in *.tgz.
# 

from __future__ import print_function
import os, sys, re
from glob import glob
#import tarfile
from bs4 import BeautifulSoup


# Print Usage
if len(sys.argv) <= 1:
    print('Usage: %s %s'%(os.path.basename(__file__), '/path/to/qa/member*.html'), file=sys.stderr)
    sys.exit()


# Read User Input
weblog_html = sys.argv[1]


# Check weblog html
if not os.path.isfile(weblog_html):
    print('Error! Could not find "%s"!'%(weblog_html), file=sys.stderr)
    sys.exit()


# Prepare to get casa_version
casa_version = ''


with open(weblog_html, 'r') as weblog_index_html:
    #print(weblog_index_html, file=sys.stderr)
    weblog_index_html_content = weblog_index_html.read()
    #print(weblog_index_html_content)

    soup = BeautifulSoup(weblog_index_html_content, 'html.parser')

    #for soup_th in [t.parent for t in soup.findAll(text='CASA Version') if t.parent.name=='th']
    if casa_version == '':
        #<20240902># for soup_th in soup.findAll('th', text='CASA Version'): # DeprecationWarning: The 'text' argument to find()-type methods is deprecated. Use 'string' instead.
        for soup_th in soup.findAll('th', string='CASA Version'):
            #print(soup_th) # soup_th.name # soup_th.text
            for soup_td in soup_th.find_next_siblings():
                #print(soup_td.text)
                if len(soup_td.text) > 0:
                    if soup_td.text.find('.') > 0:
                        if soup_td.text.find(' ') > 0:
                            casa_version = soup_td.text.split()[0]
                        else:
                            casa_version = soup_td.text
                if casa_version != '':
                    break
            
            if casa_version != '':
                break
    
    # try again to find span that includes 'CASA version:'
    if casa_version == '':
        for soup_span in soup.findAll('span'):
            if soup_span.text.startswith('CASA version:'):
                #print(soup_span.text)
                casa_version = re.sub(r'CASA version: ([0-9.]+).*', r'\1', soup_span.text)
                if casa_version != '':
                    break
    
    # try again to find span that include 'CASA version' and next is 'Report date'
    if casa_version == '':
        for soup_span in soup.findAll('span'):
            if soup_span.text == 'CASA version':
                #print(soup_span.text)
                soup_tr = soup_span.find_parent('tr')
                soup_tr_td = soup_tr.find_all('td')
                soup_tr_td_text = [t.text.strip() for t in soup_tr_td]
                soup_tr_td_index = soup_tr_td_text.index('CASA version')
                #print(soup_tr)
                soup_tr_next = soup_tr.find_next_sibling('tr')
                #print(type(soup_tr_next))
                
                if soup_tr_next is None:
                    # 2022-04-11 fixing reading html if there is nested tables
                    # tr does not have a sibling tr
                    # we need to jump out a level
                    #   table > tr > td > table > tr > td (nonsense stuff)
                    #                           > tr > td (CASA version)
                    #         > tr > td > table > tr > td (nonsense stuff)
                    #                           > tr > td (actual number we want)
                    soup_parent_table = soup_tr.find_parent('table')
                    soup_parent_table_parent_td = soup_parent_table.find_parent('td')
                    soup_parent_table_parent_td_parent_tr = soup_parent_table_parent_td.find_parent('tr')
                    soup_this_tr = soup_parent_table_parent_td_parent_tr
                    soup_next_tr = soup_parent_table_parent_td_parent_tr.find_next_sibling('tr')
                    this_index = soup_this_tr.find_all('td').index(soup_parent_table_parent_td)
                    #print('this_index', this_index)
                    soup_this_tr_td = soup_this_tr.find_all('td')[this_index]
                    soup_next_tr_td = soup_next_tr.find_all('td')[this_index]
                    
                    this_index = soup_this_tr_td.find_all('table').index(soup_parent_table)
                    #print('this_index', this_index)
                    soup_this_tr_td_table = soup_this_tr_td.find_all('table')[this_index]
                    soup_next_tr_td_table = soup_next_tr_td.find_all('table')[this_index]
                    
                    this_index = soup_this_tr_td_table.find_all('tr').index(soup_tr)
                    #print('this_index', this_index)
                    soup_this_tr_td_table_tr = soup_this_tr_td_table.find_all('tr')[this_index]
                    soup_next_tr_td_table_tr = soup_next_tr_td_table.find_all('tr')[this_index]
                    
                    soup_tr_next = soup_next_tr_td_table_tr
                
                soup_tr_next_td = soup_tr_next.find_all('td')
                soup_tr_next_td_text = [t.text.strip() for t in soup_tr_next_td]
                found_text = soup_tr_next_td_text[soup_tr_td_index]
                #print(soup_tr_next)
                if re.match(r'^[0-9.-]+$', found_text):
                    casa_version = found_text
                if casa_version != '':
                    break
                    
                    
                    

if casa_version != '':
    print('CASA version %s'%(casa_version))


