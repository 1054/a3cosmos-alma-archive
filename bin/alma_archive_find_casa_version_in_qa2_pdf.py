#!/usr/bin/env python
# 

from __future__ import print_function
import os, sys, re
from glob import glob
from pypdf import PdfReader


# Print Usage
if len(sys.argv) <= 1:
    print('Usage: %s %s'%(os.path.basename(__file__), '/path/to/qa/*.qa2_report.pdf'), file=sys.stderr)
    sys.exit()

# Read User Input
qa2_pdf = sys.argv[1]

# Check file
if not os.path.isfile(qa2_pdf):
    print('Error! Could not find "%s"!'%(qa2_pdf), file=sys.stderr)
    sys.exit()

# Prepare to get casa_version
casa_version = ''

# Read pdf text
reader = PdfReader(qa2_pdf)
for page in reader.pages:
    text = page.extract_text()
    #print(text)
    matches = re.findall(r'\bCASA version[:]* *([0-9]+[0-9.-]+)\b', text, re.IGNORECASE)
    for match in matches:
        casa_version = re.sub(r'\bCASA version[:]* ([0-9]+[0-9.-]+)\b', r'\1', match, re.IGNORECASE)
        if casa_version != '':
            break
    if casa_version != '':
        break

if casa_version != '':
    print('CASA version %s'%(casa_version))


