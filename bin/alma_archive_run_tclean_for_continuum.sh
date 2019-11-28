#!/bin/bash
# 


# Usage
if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_run_tclean_for_continuum.sh \"XXX.ms\""
    echo ""
    exit
fi


# check CASA
if [[ ! -d "$HOME/Softwares/CASA" ]]; then
    echo "Error! \"$HOME/Softwares/CASA\" was not found!"
    echo "Sorry, we need to put all versions of CASA under \"$HOME/Softwares/CASA/Portable/\" directory!"
    exit 1
fi
if [[ ! -f "$HOME/Softwares/CASA/SETUP.bash" ]]; then
    echo "Error! \"$HOME/Softwares/CASA/SETUP.bash\" was not found!"
    echo "Sorry, please ask Daizhong by emailing dzliu@mpia.de!"
    exit 1
fi
casa_setup_script_path="$HOME/Softwares/CASA/SETUP.bash"



# 
data_path="$1"
shift

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
echo source "$casa_setup_script_path"
source "$casa_setup_script_path"

echo casa --no-gui --log2term -c "\"import sys; sys.path.append(\\\"$(dirname ${BASH_SOURCE[0]})\\\"); import alma_archive_run_tclean_for_continuum; alma_archive_run_tclean_for_continuum.go(\\\"$data_name\\\")\""
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



