# This script calculates the imcell for tclean. 
# 
# This script needs to be executed inside CASA via the execfile() command!
# e.g., execfile('dzliu_calc_imcell.py')
# 

import os
import numpy as np

# 
# set ms data
# 
vis = 'split_science_target.ms'
print('vis = %r'%(vis))


# 
# get reference frequency
# 
tb.open(vis+os.sep+'SPECTRAL_WINDOW')
ref_freq_Hz = tb.getcol('REF_FREQUENCY').max()
tb.close()
print('ref_freq_Hz = %e [Hz]'%(ref_freq_Hz))

# 
# get uvdist
# 
tb.open(vis)
uvw = tb.getcol('UVW') # shape (3, nrows), each row is a (u,v,w) array
##print('tb.query(\'FIELD_ID in [%s] AND DATA_DESC_ID in [%s] AND STATE_ID in [%s]\', \'UVW\')'%(','.join(matched_field_indices.astype(str)), ','.join(valid_data_desc_indicies.astype(str)), ','.join(valid_state_indices.astype(str))))
##result = tb.query('FIELD_ID in [%s] AND DATA_DESC_ID in [%s] AND STATE_ID in [%s]'%(','.join(matched_field_indices.astype(str)), ','.join(valid_data_desc_indicies.astype(str)), ','.join(valid_state_indices.astype(str))), 'UVW')
#print('tb.query(\'FIELD_ID in [%s] AND STATE_ID in [%s]\', \'UVW\')'%(','.join(matched_field_indices.astype(str)), ','.join(valid_state_indices.astype(str))))
#result = tb.query('FIELD_ID in [%s] AND STATE_ID in [%s]'%(','.join(matched_field_indices.astype(str)), ','.join(valid_state_indices.astype(str))), 'UVW')
#uvw = result.getcol('UVW')
tb.close()
# 
uvdist = np.sqrt(np.sum(np.square(uvw[0:2, :]), axis=0))
maxuvdist = np.max(uvdist)
print('maxuvdist = %s [m]'%(maxuvdist))
L80uvdist = np.percentile(uvdist, 80) # np.max(uvdist) # now I am using 90-th percentile of baselies, same as used by 'analysisUtils.py' pickCellSize() getBaselineStats(..., percentile=...)
print('L80uvdist = %s [m] (80-th percentile)'%(L80uvdist))
# 
synbeam = 2.99792458e8 / ref_freq_Hz / maxuvdist / np.pi * 180.0 * 3600.0 # arcsec
synbeam = 0.574 * 2.99792458e8 / ref_freq_Hz / L80uvdist / np.pi * 180.0 * 3600.0 # arcsec # .574lambda/L80, see 'analysisUtils.py' estimateSynthesizedBeamFromASDM()
synbeam_nprec = 2 # keep 2 valid 
synbeam_ndigits = (synbeam_nprec-1) - int(np.floor(np.log10(synbeam))) # keep to these digits (precision) after point, e.g., 0.1523 -> nprec 2 -> round(0.1523*100)/100 = 0.15
synbeam = (np.round(synbeam * 10**(synbeam_ndigits))) / 10**(synbeam_ndigits)
oversampling = 5.0
imcell_arcsec = synbeam / oversampling
imcell = '%sarcsec'%(imcell_arcsec)
print('synbeam = %s [arcsec]'%(synbeam))
print('imcell_arcsec = %s'%(imcell_arcsec))

