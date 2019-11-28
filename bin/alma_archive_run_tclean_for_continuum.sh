#!/bin/bash
# 

if [[ $# -lt 1 ]]; then
    echo "Usage: alma_archive_run_tclean_for_continuum.sh \"XXX.ms\""
    exit
fi

data_path="$1"

data_dir=$(dirname "$data_path")
data_name=$(basename "$data_path")

current_dir=$(pwd)

echo cd "$data_dir"
cd "$data_dir"

if [[ ! -d "run_tclean" ]]; then
    mkdir "run_tclean"
fi
echo cd "run_tclean"
cd "run_tclean"

ln -fs ../"$data_name"

# Run CASA
echo casa --no-gui --log2term -c "import sys; sys.path.append(\"$(dirname ${BASH_SOURCE[0]})\"); import alma_archive_run_tclean_for_continuum; alma_archive_run_tclean_for_continuum.go(\"$data_name\")"
casa --no-gui --log2term -c "import sys; sys.path.append(\"$(dirname ${BASH_SOURCE[0]})\"); import alma_archive_run_tclean_for_continuum; alma_archive_run_tclean_for_continuum.go(\"$data_name\")"

echo cd ../
cd ../

echo cd "$current_dir"
cd "$current_dir"

# the code run in CASA will output to a subdirectory named "run_tclean"
if [[ -f "$data_dir/run_tclean/list_of_images.json" ]]; then
    echo "Output to \"$data_dir/run_tclean/list_of_images.json\" which contains the list of cleaned continuum images."
else
    echo "Error occurred! Please check the log!"
fi

