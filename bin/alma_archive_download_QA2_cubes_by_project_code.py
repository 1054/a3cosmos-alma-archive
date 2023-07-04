#!/usr/bin/env python
# 

from astroquery.alma import Alma
from astropy.table import Table
from astropy.io import fits
from spectral_cube import SpectralCube, VaryingResolutionSpectralCube
import astropy.units as u
import numpy as np
import os, sys, re, glob, copy, shutil, tarfile
import click


@click.command()
@click.argument('project_code', type=str)
def main(project_code):
    
    alma = Alma()
    alma.archive_url = 'https://almascience.eso.org'
    alma.cache_location = os.path.abspath('cache_dir')

    
    #project_code = '2021.1.01650.S'

    cube_files = glob.glob('{}/s*/g*/m*/external/ari_l/*cube*.fits'.format(project_code)) + glob.glob('{}/s*/g*/m*/product/*cube*.fits'.format(project_code))
    if len(cube_files) == 0:
        query_file = 'query_{}.csv'.format(project_code)
        if os.path.exists(query_file):
            data_table = Table.read(query_file)
        else:
            result = Alma.query(payload=dict(project_code=project_code, public=True))
            uids = np.unique(result['member_ous_uid'])
            data_table = alma.get_data_info(uids)
            # select product tar files
            selected = np.array([re.match(r'^.*_[0-9]+_of_[0-9]+.tar$', t) is not None for t in data_table['access_url']])
            data_table = data_table[selected]
            data_table.write(query_file)
            print('Output to {!r}'.format(query_file))

        # download tar files
        files = [url.split('/')[-1] for url in data_table['access_url']]
        check_okay = np.all([os.path.exists(alma.cache_location+'/'+filename) for filename in files])
        if not check_okay:
            print('Downloading tar files: {}'.format(files))
            alma.download_files(data_table['access_url'], cache=True)

        # extract tar files
        for filename in files:
            with tarfile.open(alma.cache_location+'/'+filename, 'r') as tar:
                for tarinfo in tar:
                    #print(tarinfo.name)
                    tarfilepath = tarinfo.name
                    tarfilename = tarinfo.name.split('/')[-1]
                    if re.match(r'.*cube.I.(pb|pbcor).(fits|fits.gz)', tarfilename):
                        if not os.path.exists(tarfilepath):
                            print('tar.extract({!r})'.format(tarinfo.name))
                            tar.extract(tarinfo)

        #os.system('alma_archive_unpack_tar_files_with_verification.sh cache_dir/*.tar')

        cube_files = glob.glob('{}/s*/g*/m*/external/ari_l/*cube*.fits'.format(project_code)) + glob.glob('{}/s*/g*/m*/product/*cube*.fits'.format(project_code))

    # compress cube channels
    if not os.path.isdir('processed_dir'):
        os.makedirs('processed_dir')
    for cube_file in cube_files:
        cube_filename = os.path.basename(cube_file)
        
        # add QA2 string in the source name part of the filename (right before spw)
        regex_check = r'(.*)(\.spw[0-9]+)(.*)'
        regex_match = re.match(regex_check, cube_filename)
        if regex_match is not None:
            outcube_filename = regex_match.group(1) + '_QA2' + regex_match.group(2) + regex_match.group(3)
        else:
            raise Exception('Data file name {!r} does not have a format of {!r}!'.format(cube_filename, regex_check))
        #if cube_filename.find('_sci') >= 0:
        #    outcube_filename = cube_filename.replace('_sci', '_sci_QA2')
        outcube_file = 'processed_dir/{}.{}'.format(project_code, outcube_filename)
        if not os.path.isfile(outcube_file):
            print('Processing {!r}'.format(cube_file))
            scube = SpectralCube.read(cube_file)
            freq = np.mean(scube.spectral_axis).to(u.Hz).value
            header = scube.header
            freqwidth = header['CDELT3'] # Hz
            velwidth = 3e5*np.abs(freqwidth/freq) # km/s
            rebin = int(np.ceil(25.0/velwidth)) # to about 25.0 km/s
            if rebin > 1:
                naxis3 = int(header['NAXIS3']/rebin)
                nchan = header['NAXIS3']
                ny, nx = header['NAXIS2'], header['NAXIS1']
                outdata = np.nanmean(scube.filled(np.nan).reshape([nchan, ny, nx])[0:rebin*naxis3, :, :].reshape([rebin, naxis3, ny, nx]), axis=0)
                outheader = copy.deepcopy(header)
                outheader['NAXIS'] = 3
                outheader['NAXIS3'] = naxis3
                outheader['CDELT3'] *= float(rebin)
                outheader['CRPIX3'] = (header['CRPIX3'] - 1.0) / float(rebin) + 1.0
            else:
                naxis3 = header['NAXIS3']
                ny, nx = header['NAXIS2'], header['NAXIS1']
                outdata = scube.filled(np.nan).reshape([naxis3, ny, nx])
                outheader = copy.deepcopy(header)
                outheader['NAXIS'] = 3
            if isinstance(outdata, u.Quantity):
                outdata = outdata.value
            if isinstance(scube, VaryingResolutionSpectralCube):
                avgbeam = scube.average_beams()
                outheader['BMAJ'] = avgbeam.major.to(u.deg).value
                outheader['BMIN'] = avgbeam.minor.to(u.deg).value
                outheader['BPA'] = avgbeam.pa.to(u.deg).value
            outhdu = fits.PrimaryHDU(data=outdata, header=outheader)
            outhdu.writeto(outcube_file)
            print('Output to {!r}'.format(outcube_file))



if __name__ == '__main__':
    main()



