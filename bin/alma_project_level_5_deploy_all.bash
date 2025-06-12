#!/bin/bash
# 
set -e

Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_deploy_all.bash \"Deploy_dir\""
    echo "Notes: "
    echo "    We will copy files into following subdirectories under the Deploy_dir: "
    echo "    \"meta_tables\", \"uvdata\", \"uvfits\", \"images\", and \"cubes\"."
    echo "    We require the current directory name to have a start with the ALMA project code."
    exit
fi

Deploy_dir="$1"
echo "Deploy_dir: \"$Deploy_dir\""
if [[ ! -d "$Deploy_dir" ]]; then
    echo "Error! The deploy directory is not found: \"$Deploy_dir\""
    exit 255
fi

Project_code=$(basename $(pwd) | cut -b 1-14)

if [[ $(echo $Project_code | perl -p -e 's/[0-9]{4}\.[0-9A]\.[0-9]{5}\.[A-Z]/OK/g') == OK ]]; then
    
    #echo "ps aux | grep \"alma_project_level_5_deploy\" | grep -v \"grep\""
    #ps aux | grep "alma_project_level_5_deploy" | grep -v "grep"
    count=$(ps aux | grep "alma_project_level_5_deploy" | grep -v "grep" | wc -l)
    #echo $count
    if [[ $count -gt 2 ]]; then
        echo "There are existing processes running \"alma_project_level_5_deploy\"! We can not run this process at the same time!"
        exit 255
    fi
    
    #if [[ ! -d "$Deploy_dir/uvfits" ]]; then
    #    echo "Error! Directory is not found: \"$Deploy_dir/uvfits\""
    #    exit 255
    #fi
    
    #if [[ ! -d "$Deploy_dir/images" ]]; then
    #    echo "Error! Directory is not found: \"$Deploy_dir/images\""
    #    exit 255
    #fi

    if [[ ! -f done_deploying_meta_table ]]; then
        alma_project_level_5_deploy_meta_table.bash $Project_code "$Deploy_dir"
    fi
    
    if [[ ! -f done_deploying_uvdata ]]; then
        alma_project_level_5_deploy_uvdata.bash $Project_code "$Deploy_dir"
    fi
    
    if [[ ! -f done_deploying_uvfits ]]; then
        alma_project_level_5_deploy_uvfits.bash $Project_code "$Deploy_dir"
    fi

    if [[ ! -f done_deploying_fits_images ]]; then
        alma_project_level_5_deploy_fits_images.bash $Project_code "$Deploy_dir"
    fi

    if [[ ! -f done_deploying_fits_image_cubes ]]; then
        alma_project_level_5_deploy_fits_image_cubes.bash $Project_code "$Deploy_dir"
    fi

else
    
    echo "Error! The current directory name seems to be not starting with an ALMA project code in the format of \"[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]\"?"
    exit 255
    
fi






