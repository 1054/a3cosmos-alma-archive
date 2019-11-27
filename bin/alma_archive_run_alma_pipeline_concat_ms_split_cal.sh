#!/bin/bash
# 

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_run_alma_pipeline_concat_ms_split_cal.sh /path/to/calibrated/"
    echo ""
    echo "Notes:"
    echo "    This code will cd into \"/path/to/calibrated/\" and find \"uid___*.ms.split.cal\" and concatenate them into \"calibrated.ms\" in that directory."
    echo ""
    exit
fi


script_path=$(dirname "${BASH_SOURCE[0]}")"/"$(basename "${BASH_SOURCE[0]}" | sed -e 's/\.sh$/\.py/g')


echo "cd \"$1\""
cd "$1"


# check existing "calibrated_final.ms"
if [[ -d "calibrated_final.ms" ]] || [[ -d "calibrated_final.ms" ]]; then
    echo "Found exisiting \"calibrated_final.ms\"! Can not continue! Exit!"
    exit 1
fi

# check existing "calibrated.ms"
if [[ -d "calibrated.ms" ]] || [[ -d "calibrated.ms" ]]; then
    echo "Found exisiting \"calibrated.ms\"! Can not continue! Exit!"
    exit 1
fi


# read user input
freqtol=""


# run CASA
if [[ "x$freqtol" != "x" ]]; then
    casa -c "freqtol='$freqtol'; execfile('$script_path')"
else
    casa -c "execfile('$script_path')"
fi


# check result
if [[ ! -d "calibrated.ms" ]]; then
    echo "Error! Failed to run CASA concat and produce \"calibrated.ms\"!"
    exit 1
fi


