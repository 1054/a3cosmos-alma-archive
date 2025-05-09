#!/bin/bash
# 

#source ~/Softwares/CASA/SETUP.bash 5.4.0
#source ~/Softwares/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code and meta user info (see usage)
if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_1_raw.bash Project_code"
    echo "Example: "
    echo "    alma_project_level_1_raw.bash 2013.1.00034.S"
    echo "Notes: "
    echo "    This code will use astroquery to query and download raw ALMA data for the input project code."
    echo "    If the data is proprietary, please input --user XXX"
    exit
fi
Project_code="$1"

shift

download_only=0
query_kwargs=()
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--user" ]] && [[ $# -ge 2 ]]; then
        echo "$1 $2"
        echo "$1 $2" >> "meta_user_info.txt"
        query_kwargs+=($1)
        query_kwargs+=($2)
        shift
    fi
    if [[ "$1" == "--server" ]] && [[ $# -ge 2 ]]; then
        echo "$1 $2"
        query_kwargs+=($1)
        query_kwargs+=($2)
        shift
    fi
    if [[ "$1" == "--download-only" ]]; then
        echo "download_only=1"
        download_only=1
    fi
    shift
done

#if [[ $# -gt 0 ]]; then
#    echo "$@" >> "meta_user_info.txt"
#fi

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


# query ALMA archive and prepare meta data table
if [[ ! -f "alma_archive_query_by_project_code_${Project_code}.txt" ]]; then
    echo_output "Querying ALMA archive by running following command: "
    echo_output "alma_archive_query_by_project_code.py $Project_code ${query_kwargs[@]}"
    $(dirname ${BASH_SOURCE[0]})/alma_archive_query_by_project_code.py "$Project_code" ${query_kwargs[@]}
fi

if [[ ! -f "alma_archive_query_by_project_code_${Project_code}.txt" ]]; then
    echo_error "Error! Sorry! Failed to run the code! Maybe you do not have the Python package \"astroquery\" or \"keyrings.alt\"?"
    exit 255
fi

if [[ ! -f "meta_data_table.txt" ]]; then
    cp "alma_archive_query_by_project_code_${Project_code}.txt" \
       "meta_data_table.txt"
fi


# now downloading raw data
if [[ ! -f "Level_1_Raw/${Project_code}.cache.done" ]]; then
    echo_output "Now downloading raw data (it can take several days!)"
    echo alma_archive_download_data_according_to_meta_table.py "meta_data_table.txt" -out "Level_1_Raw/${Project_code}.cache ${query_kwargs[@]}"
    alma_archive_download_data_according_to_meta_table.py "meta_data_table.txt" -out "Level_1_Raw/${Project_code}.cache" ${query_kwargs[@]}
    if [[ $? -ne 0 ]]; then echo "Error! Failed to run alma_archive_download_data_according_to_meta_table.py"; exit 255; fi
    date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "Level_1_Raw/${Project_code}.cache.done"
else
    echo_output "Already downloaded raw data (found \"Level_1_Raw/${Project_code}.cache.done\")"
fi

if [[ $(find "Level_1_Raw/${Project_code}.cache" -maxdepth 1 -type f -name "*.tar" | wc -l) -eq 0 ]]; then
    echo "Error! Failed to run alma_archive_download_data_according_to_meta_table.py"
    exit 255
fi


# check download only
if [[ $download_only -gt 0 ]]; then
    echo_output "Download only, Exit."
    exit
fi


# now unpacking tar balls
if [[ ! -f "Level_1_Raw/${Project_code}.unpack.done" ]]; then
    echo_output "Now unpacking tar balls"
    set -e
    cd Level_1_Raw/
    echo alma_archive_unpack_tar_files_with_verification.sh ${Project_code}.cache/*.tar
    alma_archive_unpack_tar_files_with_verification.sh ${Project_code}.cache/*.tar
    if [[ $? -ne 0 ]]; then echo "Error! Failed to run alma_archive_unpack_tar_files_with_verification.py"; exit 255; fi
    cd ../
    set +e
    date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "Level_1_Raw/${Project_code}.unpack.done"
else
    echo_output "Already unpacked raw data (found \"Level_1_Raw/${Project_code}.unpack.done\")"
fi


# now creating data directory structure
echo_output "Now creating data directory structure"
echo $(dirname ${BASH_SOURCE[0]})/alma_archive_make_data_dirs_with_meta_table.py "meta_data_table.txt" -out "meta_data_table.txt"
$(dirname ${BASH_SOURCE[0]})/alma_archive_make_data_dirs_with_meta_table.py "meta_data_table.txt" -out "meta_data_table.txt"
if [[ $? -ne 0 ]]; then echo "Error! Failed to run alma_archive_make_data_dirs_with_meta_table.py"; exit 255; fi


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
