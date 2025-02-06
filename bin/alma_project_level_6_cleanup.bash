#!/bin/bash
# 

#list_of_raw_dirs=($(find "Level_1_Raw" -maxdepth 1 -mindepth 1 -type d -name "*.*.*.*" ))
#list_of_split_dirs=($(find "Level_3_Split" -maxdepth 1 -mindepth 1 -type d -name "DataSet_*"))

#echo "Please run this command by yourself:"
#echo "rm -rf ${list_of_raw_dirs[@]}"
#echo "rm -rf Level_3_Split/DataSet_*/split_*"
#echo "rm -rf Level_4_Data_Images/*/DataSet_*/processing"

echo "Make sure you have finished following steps:"
echo "alma_project_level_4_copy_uvfits.bash"
echo "alma_project_level_4_copy_uvt.bash"
echo "alma_project_level_5_deploy_uvfits.bash"
echo "alma_project_level_5_deploy_fits_images.bash"
echo "alma_project_level_5_deploy_fits_image_cubes.bash"

echo "Then, please run this command by yourself:"
echo "rm -rf Level_1_Raw/*.cache/*.{tar,tar.gz}"
echo "rm -rf Level_1_Raw/*.tar"
echo "rm -rf Level_2_Calib/DataSet_*/calibration/uid*"
echo "rm -rf Level_2_Calib/DataSet_*/raw/uid*"
#echo "rm -rf Level_2_Calib/DataSet_*/product/*"
# 
# if calibrated.ms is a link, copy the original file to replace the link.
list_of_calibrated_ms=($(ls -1d Level_2_Calib/DataSet_*/calibrated/calibrated.ms))
for (( i = 0; i < ${#list_of_calibrated_ms[@]}; i++ )); do
    if [[ -L "${list_of_calibrated_ms[i]}" ]]; then
        echo "#" "${list_of_calibrated_ms[i]} is a link!"
        echo "#" mv "${list_of_calibrated_ms[i]}" "${list_of_calibrated_ms[i]}.copy"
        mv "${list_of_calibrated_ms[i]}" "${list_of_calibrated_ms[i]}.copy"
        echo "#" cp -rL "${list_of_calibrated_ms[i]}.copy" "${list_of_calibrated_ms[i]}"
        cp -rL "${list_of_calibrated_ms[i]}.copy" "${list_of_calibrated_ms[i]}"
        if [[ -d "${list_of_calibrated_ms[i]}" ]] && [[ -f "${list_of_calibrated_ms[i]}/table.dat" ]]; then
            echo "#" rm "${list_of_calibrated_ms[i]}.copy"
            rm "${list_of_calibrated_ms[i]}.copy"
        fi
    fi
done
echo "rm -rf Level_2_Calib/DataSet_*/calibrated/{raw,prod,uid}*"
echo "rm -rf Level_2_Calib/DataSet_*/calibrated/working/{uid,byspw}*"
echo "rm -rf Level_2_Calib/DataSet_*/calibrated/uid*"
echo "rm -rf Level_3_Split/DataSet_*/split_*.{ms,uvfits,uvt}"
echo "rm -rf Level_3_Split/DataSet_*/*backup*"
echo "rm -rf Level_4_Data_Images/*/DataSet_*/processing/run_tclean_*/split_*"
echo "rm -rf Level_4_Data_Images/*/DataSet_*/processing"
#echo "rm -rf Level_2_Calib/DataSet_*/external/ari_l/*"

if [[ "$@" == *"-exec"* ]]; then
    read -p "Do you really want to delete these files? [y/n] " delete
    if [[ $(echo "$delete" | tr '[:upper:]' '[:lower:]') == "y"* ]]; then
        echo "rm -rf Level_1_Raw/*.cache/*.{tar,tar.gz}"
        rm -rf Level_1_Raw/*.cache/*.{tar,tar.gz}
        echo "rm -rf Level_1_Raw/*.tar"
        rm -rf Level_1_Raw/*.tar
        echo "rm -rf Level_2_Calib/DataSet_*/calibration/uid*"
        rm -rf Level_2_Calib/DataSet_*/calibration/uid*
        echo "rm -rf Level_2_Calib/DataSet_*/raw/uid*"
        rm -rf Level_2_Calib/DataSet_*/raw/uid*
        #echo "rm -rf Level_2_Calib/DataSet_*/product/*"
        #rm -rf Level_2_Calib/DataSet_*/product/*
        echo "rm -rf Level_2_Calib/DataSet_*/calibrated/{raw,prod,uid}*"
        rm -rf Level_2_Calib/DataSet_*/calibrated/{raw,prod,uid}*
        echo "rm -rf Level_2_Calib/DataSet_*/calibrated/working/{uid,byspw}*"
        rm -rf Level_2_Calib/DataSet_*/calibrated/working/{uid,byspw}*
        echo "rm -rf Level_2_Calib/DataSet_*/calibrated/uid*"
        rm -rf Level_2_Calib/DataSet_*/calibrated/uid*
        echo "rm -rf Level_3_Split/DataSet_*/split_*.{ms,uvfits,uvt}"
        rm -rf Level_3_Split/DataSet_*/split_*.{ms,uvfits,uvt}
        echo "rm -rf Level_3_Split/DataSet_*/*backup*" 
        rm -rf Level_3_Split/DataSet_*/*backup*
        #echo "rm -rf Level_4_Data_Images/*/DataSet_*/processing/run_tclean_*/split_*"
        #rm -rf Level_4_Data_Images/*/DataSet_*/processing/run_tclean_*/split_*
        echo "rm -rf Level_4_Data_Images/*/DataSet_*/processing"
        rm -rf Level_4_Data_Images/*/DataSet_*/processing
    fi
fi

