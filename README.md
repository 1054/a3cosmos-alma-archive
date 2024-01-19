# a3cosmos-alma-archive

a3cosmos alma archive processing tools to easily reduce ALMA interferometric data and make images / cubes.


## Why this tool is needed

Sometimes we want to reduce a large amount of ALMA archival data. This tool will make the process efficient. 


## How to use this tool

We first need to setup the CASA software, then we will reduce the ALMA data using program IDs in several 'levels'. The final products will be 'uvfits' files and 'fits' images/cubes. 


### Download-and-extract or clone this repository

Let's clone this repository to your local path:

```
mkdir ~/Cloud/Github/
cd ~/Cloud/Github/
git clone https://github.com/1054/a3cosmos-alma-archive.git
```

 (where `~` is a system symbol referring to your home path. You can choose a custom path, but remember to apply your custom path in later commands.)


### Setup the CASA software

Reducing the raw ALMA data from an ALMA program will need a specific CASA version matching the observation data. Therefore we need all CASA versions to be stored in your computer. Let's first download the CASA packages from [https://casa.nrao.edu/casa_obtaining.shtml](https://casa.nrao.edu/casa_obtaining.shtml) to your local path `~/Software/CASA/Portable`, then extract the packages so that we have a list of CASA versions: 

```
~/Software/CASA/Portable/casapy-41.0.24668-001-64b-2
~/Software/CASA/Portable/casapy-42.1.29047-001-1-64b
~/Software/CASA/Portable/casapy-42.2.30986-pipe-1-64b
~/Software/CASA/Portable/casa-release-4.3.1-el6
~/Software/CASA/Portable/casa-release-4.3.1-pipe-el6
~/Software/CASA/Portable/casa-release-4.4.0-el6
~/Software/CASA/Portable/casa-release-4.5.0-el6
~/Software/CASA/Portable/casa-release-4.5.1-el6
~/Software/CASA/Portable/casa-release-4.5.2-el6
~/Software/CASA/Portable/casa-release-4.5.3-el6
~/Software/CASA/Portable/casa-release-4.6.0-el6
~/Software/CASA/Portable/casa-release-4.7.0-el6
~/Software/CASA/Portable/casa-release-4.7.2-el6
~/Software/CASA/Portable/casa-release-5.0.0-218.el6
~/Software/CASA/Portable/casa-release-5.1.1-5.el6
~/Software/CASA/Portable/casa-release-5.3.0-143.el7
~/Software/CASA/Portable/casa-release-5.4.0-70.el7
~/Software/CASA/Portable/casa-release-5.4.2-5.el7
~/Software/CASA/Portable/casa-release-5.5.0-149.el7
~/Software/CASA/Portable/casa-release-5.7.2-4.el7
~/Software/CASA/Portable/casa-6.1.1-15-pipeline-2020.1.0.40
~/Software/CASA/Portable/casa-6.2.1-7-pipeline-2021.2.0.128
~/Software/CASA/Portable/casa-6.4.1-12-pipeline-2022.2.0.64
~/Software/CASA/Portable/casa-6.4.4-31-py3.8
~/Software/CASA/Portable/casa-6.5.4-9-pipeline-2023.1.0.124
~/Software/CASA/Portable/casa-6.5.5-21-py3.8
```

Sometimes a CASA version cannot be launched, it could be due to some library file problem, e.g., `lib/libtinfo.so.5`, renaming it to something like `lib/libtinfo.so.5.backup` could probably work. Such problems need to be solved out individually. Assuming all CASA versions will work, then we need a script that can switch between these CASA versions. Copy the script and the subfolder in this folder [https://github.com/1054/a3cosmos-alma-archive/tree/master/CASA](https://github.com/1054/a3cosmos-alma-archive/tree/master/CASA) to your `~/Software/CASA` folder will work. Remember to make the scripts executable: 

```
chmod +x ~/Software/CASA/SETUP.bash
chmod +x ~/Software/CASA/Portable/bin/bin_setup.bash
```

(and yes we need BASH shell)


### Add this repository's local path to your system PATH

```
export PATH=$PATH:$HOME/Cloud/Github/a3cosmos-alma-archive/bin
```


### Install the latest version of astroquery

```
pip install --upgrade git+https://github.com/astropy/astroquery.git
pip install keyrings.alt # this is needed!
```

Note that sometimes the level 1 downloading code can break due to upgrades of the ALMA archive database and the astroquery version. 


### Level 1: downloading the raw data

For a given program, for instance, 2099.1.09999.S, we can query and download the data via this command: 

```
alma_project_level_1_raw.bash 2099.1.09999.S
```


### Level 2: restoring calibration

We need to run this twice: the first time will run the observatory 'scriptForPI', then the second time will make sure the final calibrated measurement set is either named "calibrated.ms" or concatenated into a "calibrated.ms". 

```
alma_project_level_2_calib.bash 2099.1.09999.S
alma_project_level_2_calib.bash 2099.1.09999.S
```


### Level 3: splitting sources

Split out individual targets. Now we need to specify a channel width: "1" means the original channel width, "25km/s" means a integer-binned channel width as close to 25km/s as possible. We will not try to achieve the exact input velocity channel width so as to avoid aliasing issue (e.g., a "sawtooth" noise pattern, [Leroy et al. 2021 ApJS..255...19L](https://iopscience.iop.org/article/10.3847/1538-4365/abec80#apjsabec80f3)). 

```
alma_project_level_3_split.bash 2099.1.09999.S -width 1
alma_project_level_3_split.bash 2099.1.09999.S -width 25km/s
```

Run this step with different widths will create multiple sets of products for each split target. 


### Level 4: copy uvfits

Copy the split products, uvfits files, into a folder "Level_4_Data_uvfits". 

```
alma_project_level_4_copy_uvfits.bash 2099.1.09999.S -width 1
alma_project_level_4_copy_uvfits.bash 2099.1.09999.S -width 25km/s
```


### Level 4: make images

Use the split measurement sets and run CASA `tclean` to produce image cubes and continuum images, all saved into a folder "Level_4_Data_Images". 

```
alma_project_level_4_make_images.bash 2099.1.09999.S -width 1
alma_project_level_4_make_images.bash 2099.1.09999.S -width 25km/s
```

This can take a lot of time to process, say, days to weeks. 


### Level 5: deploy LTS products

The ALMA data are so huge that we would only want to keep the science-ready, most valuable, long-term-storage (LTS) prodcuts. Here I would keep the split uvfits files, images/cubes (i.e., continuum+line cube and pseudo-continuum with all channels imaged with mtmfs). This step will copy these LTS products into a deploy folder, with "meta_data_files", "cubes", "images", and "uvfits" subfolders. Each subfolder further contains a ALMA program ID subfolder, then the final LTS products are stored inside there. 

```
alma_project_level_5_deploy_all.bash /my/long/term/storage/alma/archive/
ls /my/long/term/storage/alma/archive/cubes/2099.1.09999.S/*.cube.I.image.fits
ls /my/long/term/storage/alma/archive/images/2099.1.09999.S/*.cont.I.image.fits
ls /my/long/term/storage/alma/archive/uvfits/2099.1.09999.S/*.uvfits
```


### The end









