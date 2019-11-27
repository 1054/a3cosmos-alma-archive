#!/bin/bash
# 


# Usage
if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_run_alma_pipeline_scriptForPI.sh root_directory"
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
# Prepare Functions
# -- check_and_extract_casa_version_in_readme_file
# -- check_and_concat_calibrated_ms
# 
check_and_extract_casa_version_in_readme_file() {
    if [[ $# -ge 1 ]]; then
        local script_dir="$1"
        # 
        # check empty README* files
        if [[ -f "$script_dir/README_CASA_VERSION" ]] || [[ -L "$script_dir/README_CASA_VERSION" ]]; then
            if [[ $(cat $script_dir/README_CASA_VERSION | wc -l) -eq 0 ]]; then
                rm "$script_dir/README_CASA_VERSION"
            fi
        fi
        # check if README_CASA_VERSION exists
        if [[ -f "$script_dir/README_CASA_VERSION" ]] || [[ -L "$script_dir/README_CASA_VERSION" ]]; then
            return 0 #source "$casa_setup_script_path" "$script_dir/README_CASA_VERSION"
        else
            # check if README exists, and extract CASA version from the README file
            if [[ -f "$script_dir/README" ]] || [[ -L "$script_dir/README" ]]; then
                grep -i "CASA Version" "$script_dir/README" > "$script_dir/README_CASA_VERSION"
                # re-check if valid
                if [[ $(cat "$script_dir/README_CASA_VERSION" | wc -l) -eq 0 ]]; then
                    rm "$script_dir/README_CASA_VERSION"
                fi
            fi
            # re-check if README_CASA_VERSION exists
            if [[ -f "$script_dir/README_CASA_VERSION" ]] || [[ -L "$script_dir/README_CASA_VERSION" ]]; then
                return 0 #source "$casa_setup_script_path" "$script_dir/README_CASA_VERSION"
            else
                # if no README file or failed to extract CASA Version from there, then we read "qa/*.tgz"
                if [[ -d "$script_dir/qa" ]] || [[ -L "$script_dir/qa" ]]; then
                    list_of_found_files=($(find -L "$script_dir/qa" -name "*.tgz"))
                    if [[ ${#list_of_found_files[@]} -gt 0 ]]; then
                        # run our python code to extract CASA Version from "qa/*.tgz"
                        echo "Running alma_archive_find_casa_version_in_qa_weblog.py \"${list_of_found_files[0]}\" > \"$script_dir/README_CASA_VERSION\""
                        if [[ $(type alma_archive_find_casa_version_in_qa_weblog.py 2>/dev/null | wc -l) -ge 1 ]]; then
                            alma_archive_find_casa_version_in_qa_weblog.py "${list_of_found_files[0]}" > "$script_dir/README_CASA_VERSION"
                        elif [[ -f $(dirname ${BASH_SOURCE[0]})/alma_archive_find_casa_version_in_qa_weblog.py ]]; then
                            $(dirname ${BASH_SOURCE[0]})/alma_archive_find_casa_version_in_qa_weblog.py "${list_of_found_files[0]}" > "$script_dir/README_CASA_VERSION"
                        else
                            echo "Error! Could not find command \"alma_archive_find_casa_version_in_qa_weblog.py\", which should be shipped together with this code!"
                            return -1 # exit 1
                        fi
                        # re-cehck if valid
                        if [[ $(cat "$script_dir/README_CASA_VERSION" | wc -l) -eq 0 ]]; then
                            rm "$script_dir/README_CASA_VERSION"
                        fi
                        # re-check if README_CASA_VERSION exists
                        if [[ -f "$script_dir/README_CASA_VERSION" ]] || [[ -L "$script_dir/README_CASA_VERSION" ]]; then
                            return 0 #source "$casa_setup_script_path" "$script_dir/README_CASA_VERSION"
                        else
                            echo "Error! Failed to run alma_archive_find_casa_version_in_qa_weblog.py \"${list_of_found_files[0]}\"!"
                            return -1 # exit 1
                        fi
                    else
                        echo "Error! Could not find \"$script_dir/qa/*.tgz\"! Could not determine CASA Version!"
                        return -1 # exit 1
                    fi
                else
                    echo "Error! Could not find either \"$script_dir/README_CASA_VERSION\" or \"$script_dir/README\" files or \"$script_dir/qa/\" folder! Could not determine CASA Version!"
                    return -1 # exit 1
                fi
            fi
        fi
    else
        return -1
    fi
}




check_and_concat_calibrated_ms() {
    if [[ $# -ge 1 ]]; then
        local script_dir="$1"
        # 
        # check if "calibrated" dir already exists
        if [[ -d "$script_dir/calibrated" ]] || [[ -L "$script_dir/calibrated" ]]; then
            # if "calibrated" dir exists, check if it contains "calibrated_final.ms"
            if [[ -d "$script_dir/calibrated/calibrated_final.ms" ]] || [[ -L "$script_dir/calibrated/calibrated_final.ms" ]]; then
                if [[ $(find "$script_dir/calibrated/calibrated_final.ms/" -mindepth 1 -maxdepth 1 | wc -l) -eq 0 ]]; then
                    echo "Warning! \"$script_dir/calibrated/calibrated_final.ms\" is empty! Deleting it!"
                    echo "rm -r \"$script_dir/calibrated/calibrated_final.ms\""
                    #echo "*************************** dry-run *************************"
                    rm -r "$script_dir/calibrated/calibrated_final.ms"
                fi
            fi
            if [[ -d "$script_dir/calibrated/calibrated_final.ms" ]] || [[ -L "$script_dir/calibrated/calibrated_final.ms" ]]; then
                echo "Found existing non-empty \"$script_dir/calibrated/calibrated_final.ms\"! Will not re-run the pipeline! Skip and continue!"
                return 0 # continue # OK, no need to re-make calibrated data
            else
                # if "calibrated" dir exists, check if it contains "calibrated.ms"
                if [[ -d "$script_dir/calibrated/calibrated.ms" ]] || [[ -L "$script_dir/calibrated/calibrated.ms" ]]; then
                    if [[ $(find "$script_dir/calibrated/calibrated.ms/" -mindepth 1 -maxdepth 1 | wc -l) -eq 0 ]]; then
                        echo "Warning! \"$script_dir/calibrated/calibrated.ms\" is empty! Deleting it!"
                        echo "rm -r \"$script_dir/calibrated/calibrated.ms\""
                        #echo "*************************** dry-run *************************"
                        rm -r "$script_dir/calibrated/calibrated.ms"
                    fi
                fi
                if [[ -d "$script_dir/calibrated/calibrated.ms" ]] || [[ -L "$script_dir/calibrated/calibrated.ms" ]]; then
                    echo "Found existing non-empty \"$script_dir/calibrated/calibrated.ms\"! Will not re-run the pipeline! Skip and continue!"
                    return 0 # continue # OK, no need to re-make calibrated data
                else
                    # if "calibrated" dir exists, but no "calibrated*.ms", then check if "uid___*.ms.split.cal" dirs exist or not
                    list_of_ms_split_cal_dirs=($(find "$script_dir/calibrated/" -mindepth 1 -maxdepth 1 -type d -name "uid___*.ms.split.cal"))
                    # 20180612 for CASA 5, ALMA Cycle 5 and later, file names are changed
                    if [[ ${#list_of_ms_split_cal_dirs[@]} -eq 0 ]]; then
                        list_of_ms_split_cal_dirs=($(find "$script_dir/calibrated/" -mindepth 1 -maxdepth 1 -type d -name "uid___*.ms"))
                    fi
                    # 20180612 for CASA 5, ALMA Cycle 5 and later, file names are changed
                    if [[ ${#list_of_ms_split_cal_dirs[@]} -eq 0 ]]; then
                        list_of_ms_split_cal_dirs=($(find "$script_dir/calibrated/" -mindepth 1 -maxdepth 1 -type l -name "uid___*.ms"))
                    fi
                    if [[ ${#list_of_ms_split_cal_dirs[@]} -eq 1 ]]; then
                        echo "Found \"$script_dir/calibrated\" and one \"uid___*.ms.split.cal\" data therein but no \"calibrated_final.ms\" nor \"calibrated.ms\"! Will make a link."
                        echo bash -c "cd \"$script_dir/calibrated\"; ln -fsT \"$(basename ${list_of_ms_split_cal_dirs[0]})\" \"calibrated.ms\""
                        bash -c "cd \"$script_dir/calibrated\"; ln -fsT \"$(basename ${list_of_ms_split_cal_dirs[0]})\" \"calibrated.ms\""
                        continue
                    elif [[ ${#list_of_ms_split_cal_dirs[@]} -gt 1 ]]; then
                        echo "Found \"$script_dir/calibrated\" and \"uid___*.ms.split.cal\" therein but no \"calibrated_final.ms\" nor \"calibrated.ms\"! Will try to concatenate them."
                        # check README file which contains CASA version and source CASA version
                        list_of_readme_files=($(find -L "$script_dir" -name "README"))
                        if [[ ${#list_of_readme_files[@]} -gt 0 ]]; then
                            source "$casa_setup_script_path" "${list_of_readme_files[0]}"
                        else
                            list_of_readme_files=($(find -L "$script_dir" -name "README_CASA_VERSION"))
                            if [[ ${#list_of_readme_files[@]} -gt 0 ]]; then
                                source "$casa_setup_script_path" "${list_of_readme_files[0]}"
                            else
                                echo "Error! Failed to find README file under $script_dir!"
                                return -1 # exit 1
                            fi
                        fi
                        # run CASA concat
                        echo "Running alma_archive_run_alma_pipeline_concat_ms_split_cal.sh \"$script_dir/calibrated\""
                        if [[ $(type alma_archive_run_alma_pipeline_concat_ms_split_cal.sh 2>/dev/null | wc -l) -ge 1 ]]; then
                            alma_archive_run_alma_pipeline_concat_ms_split_cal.sh "$script_dir/calibrated"
                        elif [[ -f $(dirname ${BASH_SOURCE[0]})"/alma_archive_run_alma_pipeline_concat_ms_split_cal.sh" ]]; then
                            $(dirname ${BASH_SOURCE[0]})/alma_archive_run_alma_pipeline_concat_ms_split_cal.sh "$script_dir/calibrated"
                        else
                            echo "Error! Could not find command \"alma_archive_run_alma_pipeline_concat_ms_split_cal.sh\", which should be shipped together with this code!"
                            return -1 # exit 1
                        fi
                        # check the concat result
                        if [[ ! -d "$script_dir/calibrated/calibrated.ms" ]]; then
                            echo "Error! Failed to run alma_archive_run_alma_pipeline_concat_ms_split_cal.sh and produce \"calibrated.ms\"!"
                            return -1 # exit 1
                        else
                            echo "Successfully concatenated \"uid___*.ms.split.cal\" into \"calibrated.ms\"! No need to re-run the pipeline! Continue!"
                            return 0 # continue # OK, no need to re-make calibrated data
                        fi
                    else
                        # if not, then detele the whole "calibrated" directory
                        echo "Found \"$script_dir/calibrated\" but no \"calibrated_final.ms\", \"calibrated.ms\" or \"uid___*.ms.split.cal\"! Will delete this \"calibrated\" directory!"
                        echo "rm -r \"$script_dir/calibrated\""
                        #echo "*************************** dry-run *************************"
                        rm -r "$script_dir/calibrated"
                    fi
                fi
            fi
        fi
        return 1 # Need to re-make calibrated data
    else
        return -1
    fi
}










# read user inputs
list_of_input_dirs=()
log_file=""
i=1
while [[ $i -le $# ]]; do
    str_arg=$(echo "${!i}" | sed -e 's/^--/-/g' | awk '{print tolower($0)}')
    if [[ "$str_arg" == "-log" ]]; then
        if [[ $((i+1)) -le $# ]]; then
            i=$((i+1))
            log_file="${!i}"
        fi
    else
        list_of_input_dirs+=("${!i}")
    fi
    i=$((i+1))
done


# get current directory
current_dir=$(pwd)


# find "scriptForPI.py" files
for (( i = 0; i < ${#list_of_input_dirs[@]}; i++ )); do
    # 
    # skip empty input dir
    if [[ x"${list_of_input_dirs[i]}" == x"" ]]; then
        continue
    fi
    # 
    # format dir path, remove trailing slash
    input_dir=$(echo "${list_of_input_dirs[i]}" | perl -p -e 's%/$%%g')
    # 
    # check input dir existance
    if [[ ! -d "${input_dir}" ]] && [[ ! -L "${input_dir}" ]]; then
        echo "Error! The input direcotry \"${input_dir}\" does not exist!"
        exit 1
    fi
    # 
    # find "scriptForPI.py" files
    list_of_script_files=($(find "${input_dir}/" -type f -name "scriptForPI.py"))
    if [[ ${#list_of_script_files[@]} -eq 0 ]]; then
        list_of_script_files=($(find "${input_dir}/" -type f -name "member*.scriptForPI.py"))
    fi
    if [[ ${#list_of_script_files[@]} -eq 0 ]]; then
        echo "Warning! Could not find any \"scriptForPI.py\" or \"member*.scriptForPI.py\" under \"${input_dir}/\"!"
    fi
    # 
    # loop "scriptForPI.py" file 
    for (( j = 0; j < ${#list_of_script_files[@]}; j++ )); do
        # 
        # store script file name and dir path
        script_file="${list_of_script_files[j]}"
        script_name=$(basename "$script_file")
        script_dir=$(dirname $(dirname "$script_file"))
        echo ""
        echo ""
        seq -s "*" 100 | tr -d '[:digit:]'; echo "" # separator
        echo "script_file = $script_file"
        echo "script_dir = $script_dir"
        seq -s "*" 100 | tr -d '[:digit:]'; echo "" # separator
        # 
        # check_and_extract_casa_version_in_readme_file
        echo "check_and_extract_casa_version_in_readme_file \"$script_dir\""
        check_and_extract_casa_version_in_readme_file "$script_dir"
        check_return_code=$?
        if [[ $check_return_code -lt 0 ]]; then
            echo "check_and_extract_casa_version_in_readme_file FAILED!"
            exit 1 # got error when running the function, exit
        fi
        # 
        # check_and_concat_calibrated_ms
        echo "check_and_concat_calibrated_ms \"$script_dir\""
        check_and_concat_calibrated_ms "$script_dir"
        check_return_code=$?
        if [[ $check_return_code -lt 0 ]]; then
            echo "check_and_concat_calibrated_ms FAILED!"
            exit 1 # got error when running the function, exit
        elif [[ $check_return_code -gt 0 ]]; then
            # 
            # check directories for running pipeline
            if [[ ! -d "$script_dir/raw" ]] && [[ ! -L "$script_dir/raw" ]]; then
                echo "Error! Direcotry \"$script_dir/raw\" was not found!"
                exit 1
            fi
            if [[ ! -d "$script_dir/script" ]] && [[ ! -L "$script_dir/script" ]]; then
                echo "Error! Direcotry \"$script_dir/script\" was not found!"
                exit 1
            fi
            # 
            # cd script dir
            echo "cd \"$script_dir/script/\""
            cd "$script_dir/script/"
            # 
            # source CASA with the version in README_CASA_VERSION file
            echo "source \"$casa_setup_script_path\" \"../README_CASA_VERSION\""
            source "$casa_setup_script_path" "../README_CASA_VERSION"
            if [[ $(type casa 2>/dev/null | wc -l) -eq 0 ]]; then
                echo "Error! CASA was not found! source \"$casa_setup_script_path\" \"../README_CASA_VERSION\" FAILED!"
                exit 1
            fi
            # 
            # check if pipeline mode, 
            # then run CASA
            if [[ $(find . -mindepth 1 -maxdepth 1 -type f -name "*_pipescript.py" | wc -l) -gt 0 ]] || \
                [[ $(find . -mindepth 1 -maxdepth 1 -type f -name "*_piperestorescript.py" | wc -l) -gt 0 ]]; then
                echo casa --pipeline --nogui --log2term -c "execfile('$script_name')"
                casa --pipeline --nogui --log2term -c "execfile('$script_name')"
            else
                echo casa --nogui --log2term -c "execfile('$script_name')"
                casa --nogui --log2term -c "execfile('$script_name')"
            fi
            # 
            # cd back
            echo "cd \"$current_dir/\""
            cd "$current_dir/"
        fi
    done
    
    # print a separator line
    seq -s "-" 100 | tr -d '[:digit:]'; echo ""
    
done





