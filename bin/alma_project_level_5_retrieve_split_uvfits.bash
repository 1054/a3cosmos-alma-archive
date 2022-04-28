#!/bin/bash
# 
set -e

# Check user input

if [[ $# -lt 5 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_retrieve_one_dataset.bash Datamining_dir Project_code Mem_ous_id Target_name Retrieve_dir"
    exit
fi

Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))

Datamining_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$1" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
    
if [[ ! -d "$Datamining_dir/meta_tables" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/meta_tables\""
    exit 255
fi
if [[ ! -d "$Datamining_dir/uvfits" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/uvfits\""
    exit 255
fi
if [[ ! -d "$Datamining_dir/images" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/images\""
    exit 255
fi
if [[ ! -d "$Datamining_dir/images/fits" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/images/fits\""
    exit 255
fi
fi
if [[ ! -d "$Datamining_dir/images/fits_cubes" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/images/fits_cubes\""
    exit 255
fi

Project_code="$2"

if [[ $(echo $Project_code | perl -p -e 's/[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]/OK/g') != OK ]]; then
    echo "Error! Project_code does not match regular expression 's/[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]/OK/g'"
    exit 255
fi

Mem_ous_id="$3"
Mem_ous_id=$(echo "$Mem_ous_id" | perl -p -e 's%[:/]%_%g')

Target_name="$4"

#Retrieve_dir="${Project_code}"
Retrieve_dir="$5"


# find meta table

if [[ ! -d "$Retrieve_dir" ]]; then
    echo "mkdir \"$Retrieve_dir\""
    mkdir "$Retrieve_dir"
fi

Current_dir=$(pwd -P)

echo "cd \"$Retrieve_dir\""
cd "$Retrieve_dir"

if [[ -f "$Datamining_dir/meta_tables/meta_data_table_for_${Project_code}.txt" ]]; then
    echo "cp \"$Datamining_dir/meta_tables/meta_data_table_for_${Project_code}.txt\" meta_data_table.txt"
    cp "$Datamining_dir/meta_tables/meta_data_table_for_${Project_code}.txt" meta_data_table.txt
else
    echo "alma_archive_query_by_project_code.py ${Project_code}"
    alma_archive_query_by_project_code.py ${Project_code}
fi

echo "alma_archive_make_data_dirs_with_meta_table.py alma_archive_query_by_project_code_${Project_code}.txt -out meta_data_table.txt"
alma_archive_make_data_dirs_with_meta_table.py alma_archive_query_by_project_code_${Project_code}.txt -out meta_data_table.txt


# get memousid and dataset in meta_data_table.txt

meta_mem_ous_ids=($(cat meta_data_table.txt | grep -v '^#' | awk '{print $2;}' | perl -p -e 's%[:/]%_%g'))
meta_dataset_ids=($(cat meta_data_table.txt | grep -v '^#' | awk '{print $9;}'))
if [[ ${#meta_mem_ous_ids[@]} -eq 0 ]] || [[ ${#meta_mem_ous_ids[@]} -ne ${#meta_dataset_ids[@]} ]]; then
    echo "Error! Could not properly read \"meta_data_table.txt\""
    exit 255
fi


# find uvfits or ms data

find_type="none"
find_pattern=""
find_patterns=()
found_data=()
if [[ ${#found_data[@]} -eq 0 ]]; then
    find_type="ms"
    find_pattern="${Project_code}.member.${Mem_ous_id}.field.${Target_name}.*.${found_type}"
    find_patterns+=("$find_pattern")
    found_data=($(find "$Datamining_dir/uvfits/${Project_code}" -maxdepth 1 -type d -name "$find_pattern"))
fi
if [[ ${#found_data[@]} -eq 0 ]]; then
    found_type="ms"
    find_pattern="${Project_code}.member.*${Mem_ous_id}*.field.*${Target_name}*.*.${found_type}"
    find_patterns+=("$find_pattern")
    found_data=($(find "$Datamining_dir/uvfits/${Project_code}" -maxdepth 1 -type d -name "$find_pattern"))
fi
if [[ ${#found_data[@]} -eq 0 ]]; then
    found_type="uvfits"
    find_pattern="${Project_code}.member.${Mem_ous_id}.field.${Target_name}.*.${found_type}"
    find_patterns+=("$find_pattern")
    found_data=($(find "$Datamining_dir/uvfits/${Project_code}" -maxdepth 1 -type d -name "$find_pattern"))
fi
if [[ ${#found_data[@]} -eq 0 ]]; then
    find_type="uvfits"
    find_pattern="${Project_code}.member.*${Mem_ous_id}*.field.*${Target_name}*.*.${found_type}"
    find_patterns+=("$find_pattern")
    found_data=($(find "$Datamining_dir/uvfits/${Project_code}" -maxdepth 1 -type d -name "$find_pattern"))
fi
if [[ ${#found_data[@]} -eq 0 ]]; then
    echo "Error! Could not find data files in \"$Datamining_dir/uvfits/${Project_code}\" that matched following patterns:"
    for (( i = 0; i < ${#find_patterns[@]}; i++ )); do
        echo "    ${find_patterns[i]}"
    done
    exit 255
fi


# copy uvfits or ms data

for (( i = 0; i < ${#found_data[@]}; i++ )); do
    data_filepath="${found_data[i]}"
    data_filename=$(basename "$data_filepath")
    #echo "copying $data_filepath"
    data_filenamesplit=($(echo "$data_filename" | perl -p -e "s/^${Project_code}\.member\.([^.]+)\.field\.(.+)\.spw\.([^.]+)\.width\.(.+)\.${find_type}\$/\1 \2 \3 \4/g"))
    if [[ ${#data_filenamesplit[@]} -ne 4 ]]; then
        echo "Error! Filename \"$data_filename\" does not match regular expression \"^${Project_code}\.member\.([^.]+)\.field\.(.+)\.spw\.([^.]+)\.width\.(.+)\.${find_type}\$\""
        exit 255
    fi
    data_mousid=${data_filenamesplit[0]}
    data_field=${data_filenamesplit[1]}
    data_spw=${data_filenamesplit[2]}
    data_width=${data_filenamesplit[3]}
    data_dirname=""
    for (( j = 0; j < ${#meta_mem_ous_ids[@]}; j++ )); do
        if [[ "${meta_mem_ous_ids[j]}" == "$data_mousid" ]]; then
            data_dirname="${meta_dataset_ids[j]}"
            break
        fi
    done
    if [[ "$data_dirname"x == ""x ]]; then
        echo "Error! Could not find the mem_ous_id \"$data_mousid\" in the \"meta_data_table.txt\"?"
        exit 255
    fi
    
    if [[ ! -d Level_3_Split/${data_dirname} ]]; then
        mkdir -p Level_3_Split/${data_dirname}
    fi
    
    echo "cp \"$data_filepath\" \"Level_3_Split/${data_dirname}/split_${data_field}_spw${data_spw}_width${data_width}.${find_type}\""
    cp "$data_filepath" "Level_3_Split/${data_dirname}/split_${data_field}_spw${data_spw}_width${data_width}.${find_type}"
    
    if [[ "$find_type" == "uvfits" ]]; then
        if [[ ! -d Level_4_Data_uvfits/${data_dirname}/${data_field}/ ]]; then
            mkdir -p Level_4_Data_uvfits/${data_dirname}/${data_field}/
        fi
        echo "cp \"$data_filepath\" \"Level_4_Data_uvfits/${data_dirname}/${data_field}/split_${data_field}_spw${data_spw}_width${data_width}.${find_type}\""
        cp "$data_filepath" "Level_4_Data_uvfits/${data_dirname}/${data_field}/split_${data_field}_spw${data_spw}_width${data_width}.${find_type}"
    fi

done

# alma_project_level_5_deploy_uvfits.bash $Project_code ../../uvfits

# alma_project_level_5_deploy_fits_images.bash $Project_code ../../images

# alma_project_level_5_deploy_fits_image_cubes.bash $Project_code ../../images







