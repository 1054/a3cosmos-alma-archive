#!/usr/bin/env python
# 

from __future__ import print_function
import os, sys
from glob import glob
import tarfile
from bs4 import BeautifulSoup


# Print Usage
if len(sys.argv) <= 1:
    print('Usage: %s %s'%(os.path.basename(__file__), '/path/to/qa/weblog.tgz'), file=sys.stderr)
    sys.exit()

## Read User Input
#qa_dir = sys.argv[1]
#
## Find weblog tgz
#weblog_tgz = glob(qa_dir+os.sep+'*.weblog.tgz')
#
## Check weblog tgz
#if len(weblog_tgz) == 0:
#    print('Error! Could not find *.weblog.tgz under "%s"!'%(qa_dir))
#    sys.exit()

# Read User Input
weblog_tgz = sys.argv[1]

# Check weblog tgz
if not os.path.isfile(weblog_tgz):
    print('Error! Could not find "%s"!'%(weblog_tgz), file=sys.stderr)
    sys.exit()

# Open weblog tgz
weblog_obj = tarfile.open(weblog_tgz)


# Prepare to get casa_version
casa_version = ''

for weblog_item in weblog_obj.getmembers():
    if os.path.basename(weblog_item.name) == 'index.html':
        #print(weblog_item, file=sys.stderr)
        weblog_index_html = weblog_obj.extractfile(weblog_item)
        #print(weblog_index_html, file=sys.stderr)
        weblog_index_html_content = weblog_index_html.read()
        
        soup = BeautifulSoup(weblog_index_html_content, 'html.parser')
        
        #for soup_th in [t.parent for t in soup.findAll(text='CASA Version') if t.parent.name=='th']
        for soup_th in soup.findAll('th', text='CASA Version'):
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
        
        if casa_version != '':
            break

print('CASA version %s'%(casa_version))


