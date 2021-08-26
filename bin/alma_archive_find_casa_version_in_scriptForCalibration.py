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
    print('Usage: %s %s'%(os.path.basename(__file__), '/path/to/script/*scriptForCalibration.py'), file=sys.stderr)
    sys.exit()


# Read User Input
script_file = sys.argv[1]


# Check weblog html
if not os.path.isfile(script_file):
    print('Error! Could not find "%s"!'%(script_file), file=sys.stderr)
    sys.exit()


# Prepare to get casa_version
casa_version = ''


with open(script_file, 'r') as fp:
    
    for line in fp:
        if line.find('PLEASE USE THE SAME VERSION OF CASA') >= 0:
            if re.match(r'^.*PLEASE USE THE SAME VERSION OF CASA.*:[ \t]*([0-9.]+)\b.*$', line):
                casa_version = re.sub(r'^.*PLEASE USE THE SAME VERSION OF CASA.*:[ \t]*([0-9.]+)\b.*$', r'\1', line)
                break


if casa_version != '':
    print('CASA version %s'%(casa_version))


