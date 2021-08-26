#!/bin/bash
# 

data_dir_by_project="../../By_Project"
if [[ ! -d "$data_dir_by_project" ]]; then 
    echo "Error! \"$data_dir_by_project\" does not exist!"
    exit 1
fi


# 
# Read user input
archival_prefix="archival_projects/"
list_of_projects=()
i=0
while [[ $i -le $# ]]; do
    str_arg=$(echo "${!i}")
    if [[ "$str_arg" == "-archival" ]] || [[ "$str_arg" == "--archival" ]]; then
        archival_prefix="archival_projects/"
    elif [[ "$str_arg" == "-non-archival" ]] || [[ "$str_arg" == "--non-archival" ]]; then
        archival_prefix=""
    else
        list_of_projects+=("${!i}")
    fi
    i=$((i+1))
done

if [[ ${#list_of_projects[@]} -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_make_links_to_project_files.sh 2013.0.00000.S [-non-archival]"
    echo ""
    exit
fi


# 
# Make Level_N directories
if [[ ! -d Level_1_Raw ]]; then mkdir Level_1_Raw; fi
if [[ ! -d Level_2_Calib ]]; then mkdir Level_2_Calib; fi


# 
# Link to projects
for project_id in 2013.1.00034.S; do
    
    echo "cd Level_1_Raw/"
    cd Level_1_Raw/
    echo "ln -fsT ../$data_dir_by_project/${archival_prefix}${project_id} ${project_id}.cache"
    ln -fsT ../$data_dir_by_project/${archival_prefix}${project_id} ${project_id}.cache
    echo "cd ../"
    cd ../
    
    echo "cd Level_2_Calib/"
    cd Level_2_Calib/
    list_of_mem_ous_ids=($(ls -1d ../$data_dir_by_project/${archival_prefix}${project_id}/sci*/group*/mem* | sort -V))
    iSB=0
    iGB=0
    iMB=0
    for (( i = 0; i < ${#list_of_mem_ous_ids[@]}; i++ )); do
        # 
        # determine SB GB MB number, auto-increased
        str_SB=$(echo "${list_of_mem_ous_ids[i]}" | perl -pe 's%.*/(sci[^/]+)/.*%\1%g')
        str_GB=$(echo "${list_of_mem_ous_ids[i]}" | perl -pe 's%.*/(group[^/]+)/.*%\1%g')
        str_MB=$(echo "${list_of_mem_ous_ids[i]}" | perl -pe 's%.*/(mem[^/]+)$%\1%g')
        if [[ $iSB -eq 0 ]]; then 
            iSB=1
            iGB=0
            iMB=0
        elif [[ "$str_SB" != "$pre_str_SB" ]]; then
            iSB=$(echo "$iSB+1" | bc)
            iGB=0
            iMB=0
        fi
        if [[ $iGB -eq 0 ]]; then 
            iGB=1
            iMB=0
        elif [[ "$str_GB" != "$pre_str_GB" ]]; then
            iGB=$(echo "$iGB+1" | bc)
            iMB=0
        fi
        if [[ $iMB -eq 0 ]]; then 
            iMB=1
        elif [[ "$str_MB" != "$pre_str_MB" ]]; then
            iMB=$(echo "$iMB+1" | bc)
        fi
        # 
        # try to get SB name (SB = scheduling block)
        str_SB_name=""
        if [[ -f "${list_of_mem_ous_ids[i]}/README" ]]; then
            str_SB_name=$(cat "${list_of_mem_ous_ids[i]}/README" | grep "^SB name" | head -n 1 | perl -pe 's/SB name: *(.*) *$/\1/g' | sed -e 's/[^0-9a-zA-Z_.=+-]/_/g')
        fi
        # 
        echo "ln -fsT ${list_of_mem_ous_ids[i]} ${project_id}_SB${iSB}_GB${iGB}_MB${iMB}_${str_SB_name}"
        ln -fsT ${list_of_mem_ous_ids[i]} ${project_id}_SB${iSB}_GB${iGB}_MB${iMB}_${str_SB_name}
        # 
        # store str SB GB MB for next loop comparison, so that we know if we need to increase SB GB MB number or not.
        pre_str_SB="$str_SB"
        pre_str_GB="$str_GB"
        pre_str_MB="$str_MB"
    done
    echo "cd ../"
    cd ../
    
done






