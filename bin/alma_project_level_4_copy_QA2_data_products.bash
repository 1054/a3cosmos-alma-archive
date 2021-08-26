#!/bin/bash
# 

list_of_member_dirs=($(ls -1d Level_1_Raw/*/science_goal.*/group.*/member.*))

if [[ ${#list_of_member_dirs[@]} -eq 0 ]]; then
    exit
fi

for member_dir in "${list_of_member_dirs[@]}"; do
    
    mem_ous_id=$(basename "$member_dir" | perl -p -e 's/^member\.//g')
    echo ""
    echo "${mem_ous_id}"

    product_dir=$(ls -1d Level_1_Raw/*/science_goal.*/group.*/member.${mem_ous_id}/product | head -n 1)

    script_dir=$(ls -1d Level_1_Raw/*/science_goal.*/group.*/member.${mem_ous_id}/script | head -n 1)
    
    readme_file=$(ls -1d Level_1_Raw/*/science_goal.*/group.*/member.${mem_ous_id}/README | head -n 1)

    output_dir="Level_4_Data_QA2/member.${mem_ous_id}"

    if [[ ! -d "$output_dir" ]]; then
        echo "mkdir -p \"$output_dir\""
        mkdir -p "$output_dir"
    fi

    if [[ $(find "$product_dir" -maxdepth 1 -mindepth 1 -type f -name "*" | wc -l) -gt 0 ]]; then
        echo "cp -r $product_dir/* $output_dir/"
        cp -r $product_dir/* $output_dir/
    fi

    if [[ $(find "$script_dir" -maxdepth 1 -mindepth 1 -type f -name "scriptForImaging*.py" | wc -l) -gt 0 ]]; then
        echo "cp $script_dir/scriptForImaging*.py $output_dir/"
        cp $script_dir/scriptForImaging*.py $output_dir/
    fi

    if [[ -f "$readme_file" ]]; then
        echo "cp $readme_file $output_dir/"
        cp $readme_file $output_dir/
    fi

done


