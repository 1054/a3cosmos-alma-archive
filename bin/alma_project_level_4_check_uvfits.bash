#!/bin/bash
# 

#source ~/Softwares/CASA/SETUP.bash 5.4.0
#source ~/Softwares/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_4_check_uvfits.bash Project_code"
    echo "Example: "
    echo "    alma_project_level_4_check_uvfits.bash 2013.1.00034.S"
    echo "Notes: "
    echo "    This code will check blank channels in uvfits files in \"Level_3_Split\"."
    exit
fi

Project_code="$1"

# define logging files and functions
error_log_file="$(pwd)/.$(basename ${BASH_SOURCE[0]}).err"
output_log_file="$(pwd)/.$(basename ${BASH_SOURCE[0]}).log"
if [[ -f "$error_log_file" ]]; then mv "$error_log_file" "$error_log_file.2"; fi
if [[ -f "$output_log_file" ]]; then mv "$output_log_file" "$output_log_file.2"; fi

echo_output()
{
    echo "$@"
    echo "["$(date "+%Y%m%dT%H%M%S")"]" "$@" >> "$output_log_file"
}

echo_error()
{
    echo "*************************************************************"
    echo "$@"
    echo "["$(date "+%Y%m%dT%H%M%S")"]" "$@" >> "$error_log_file"
    echo "["$(date "+%Y%m%dT%H%M%S")"]" "$@" >> "$output_log_file"
    echo "*************************************************************"
}


# begin
echo_output "Began processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"


# check meta data table file
if [[ ! -f "meta_data_table.txt" ]]; then
    echo_error "Error! \"meta_data_table.txt\" was not found! Please run previous steps first!"
    exit 255
fi


# check Level_3_Split folder
if [[ ! -d Level_3_Split ]]; then 
    echo_error "Error! \"Level_3_Split\" does not exist! Please run previous steps first!"
    exit 255
fi


# read Level_3_Split/DataSet_*
list_of_datasets=($(ls -1d Level_3_Split/DataSet_* | sort -V))


# cd Level_3_Split folder
echo_output cd Level_3_Split
cd Level_3_Split


# loop datasets and run CASA split then GILDAS importuvfits
for (( i = 0; i < ${#list_of_datasets[@]}; i++ )); do
    
    DataSet_dir=$(basename ${list_of_datasets[i]})
    
    # print message
    echo_output "Now checking *.uvfits files in \"$DataSet_dir\"."
    
    # check Level_3_Split DataSet_dir
    if [[ ! -d $DataSet_dir ]]; then
        echo_error "Error! \"$DataSet_dir\" was not found! Please run Level_3_Split first! We will skip this dataset for now."
        continue
    fi
    
    # cd Level_3_Split DataSet_dir
    echo_output cd $DataSet_dir
    cd $DataSet_dir
    
    # find uvfits files
    list_of_uvfits_files=($(ls ../../Level_3_Split/$DataSet_dir/split_*_spw*_width*.uvfits ) )
    if [[ ${#list_of_uvfits_files[@]} -eq 0 ]]; then
        echo_error "Error! Failed to find \"split_*_spw*_width*.uvfits\" under \"$(pwd)\"!"
        exit 255
    fi
    
    # loop uvfits files and check blank channels
    for (( j = 0; j < ${#list_of_uvfits_files[@]}; j++ )); do
        uvfits_file=${list_of_uvfits_files[j]}
        echo_output "Checking ${uvfits_file}"
        if [[ ! -f "${uvfits_file}.check.blank.channels.txt" ]]; then
            echo_output "casa_uvfits_check_blank_channels.py" "${uvfits_file}" "|" "tee" "${uvfits_file}.check.blank.channels.txt"
            casa_uvfits_check_blank_channels.py "${uvfits_file}" | tee "${uvfits_file}.check.blank.channels.txt"
        fi
        if [[ $(cat "${uvfits_file}.check.blank.channels.txt" | grep "Found * blank channels" | wc -l) -gt 0 ]]; then
            echo_output "Checked ${uvfits_file}, and found some blank channels."
        else
            rm "${uvfits_file}.check.blank.channels.txt" # if no blank channel found then we output nothing
            echo_output "Checked ${uvfits_file}, no blank channel."
        fi
    done
    
    # cd back
    echo_output "cd ../"
    cd ../
    
    # print message
    if [[ $i -gt 0 ]]; then
        echo ""
        echo ""
    fi
    
done


echo_output "cd ../"
cd ../


# finish
echo_output "Finished processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"
echo_output ""
echo_output ""


# 
# common data directory structure:
# Level_1_Raw
# Level_2_Calib
# Level_3_Split
# Level_4_Data_uvfits
# Level_4_Data_uvt
# Level_4_Run_clean
# Level_4_Run_uvfit
# Level_5_Sci
