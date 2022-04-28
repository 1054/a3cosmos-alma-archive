#!/bin/bash
# 
set -e

# Check user input

if [[ $# -lt 5 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_retrieve_calibrated_ms.bash Datamining_dir Project_code Retrieve_dir"
    exit
fi

Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))

Datamining_dir=$(echo "$1" | sed -e 's%/$%%g') # keep relative path $(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$1" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
    
if [[ ! -d "$Datamining_dir/meta_tables" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/meta_tables\""
    exit 255
fi
if [[ ! -d "$Datamining_dir/uvdata" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/uvdata\""
    exit 255
fi

Project_code="$2"

if [[ $(echo $Project_code | perl -p -e 's/[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]/OK/g') != OK ]]; then
    echo "Error! Project_code does not match regular expression 's/[0-9]{4}\.[0-9]\.[0-9]{5}\.[A-Z]/OK/g'"
    exit 255
fi

#Retrieve_dir="${Project_code}"
Retrieve_dir="$3"


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



# check paths

if [[ ! -d "$Datamining_dir/uvdata/${Project_code}" ]]; then
    echo "Error! Directory is not found: \"$Datamining_dir/uvdata/${Project_code}\""
    exit 255
fi

if [[ ! -d Level_1_Raw ]]; then
    mkdir Level_1_Raw
fi

if [[ -d "Level_1_Raw/${Project_code}" ]]; then
    echo "Warning! Target directory already exists: \"Level_1_Raw/${Project_code}\". Will do nothing."
    exit
fi


# link paths

if [[ $(type gln 2>/dev/null | wc -l) -eq 1 ]]; then
    ln_command=gln
else
    ln_command=ln
fi
if [[ "$Datamining_dir" == "/"* ]]; then
    # absolute path
    echo "$ln_command -fsT \"$Datamining_dir/uvdata/${Project_code}\" Level_1_Raw/${Project_code}"
    $ln_command -fsT "$Datamining_dir/uvdata/${Project_code}" Level_1_Raw/${Project_code}
else
    # relative path
    echo "$ln_command -fsT \"../../$Datamining_dir/uvdata/${Project_code}\" Level_1_Raw/${Project_code}"
    $ln_command -fsT "../../$Datamining_dir/uvdata/${Project_code}" Level_1_Raw/${Project_code}
fi









