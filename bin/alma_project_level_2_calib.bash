#!/bin/bash
# 

#source ~/Softwares/CASA/SETUP.bash 5.4.0
#source ~/Softwares/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code
if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_2_calib.bash Project_code"
    echo "Example: "
    echo "    alma_project_level_2_calib.bash 2013.1.00034.S"
    echo "Notes: "
    echo "    This code will call CASA to apply the ALMA pipeline calibration for all datasets in the meta data table."
    exit
fi
Project_code="$1"

# read user input
iarg=1
select_dataset=()
with_gui=0
while [[ $iarg -le $# ]]; do
    istr=$(echo ${!iarg} | tr '[:upper:]' '[:lower:]' | sed -e 's/--/-/g')
    if [[ "$istr" == "-dataset" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); select_dataset+=("${!iarg}"); echo "Selecting dataset \"${!iarg}\""
    elif [[ "$istr" == "-with-gui" ]]; then
        with_gui=1; echo "Setting with gui"
    fi
    iarg=$((iarg+1))
done

# get script_dir
script_dir=$(dirname $(realpath ${BASH_SOURCE[0]}))
script_name=$(basename ${BASH_SOURCE[0]})

# define logging files and functions
error_log_file="$(pwd)/.${script_name}.err"
output_log_file="$(pwd)/.${script_name}.log"
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


# check CASA
if [[ ! -d "$HOME/Softwares/CASA" ]] && [[ ! -d "$HOME/Software/CASA" ]]; then
    echo "Error! \"$HOME/Software/CASA\" was not found!"
    echo "Sorry, we need to put all versions of CASA under \"$HOME/Software/CASA/Portable/\" directory!"
    exit 1
fi
if [[ ! -f "$HOME/Softwares/CASA/SETUP.bash" ]] && [[ ! -f "$HOME/Software/CASA/SETUP.bash" ]]; then
    echo "Error! \"$HOME/Software/CASA/SETUP.bash\" was not found!"
    echo "Please copy \"$(dirname ${BASH_SOURCE[0]})/casa_setup/SETUP.bash\" to \"$HOME/Software/CASA/SETUP.bash\" and make it executable."
    #echo "Sorry, please ask Daizhong by emailing dzliu@mpia.de!"
    exit 1
fi
if [[ ! -f "$HOME/Softwares/CASA/Portable/bin/bin_setup.bash" ]] && [[ ! -f "$HOME/Software/CASA/Portable/bin/bin_setup.bash" ]]; then
    echo "Error! \"$HOME/Software/CASA/Portable/bin/bin_setup.bash\" was not found!"
    echo "Please copy \"$(dirname ${BASH_SOURCE[0]})/casa_setup/bin_setup.bash\" to \"$HOME/Software/CASA/Portable/bin/bin_setup.bash\" and make it executable."
    #echo "Sorry, please ask Daizhong by emailing dzliu@mpia.de!"
    exit 1
fi

if [[ -f "$HOME/Software/CASA/SETUP.bash" ]]; then
    casa_setup_script_path="$HOME/Software/CASA/SETUP.bash"
elif [[ -f "$HOME/Softwares/CASA/SETUP.bash" ]] && [[ ! -f "$HOME/Software/CASA/SETUP.bash" ]]; then
    casa_setup_script_path="$HOME/Softwares/CASA/SETUP.bash"
fi


# check python
check_python_ok=1
if [[ $(python -c 'import pypdf' 2>&1 | grep "No module" | wc -l) -gt 0 ]]; then
    echo "Error! Python pypdf package is not found! Please install it with \`pip install pypdf\`"
    check_python_ok=0
fi
if [[ $(python -c 'import bs4' 2>&1 | grep "No module" | wc -l) -gt 0 ]]; then
    echo "Error! Python beautifulsoup4 package is not found! Please install it with \`pip install beautifulsoup4\`"
    check_python_ok=0
fi
if [[ $(python -c 'import tarfile' 2>&1 | grep "No module" | wc -l) -gt 0 ]]; then
    echo "Error! Python tarfile package is not found! Please install it with \`pip install tarfile\`"
    check_python_ok=0
fi
if [[ $check_python_ok -eq 0 ]]; then
    exit 255
fi


# check meta table
if [[ ! -f "meta_data_table.txt" ]]; then
    echo_error "Error! \"meta_data_table.txt\" was not found! Please run previous steps first!"
    exit 255
fi


# check Level_2_Calib folder
if [[ ! -d Level_2_Calib ]]; then 
    echo_error "Error! \"Level_2_Calib\" does not exist! Please run previous steps first!"
    exit 255
fi


# read Level_2_Calib/DataSet_*
if [[ ${#select_dataset[@]} -eq 0 ]]; then
    # if user has not input -dataset, then process all datasets
    list_of_datasets=($(ls -1d Level_2_Calib/DataSet_* | sort -V))
else
    list_of_datasets=()
    for (( i = 0; i < ${#select_dataset[@]}; i++ )); do
        if [[ ! -d "Level_2_Calib/${select_dataset[i]}" ]]; then
            echo "Error! \"Level_2_Calib/${select_dataset[i]}\" was not found!"
            exit
        fi
        list_of_datasets+=($(ls -1d "Level_2_Calib/${select_dataset[i]}"))
    done
fi


# loop datasets and run ALMA calibration pipeline scriptForPI.py
for (( i = 0; i < ${#list_of_datasets[@]}; i++ )); do
    dataset_dir=${list_of_datasets[i]}
    dataset_name=$(basename "${dataset_dir}")
    
    # run pipelines
    proc_kwargs=()
    if [[ $with_gui -eq 0 ]]; then
        proc_kwargs=(--nogui)
    fi
    proc_kwargs+=("${dataset_dir}")
    echo_output "Now running ALMA calibration pipeline for \"${dataset_dir}\""
    echo_output "${script_dir}/alma_archive_run_alma_pipeline_scriptForPI.sh ${proc_kwargs[@]} > \".alma_archive_run_alma_pipeline_scriptForPI_${dataset_name}.log\""
    ${script_dir}/alma_archive_run_alma_pipeline_scriptForPI.sh ${proc_kwargs[@]} > ".alma_archive_run_alma_pipeline_scriptForPI_${dataset_name}.log"

    # check output
    if [[ -d "${dataset_dir}/calibrated" ]]; then
        echo_output "Successfully produced \"${dataset_dir}/calibrated\"!"

        # further check calibrated.ms
        if [[ $(find "${dataset_dir}/calibrated/" -maxdepth 1 -name "uid*.ms*" | wc -l) -gt 0 ]]; then
            if [[ ! -d "${dataset_dir}/calibrated/calibrated.ms" ]] && [[ ! -d "${dataset_dir}/calibrated/calibrated_final.ms" ]]; then
                echo_output "Now running ALMA calibration pipeline for \"${dataset_dir}\" again to concatenate uid*.ms to calibrated.ms"
                echo_output "${script_dir}/alma_archive_run_alma_pipeline_scriptForPI.sh ${proc_kwargs[@]} > \".alma_archive_run_alma_pipeline_scriptForPI_${dataset_name}_concat.log\""
                ${script_dir}/alma_archive_run_alma_pipeline_scriptForPI.sh ${proc_kwargs[@]} > ".alma_archive_run_alma_pipeline_scriptForPI_${dataset_name}_concat.log"
            fi
        fi
    else
        echo_error "Error! Failed to produce \"${dataset_dir}/calibrated\"!"
    fi
    
    if [[ $i -gt 0 ]]; then
        echo ""
        echo ""
    fi
    
done


# finish
echo_output "Finished processing ALMA project ${Project_code} with ${script_name}"
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
