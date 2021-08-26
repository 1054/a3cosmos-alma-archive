#!/bin/bash
# 

#source ~/Softwares/CASA/SETUP.bash
#source ~/Softwares/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_4_copy_uvt.bash Project_code [-dataset DataSet_01]"
    echo "Example: "
    echo "    alma_project_level_4_copy_uvt.bash 2013.1.00034.S"
    echo "Notes: "
    echo "    This code will copy uvt files from \"Level_3_Split\" to \"Level_4_Data_uvt\" classified by source names."
    exit
fi

Project_code="$1"; shift

# read user input
iarg=1
width="25km/s"
select_dataset=()
output_folder="Level_4_Data_uvt"
while [[ $iarg -le $# ]]; do
    istr=$(echo ${!iarg} | tr '[:upper:]' '[:lower:]')
    if [[ "$istr" == "-width" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); width="${!iarg}"; echo "Setting width=\"${!iarg}\""
    fi
    if [[ "$istr" == "-dataset" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); select_dataset+=("${!iarg}"); echo "Selecting \"${!iarg}\""
    fi
    if [[ "$istr" == "-out" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); output_folder="${!iarg}"; echo "Outputting to \"${!iarg}\""
    fi
    iarg=$((iarg+1))
done

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
if [[ ${#select_dataset[@]} -eq 0 ]]; then
    # if user has not input -dataset, then process all datasets
    list_of_datasets=($(ls -1d Level_3_Split/DataSet_* | sort -V))
else
    list_of_datasets=()
    for (( i = 0; i < ${#select_dataset[@]}; i++ )); do
        if [[ ! -d "Level_3_Split/${select_dataset[i]}" ]]; then
            echo "Error! \"Level_3_Split/${select_dataset[i]}\" was not found!"
            exit
        fi
        list_of_datasets+=($(ls -1d "Level_3_Split/${select_dataset[i]}"))
    done
fi


# prepare output folder
if [[ ! -d "${output_folder}" ]]; then 
    mkdir "${output_folder}"
fi
echo_output cd "${output_folder}"
cd "${output_folder}"


# loop datasets and run CASA split then GILDAS importuvfits
for (( i = 0; i < ${#list_of_datasets[@]}; i++ )); do
    
    DataSet_dir=$(basename ${list_of_datasets[i]})
    
    # print message
    echo_output "Checking \"../Level_3_Split/$DataSet_dir\""
    
    # check Level_3_Split DataSet_dir
    if [[ ! -d ../Level_3_Split/$DataSet_dir ]]; then
        echo_error "Error! \"../Level_3_Split/$DataSet_dir\" was not found! Please run Level_3_Split first! We will skip this dataset for now."
        continue
    fi
    
    # prepare Level_4_Data_uvt DataSet_dir
    if [[ ! -d $DataSet_dir ]]; then
        mkdir $DataSet_dir
    fi
    echo_output cd $DataSet_dir
    cd $DataSet_dir
    
    # select width
    if [[ x"${width}" == x*"km/s" ]] || [[ x"${width}" == x*"KM/S" ]]; then
        width_val=$(echo "${width}" | sed -e 's%km/s%%g' | sed -e 's%KM/S%%g')
        width_str="${width_val}kms"
    else
        width_str="${width}"
    fi
    
    # print message
    echo_output "Now sorting out unique sources in \"$DataSet_dir\" and copying split_*_spw*_width${width_str}_SP.uvt"
    
    # read source names
    list_of_unique_source_names=($(ls ../../Level_3_Split/$DataSet_dir/split_*_spw*_width${width_str}_SP.uvt | perl -p -e 's%.*split_(.*?)_spw[0-9]+_width[0-9kms]+_SP.uvt$%\1%g' | sort -V | uniq ) )
    if [[ ${#list_of_unique_source_names[@]} -eq 0 ]]; then
        echo_error "Error! Failed to find \"../../Level_3_Split/$DataSet_dir/split_*_spw*_width${width_str}_SP.uvt\" and get unique source names!"
        exit 255
    fi
    echo "Unique source names: ${list_of_unique_source_names[@]} (${#list_of_unique_source_names[@]})"
    
    # loop list_of_unique_source_names and make dir for each source and copy uvt files
    for (( j = 0; j < ${#list_of_unique_source_names[@]}; j++ )); do
        source_name=${list_of_unique_source_names[j]}
        if [[ ! -d "${source_name}" ]]; then
            echo_output mkdir "${source_name}"
            mkdir "${source_name}"
        fi
        echo_output cp ../../Level_3_Split/$DataSet_dir/split_"${source_name}"_spw*_width${width_str}_SP.uvt "${source_name}/"
        cp ../../Level_3_Split/$DataSet_dir/split_"${source_name}"_spw*_width${width_str}_SP.uvt "${source_name}/"
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
