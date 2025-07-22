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


script_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(dirname "${BASH_SOURCE[0]}"))
script_name=$(basename "${BASH_SOURCE[0]}" | sed -e 's/\.sh$//g')


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


# run CASA
use_execfile=1  # always use execfile, casa 5.4.0 also needs that
if [[ -f "../README_CASA_VERSION" ]]; then
    casa_version_numbers=($(cat "../README_CASA_VERSION" | head -n 1 | perl -p -e 's/^.*: ([0-9]+)\.([0-9]+).*$/\1 \2/g'))
    casa_version_major=${casa_version_numbers[0]}
    casa_version_minor=${casa_version_numbers[1]}
    if [[ $casa_version_major -le 3 ]] || ([[ $casa_version_major -eq 4 ]] && [[ $casa_version_minor -le 2 ]]); then
        use_execfile=1
    fi
fi
if [[ $use_execfile -eq 0 ]]; then
    echo "casa -c \"import sys; sys.path.append(\\\"$script_dir\\\"); from $script_name import $script_name; $script_name(locals())\""
    casa --nogui --nologger --log2term --nocrashreport -c "import sys; sys.path.append(\"$script_dir\"); from $script_name import $script_name; $script_name(locals())"
    #echo "casa -c \"import sys; sys.path.append(\\\"$script_dir\\\"); from $script_name import $script_name; $script_name({**globals(), **locals()})\""
    #casa --nogui --nologger --log2term --nocrashreport -c "import sys; sys.path.append(\"$script_dir\"); from $script_name import $script_name; $script_name({**globals(), **locals()})"
else 
    # fix for very old CASA version
    cat "$script_dir"/"$script_name.py" > "${script_name}_tmp.py"
    echo "" >> "${script_name}_tmp.py"
    echo "from itertools import chain" >> "${script_name}_tmp.py"
    echo "import sys" >> "${script_name}_tmp.py"
    echo "" >> "${script_name}_tmp.py"
    #echo "if sys.version_info >= (3, 6):" >> "${script_name}_tmp.py"
    #echo "    $script_name({**globals(), **locals()})" >> "${script_name}_tmp.py" # still syntax error
    #echo "else:" >> "${script_name}_tmp.py"
    #echo "    $script_name(dict(chain(globals().iteritems(), locals().iteritems())))" >> "${script_name}_tmp.py"
    echo "import copy" >> "${script_name}_tmp.py"
    echo "globals_dict = copy.copy(globals())" >> "${script_name}_tmp.py"
    echo "globals_dict.update(locals())" >> "${script_name}_tmp.py"
    echo "$script_name(globals_dict)" >> "${script_name}_tmp.py"
    echo "" >> "${script_name}_tmp.py"
    echo "" >> "${script_name}_tmp.py"
    chmod +x "${script_name}_tmp.py"
    echo "casa -c \"execfile(\\\"${script_name}_tmp.py\\\")\""
    casa --nogui --nologger --log2term --nocrashreport -c "execfile(\"${script_name}_tmp.py\")"
fi

# check result
if [[ ! -d "calibrated.ms" ]]; then
    echo "Error! Failed to run CASA concat and produce \"calibrated.ms\"!"
    exit 1
fi


