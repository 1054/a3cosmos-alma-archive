#!/bin/bash
# 


# read input Project_code

if [[ $# -lt 2 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_deploy_uvfits.bash Project_code Deploy_Directory"
    echo "Example: "
    echo "    alma_project_level_5_deploy_uvfits.bash 2013.1.00034.S ../../alma_archive"
    echo "Notes: "
    echo "    This code will copy \"*.uvfits\" files under Level_4_Data_uvfits"
    echo "    to the path \"<Deploy_Directory>/uvfits/<project_codde>\"."
    echo "    A subfolder \"uvfits/<project_code>\" will be created under the <Deploy_Directory>."
    exit
fi

Project_code="$1"
Deploy_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$2" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))
Subset_dir="uvfits"
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


# check Level_4_Data_uvt folder
if [[ ! -d Level_4_Data_uvfits ]]; then 
    echo_error "Error! \"Level_4_Data_uvfits\" does not exist! Please run previous step \"alma_project_level_4_copy_uvfits.bash\" first!"
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


# search for image files, they must comply certain naming rules
echo "Searching for \"Level_4_Data_uvfits/*/*/split_*_spw*_width*.uvfits\" ..."
list_image_files=($(find Level_4_Data_uvfits -mindepth 3 -maxdepth 3 -type f -name "split_*_spw*_width*.uvfits"))
if [[ ${#list_image_files[@]} -eq 0 ]]; then
    echo "Error! Could not find any file! Please check the file names!"
    exit 255
fi


# check alma_project_meta_table_for_uvfits.txt, 
# if it exists, then we will append to it (but clear previous project), otherwise initialize one
#if [[ -f "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt" ]]; then
#    echo_output "Found existing \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\""
#    if [[ -f "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup" ]]; then
#        echo_output "mv \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup\" \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup.backup\""
#        mv "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup" "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup.backup"
#    fi
#    echo_output "mv \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\" \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup\""
#    mv "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt" "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup"
#    echo_output "cat \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup\" | head -n 1 > \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\""
#    cat "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup" | head -n 1 > "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt"
#    echo_output "cat \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup\" | grep -v \'^#\' | grep -v \" ${Project_code} \" >> \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\""
#    cat "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt.backup" | grep -v '^#' | grep -v " ${Project_code} " >> "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt"
#else
#    echo_output "Initializing \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\""
#    printf "# %-15s %-20s %-25s %8s %12s %12s %15s %15s %15s %15s %11s %11s %11s %15s %15s   %-s\n" \
#        'project' 'source' 'mem_ous_id' 'band' 'wavelength' 'chan_num' 'chan_width' 'min_freq' 'max_freq' 'rms' 'beam_major' 'beam_minor' 'beam_angle' 'OBSRA' 'OBSDEC' 'image_file' \
#        > "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt"
#fi


# list_dataset_dir
for (( i = 0; i < ${#list_image_files[@]}; i++ )); do
    image_path="${list_image_files[i]}"
    echo_output "Processing image_path \"${image_path}\""
    dataset_id=$(basename $(dirname $(dirname "${image_path}")))
    project_code=""
    mem_ous_id=""
    mem_ous_id_str="" # for file name
    band=""
    if [[ "$dataset_id" == "DataSet_Merged"* ]]; then
        mem_ous_id=""
        mem_ous_id_list=()
        source_name=$(basename $(dirname "${image_path}"))
        for (( j = 0; j < ${#list_source_name[@]}; j++ )); do
            #echo "list_source_name: ${list_source_name[@]} (${#list_source_name[@]})" #<DEBUG>#
            if [[ "${list_source_name[j]}" == "$source_name" ]]; then
                if [[ "${mem_ous_id}"x == ""x ]]; then
                    project_code="${list_project_code[j]}"
                    mem_ous_id_list+=("${list_mem_ous_id[j]}") 
                    mem_ous_id="${list_mem_ous_id[j]}"
                    mem_ous_id_str=$(echo "${list_mem_ous_id[j]}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/[^a-zA-Z0-9_+-]/_/g')
                    band="${list_alma_band[j]}"
                elif [[ "${mem_ous_id}"x != *"${list_mem_ous_id[j]}"*x ]]; then
                    mem_ous_id_list+=("${list_mem_ous_id[j]}")
                    mem_ous_id="${mem_ous_id}+${list_mem_ous_id[j]}"
                    if [[ ${#mem_ous_id_list[@]} -le 6 ]]; then
                        mem_ous_id_str="${mem_ous_id_str}+"$(echo "${list_mem_ous_id[j]}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/[^a-zA-Z0-9_+-]/_/g')
                    fi
                fi
            fi
        done
        if [[ "${project_code}"x == ""x ]] || [[ "${mem_ous_id}"x == ""x ]]; then
            echo_error "Error! Could not determine project_code and mem_ous_id from ${meta_data_table_file} for the input image ${image_path} source name ${source_name}!"
            exit 255
        fi
        if [[ ${#mem_ous_id_list[@]} -gt 6 ]]; then
            mem_ous_id_str="${mem_ous_id_str}++truncated++"
        fi
    else
        for (( j = 0; j < ${#list_dataset_id[@]}; j++ )); do
            #echo "list_dataset_id: ${list_dataset_id[@]} (${#list_dataset_id[@]})" #<DEBUG>#
            if [[ "${list_dataset_id[j]}" == "$dataset_id" ]]; then
                project_code="${list_project_code[j]}"
                mem_ous_id="${list_mem_ous_id[j]}"
                band="${list_alma_band[j]}"
                break
            fi
        done
        if [[ "${project_code}"x == ""x ]] || [[ "${mem_ous_id}"x == ""x ]]; then
            echo_error "Error! Could not find dataset_id ${dataset_id} in ${meta_data_table_file}!"
            exit 255
        fi
        mem_ous_id_str=$(echo "${mem_ous_id}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/[^a-zA-Z0-9_+-]/_/g')
    fi
    
    # set output subdir
    if [[ ! -d "$Deploy_dir/$Subset_dir/$project_code" ]]; then
        echo_output "mkdir -p \"$Deploy_dir/$Subset_dir/$project_code\""
        mkdir -p "$Deploy_dir/$Subset_dir/$project_code"
    fi
    if [[ ! -d "$Deploy_dir/$Subset_dir/$project_code" ]]; then
        echo_error "Error! Could not create output directory \"$Deploy_dir/$Subset_dir/$project_code\"! Please check your permission!"
        exit 255
    fi
    
    # recheck the accurate width
    ctype4=$(gethead "${image_path}" CTYPE4)
    ref_freq=$(gethead "${image_path}" CRVAL4)
    chan_width=$(gethead "${image_path}" CDELT4)
    if [[ "$ctype4"x != "FREQ"x ]]; then
        echo_error "Error! Could not get CTYPE4 key or it is not \"FREQ\" in the fits header of \"${image_path}\"!"
        exit 255
    fi
    if [[ "$ref_freq"x == ""x ]]; then
        echo_error "Error! Could not get CRVAL4 key in the fits header of \"${image_path}\"!"
        exit 255
    fi
    if [[ "$chan_width"x == ""x ]]; then
        echo_error "Error! Could not get CDELT4 key in the fits header of \"${chan_width}\"!"
        exit 255
    fi
    chan_velwidth=$(mathcalc0f "${chan_width}/(${ref_freq})*2.99792458e5")
    if [[ "${chan_velwidth}" == "-"* ]]; then
        chan_velwidth=$(echo "${chan_velwidth}" | perl -p -e 's/^-//g')
    fi
    
    # set output name <project_code>.member.<mem_ous_id>.field.<target_name>.spw.<spw_id>.width.<chan_width>.uvfits
    # chan_width is the radio definition velocity width about the spw center
    image_name=$(basename "${image_path}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/^split_(.*)_spw([0-9]+)_width(.*)\.uvfits/\1.spw.\2/g')
    image_file="${project_code}.member.${mem_ous_id_str}.field.${image_name}.width.${chan_velwidth}kms.uvfits"
    
    # copy fits file
    if [[ ! -f "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}" ]] || [[ $overwrite -gt 0 ]]; then
        echo_output "cp -L \"${image_path}\" \"${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}\""
        cp -L "${image_path}" "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}"
    fi
    
    # cd into the directory
    Current_dir=$(pwd -P)
    echo_output "cd \"${Deploy_dir}/${Subset_dir}/${project_code}\""
    cd "${Deploy_dir}/${Subset_dir}/${project_code}"
    # write mem_ous_id into the fits header
    if [[ $(gethead "${image_file}" MEMBER 2>/dev/null | wc -l) -eq 0 ]]; then
        echo_output "sethead \"${image_file}\" MEMBER=\"${mem_ous_id}\""
        sethead "${image_file}" MEMBER="${mem_ous_id}"
    fi
    
    # # get spw info
    #frequency=$(gethead "${image_file}" CRVAL4)
    #if [[ "$frequency"x == ""x ]]; then
    #    echo_error "Error! Could not get CRVAL4 key in the fits header of \"${image_file}\"!"
    #    exit 255
    #fi
    #wavelength=$(awk "BEGIN {print 2.99792458e5 / ((${frequency})/1e9);}") # convert frequency Hz to wavelength um
    ## 
    #ref_pix=$(gethead "${image_file}" CRPIX4)
    #chan_num=$(gethead "${image_file}" NAXIS4)
    #chan_width=$(gethead "${image_file}" CDELT4)
    #min_freq=$(mathcalc "${frequency}-(${ref_pix}-1)*(${chan_width})")
    #max_freq=$(mathcalc "${frequency}+(${chan_num}-${ref_pix})*(${chan_width})")
    
    # cd back
    echo_output "cd \"${Current_dir}\""
    cd "${Current_dir}"
    
    # write to alma_project_meta_table_for_uvfits.txt
    #printf "  %-15s %-20s %-25s %8s %12g %12d %+15.9e %15.9e %15.9e %15g %11g %11g %11g %15.10f %+15.10f   %-s\n" \
    #    "${project_code}" "${OBJECT}" "${mem_ous_id}" "${band}" $wavelength $chan_num $chan_width $min_freq $max_freq $rms $beam_major $beam_minor $beam_angle $OBSRA $OBSDEC "${image_file}" \
    #    >> "${Deploy_dir}/alma_project_meta_table_for_uvfits.txt"
    #echo_output "Written to \"${Deploy_dir}/alma_project_meta_table_for_uvfits.txt\""
done


date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "done_deploying_uvfits"
echo "pwd: $(pwd)" >> "done_deploying_uvfits"
echo "args: $@" >> "done_deploying_uvfits"







