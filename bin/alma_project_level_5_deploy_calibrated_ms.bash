#!/bin/bash
# 


# read input Project_code

if [[ $# -lt 2 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_deploy_calibrated_ms.bash Project_code Deploy_Directory"
    echo "Example: "
    echo "    alma_project_level_5_deploy_calibrated_ms.bash 2013.1.00034.S ../../uvdata"
    echo "Notes: "
    echo "    This code will copy calibrated.ms under Level_1_Raw/<project_code>/s*/g*/m*/calibrated/ to Deploy_Directory."
    echo "    A subfolder \"<project_codde>\" will be created under the Deploy_Directory."
    exit
fi

Project_code="$1"
Deploy_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$2" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))
overwrite=0
if [[ " $@ "x == *" -overwrite "*x ]] || [[ " $@ "x == *" --overwrite "*x ]] || [[ " $@ "x == *" overwrite "*x ]]; then
    overwrite=1
fi

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

mathcalc() { awk "BEGIN {print ($1);}" ; }
mathcalc0f() { awk "BEGIN {printf \"%.0f\",($1);}" ; }



# begin
echo_output "Began processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"

echo_output "Project_code = ${Project_code}"
echo_output "Deploy_dir = ${Deploy_dir}"
echo_output "Script_dir = ${Script_dir}"
if [[ "${Deploy_dir}"x == ""x ]]; then
    echo_error "Error! Deploy_dir is empty?!"
    exit 255
fi


# check wcstools gethead sethead
for check_command in gethead sethead; do
    if [[ $(type ${check_command} 2>/dev/null | wc -l) -eq 0 ]]; then
        # if not executable in the command line, try to find it in "$HOME/Cloud/Github/Crab.Toolkit.PdBI"
        if [[ -d "$HOME/Cloud/Github/Crab.Toolkit.PdBI" ]] && [[ -f "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash" ]]; then
            source "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash"
        else
            # if not executable in the command line, nor in "$HOME/Cloud/Github/Crab.Toolkit.PdBI", report error.
            echo_error "Error! \"${check_command}\" is not executable in the command line! Please install WCSTOOLS, or check your \$PATH!"
            exit 1
        fi
    fi
done


# check meta data table file
meta_data_table_file="meta_data_table.txt"
if [[ -f "meta_data_table_with_dataset_names.txt" ]]; then
    meta_data_table_file="meta_data_table_with_dataset_names.txt"
fi
if [[ ! -f "${meta_data_table_file}" ]]; then
    echo_error "Error! \"${meta_data_table_file}\" was not found! Please run previous steps first!"
    exit 255
fi


# check Level_4_Data_uvt folder
if [[ ! -d Level_1_Raw/${Project_code} ]]; then 
    echo_error "Error! \"Level_1_Raw/${Project_code}\" does not exist!"
    exit 255
fi


# remove Deploy_dir directory suffix
if [[ "$Deploy_dir" == *"/" ]]; then
    Deploy_dir=$(echo "$Deploy_dir" | sed -e 's%/$%%g')
fi


# read meta table and list mem_ous_id
list_project_code=($(cat "${meta_data_table_file}" | awk '{ if(substr($1,0,1)!="#") print $1; }'))
list_mem_ous_id=($(cat "${meta_data_table_file}" | awk '{ if(substr($1,0,1)!="#") print $2; }'))
list_source_name=($(cat "${meta_data_table_file}" | awk '{ if(substr($1,0,1)!="#") print $3; }'))
list_alma_band=($(cat "${meta_data_table_file}" | awk '{ if(substr($1,0,1)!="#") print $6; }'))
list_dataset_id=($(cat "${meta_data_table_file}" | awk '{ if(substr($1,0,1)!="#") print $9; }'))

if [[ ${#list_project_code[@]} -eq 0 ]]; then
    echo_error "Error! Could not read the Project_code column in \"${meta_data_table_file}\"!"
    exit 255
fi
if [[ ${#list_mem_ous_id[@]} -eq 0 ]]; then
    echo_error "Error! Could not read the Mem_ous_id column in \"${meta_data_table_file}\"!"
    exit 255
fi
if [[ ${#list_source_name[@]} -eq 0 ]]; then
    echo_error "Error! Could not read the Source_name column in \"${meta_data_table_file}\"!"
    exit 255
fi
if [[ ${#list_alma_band[@]} -eq 0 ]]; then
    echo_error "Error! Could not read the Band column in \"${meta_data_table_file}\"!"
    exit 255
fi
if [[ ${#list_dataset_id[@]} -eq 0 ]]; then
    echo_error "Error! Could not read the DataSet_dirname column in \"${meta_data_table_file}\"!"
    exit 255
fi
check_project_code=0
for (( i = 0; i < ${#list_project_code[@]}; i++ )); do
    if [[ "${list_project_code[i]}" == "${Project_code}" ]]; then
        check_project_code=1
        break
    fi
done
if [[ $check_project_code -eq 0 ]]; then
    echo_error "Error! The input Project_code ${Project_code} is not found in \"${meta_data_table_file}\"!"
    exit 255
fi


# search for files, they must comply certain naming rules
echo_output "Searching for \"Level_1_Raw/${Project_code}/s*/g*/m*/calibrated/calibrated.ms\" ..."
list_files=($(find "Level_1_Raw/${Project_code}" -mindepth 5 -maxdepth 5 -type d -name "calibrated.ms"))
if [[ ${#list_files[@]} -eq 0 ]]; then
    echo_output "Searching for \"Level_1_Raw/${Project_code}/s*/g*/m*/calibrated/uid__*.ms\" ..."
    list_files=($(find "Level_1_Raw/${Project_code}" -mindepth 5 -maxdepth 5 -type d -name "uid__*.ms"))
fi
if [[ ${#list_files[@]} -eq 0 ]]; then
    echo_output "Searching for \"Level_1_Raw/${Project_code}/s*/g*/m*/calibrated/uid__*.ms.split.cal\" ..."
    list_files=($(find "Level_1_Raw/${Project_code}" -mindepth 5 -maxdepth 5 -type d -name "uid__*.ms.split.cal"))
fi
if [[ ${#list_files[@]} -eq 0 ]]; then
    echo_error "Error! Could not find any file! Please check the file names!"
    exit 255
fi


# list_dataset_dir
for (( i = 0; i < ${#list_files[@]}; i++ )); do
    file_path="${list_files[i]}"
    echo_output "Processing file_path \"${file_path}\""
    file_path_split=($(echo "$file_path" | sed -e 's%/% %g'))
    deploy_path=$(echo "$file_path" | sed -e "s%Level_1_Raw%${Deploy_dir}%g")
    if [[ -d "$deploy_path" ]] && [[ $overwrite -gt 0 ]]; then
        # backup the existing data to overwrite
        if [[ -d "$deploy_path.backup" ]]; then
            if [[ -d "$deploy_path.backup.backup" ]]; then
                rm -rf "$deploy_path.backup.backup"
            fi
            mv "$deploy_path.backup" "$deploy_path.backup.backup"
        fi
        mv "$deploy_path" "$deploy_path.backup"
    else
        # create folder if needed
        deploy_subdir=$(dirname "$deploy_path")
        if [[ ! -d "$deploy_subdir" ]]; then
            echo_output "mkdir -p \"$deploy_subdir\""
            mkdir -p "$deploy_subdir"
        fi
    fi
    if [[ -d "$deploy_path" ]]; then
        echo "Warning! Found existing \"$deploy_path\" and overwrite is not set. Do nothing."
    else
        echo_output "cp -r \"$file_path\" \"$deploy_path\""
        cp -r "$file_path" "$deploy_path"
    fi
done


date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "done_deploying_calibrated_ms"
echo "pwd: $(pwd)" >> "done_deploying_calibrated_ms"
echo "args: $@" >> "done_deploying_calibrated_ms"







