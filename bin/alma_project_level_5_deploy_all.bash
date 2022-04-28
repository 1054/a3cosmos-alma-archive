#!/bin/bash
# 
set -e

Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))

Project_code=$(basename $(pwd) | cut -b 1-14)

if [[ $(echo $Project_code | perl -p -e 's/[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]/OK/g') == OK ]]; then
    
    if [[ $(ps aux | grep "alma_project_level_5_deploy" | grep -v "grep" | wc -l) -gt 1 ]]; then
        echo "There are existing processes running \"alma_project_level_5_deploy\"! We can not run this process at the same time!"
        exit 255
    fi
    
    if [[ ! -d ../../uvfits ]]; then
        echo "Error! Directory is not found: \"../../uvfits\""
        exit 255
    fi
    
    if [[ ! -d ../../images ]]; then
        echo "Error! Directory is not found: \"../../images\""
        exit 255
    fi

    if [[ ! -f done_deploying_meta_table ]]; then
        alma_project_level_5_deploy_meta_table.bash $Project_code ../../meta_tables
    fi
    
    if [[ ! -f done_deploying_calibrated_ms ]]; then
        alma_project_level_5_deploy_calibrated_ms.bash $Project_code ../../uvdata
    fi
    
    if [[ ! -f done_deploying_uvfits ]]; then
        alma_project_level_5_deploy_uvfits.bash $Project_code ../../uvfits
    fi

    if [[ ! -f done_deploying_fits_images ]]; then
        alma_project_level_5_deploy_fits_images.bash $Project_code ../../images
    fi

    if [[ ! -f done_deploying_fits_image_cubes ]]; then
        alma_project_level_5_deploy_fits_image_cubes.bash $Project_code ../../images
    fi

fi






