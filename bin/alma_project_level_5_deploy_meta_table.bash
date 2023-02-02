#!/bin/bash
# 


# read input Project_code

if [[ $# -lt 2 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_deploy_meta_table.bash Project_code Deploy_Directory"
    echo "Example: "
    echo "    alma_project_level_5_deploy_meta_table.bash 2013.1.00034.S ../../alma_archive"
    echo "Notes: "
    echo "    This code will copy \"meta_data_table_for_<Project_code>.txt\" "
    echo "    to the path \"<Deploy_Directory>/meta_tables/\"."
    echo "    A subfolder \"meta_tables\" will be created under the Deploy_Directory."
    exit
fi

Project_code="$1"
Deploy_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$2" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))
Subset_dir="meta_tables"
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


# make Deploy_dir and the "$Subset_dir" subdirectory
if [[ "$Deploy_dir" == *"/" ]]; then
    Deploy_dir=$(echo "$Deploy_dir" | sed -e 's%/$%%g')
fi
if [[ ! -d "$Deploy_dir/$Subset_dir" ]]; then
    echo_output "mkdir -p \"$Deploy_dir/$Subset_dir\""
    mkdir -p "$Deploy_dir/$Subset_dir"
fi
if [[ ! -d "$Deploy_dir/$Subset_dir" ]]; then
    echo_error "Error! Could not create output directory \"$Deploy_dir/$Subset_dir\"! Please check your permission!"
    exit 255
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



# copy meta_data_table_file to Deploy_dir
if [[ -f "$Deploy_dir/$Subset_dir/meta_data_table_for_${Project_code}.txt" ]]; then
    mv "$Deploy_dir/$Subset_dir/meta_data_table_for_${Project_code}.txt" "$Deploy_dir/$Subset_dir/meta_data_table_for_${Project_code}.txt.backup"
fi
echo "cp \"$meta_data_table_file\" \"$Deploy_dir/$Subset_dir/meta_data_table_for_${Project_code}.txt\""
cp "$meta_data_table_file" "$Deploy_dir/$Subset_dir/meta_data_table_for_${Project_code}.txt"



date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "done_deploying_meta_table"
echo "pwd: $(pwd)" >> "done_deploying_meta_table"
echo "args: $@" >> "done_deploying_meta_table"







