#!/bin/bash
# 


# read input Project_code

if [[ $# -lt 2 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_deploy_fits_images.bash Project_code Deploy_Directory"
    echo "Example: "
    echo "    alma_project_level_5_deploy_fits_images.bash 2013.1.00034.S ../../alma_archive"
    echo "Notes: "
    echo "    This code will copy \"cont.I.image.fits\" files under Level_4_Data_Images "
    echo "    to the path \"<Deploy_Directory>/images/\"."
    echo "    A subfolder \"images\" will be created under the Deploy_Directory."
    exit
fi

Project_code="$1"
Deploy_dir=$(perl -MCwd -e 'print Cwd::abs_path shift' $(echo "$2" | sed -e 's%/$%%g')) # get absolute path, but remove trailing '/' first.
Script_dir=$(dirname $(perl -MCwd -e 'print Cwd::abs_path shift' "${BASH_SOURCE[0]}"))
Subset_dir="images" # "fits"
overwrite=0
nogzip=0
if [[ " $@ "x == *" -overwrite "*x ]] || [[ " $@ "x == *" --overwrite "*x ]] || [[ " $@ "x == *" overwrite "*x ]]; then
    overwrite=1
fi
if [[ " $@ "x == *" -nogzip "*x ]] || [[ " $@ "x == *" --no-gzip "*x ]] || [[ " $@ "x == *" nogzip "*x ]]; then
    nogzip=1
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

get_fits_header_key() 
{
    # read fits header 
    if [[ $# -ge 2 ]]; then
        keyname="$2"
        imfile="$1"
        if [[ "$imfile" == *".gz" ]]; then
            imfile=$(echo "$imfile" | perl -p -e 's/\.gz$//g')
        fi
        hdrfile="$imfile.hdr"
        if [[ ! -f "$hdrfile" ]]; then
            if [[ ! -f "$imfile" ]]; then
                if [[ -f "$imfile.gz" ]]; then
                    gunzip -c "$imfile.gz" > "$imfile"
                else
                    echo "Error! get_fits_header_key: File not found: \"$imfile\" or \"$imfile.gz\""
                    exit 255
                fi
                fitshdr "$imfile" > "$hdrfile"
                rm "$imfile"
            else
                fitshdr "$imfile" > "$hdrfile"
            fi
        fi
        keyvalues=($(cat "$hdrfile" | grep "^${keyname} *=.*" | tail -n 1 | perl -p -e 's/ *= */ /g'))
        outvalues=()
        for (( kk=1; kk<${#keyvalues[@]}; kk++ )); do
            if [[ "${keyvalues[kk]}" == "/" ]]; then
                break
            else
                # read non-comment header key value
                outvalues+=("${keyvalues[kk]}")
            fi
        done
        echo "${outvalues[@]}"
    fi
}


# begin
echo_output "Began processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"

echo_output "Project_code = ${Project_code}"
echo_output "Deploy_dir = ${Deploy_dir}"
echo_output "Script_dir = ${Script_dir}"
if [[ "${Deploy_dir}"x == ""x ]]; then
    echo_error "Error! Deploy_dir is empty?!"
    exit 255
fi


# check wcstools gethead sethead and wcslib fitshdr
for check_command in gethead sethead fitshdr; do
    if [[ $(type ${check_command} 2>/dev/null | wc -l) -eq 0 ]]; then
        # if not executable in the command line, try to find it in "$HOME/Cloud/Github/Crab.Toolkit.PdBI"
        if [[ -d "$HOME/Cloud/Github/Crab.Toolkit.PdBI" ]] && [[ -f "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash" ]]; then
            source "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash"
        else
            # if not executable in the command line, nor in "$HOME/Cloud/Github/Crab.Toolkit.PdBI", report error.
            echo_error "Error! \"${check_command}\" is not executable in the command line! Please install WCSTOOLS, WCSLIB, or check your \$PATH!"
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
if [[ ! -d Level_4_Data_Images ]]; then 
    echo_error "Error! \"Level_4_Data_Images\" does not exist! Please run previous steps first!"
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
echo "Searching for \"Level_4_Data_Images/*/*/output_*.cont.I.image.fits\" ..."
list_image_files=($(find Level_4_Data_Images -mindepth 3 -maxdepth 3 -type f -name "output_*.cont.I.image.fits"))
if [[ ${#list_image_files[@]} -eq 0 ]]; then
    echo "Error! Could not find any file! Please check the file names!"
    exit 255
fi


# check alma_project_meta_table.txt, 
# if it exists, then we will append to it (but clear previous project), otherwise initialize one
if [[ -f "${Deploy_dir}/alma_project_meta_table.txt" ]]; then
    echo_output "Found existing \"${Deploy_dir}/alma_project_meta_table.txt\""
    if [[ -f "${Deploy_dir}/alma_project_meta_table.txt.backup" ]]; then
        echo_output "mv \"${Deploy_dir}/alma_project_meta_table.txt.backup\" \"${Deploy_dir}/alma_project_meta_table.txt.backup.backup\""
        mv "${Deploy_dir}/alma_project_meta_table.txt.backup" "${Deploy_dir}/alma_project_meta_table.txt.backup.backup"
    fi
    echo_output "mv \"${Deploy_dir}/alma_project_meta_table.txt\" \"${Deploy_dir}/alma_project_meta_table.txt.backup\""
    mv "${Deploy_dir}/alma_project_meta_table.txt" "${Deploy_dir}/alma_project_meta_table.txt.backup"
    echo_output "cat \"${Deploy_dir}/alma_project_meta_table.txt.backup\" | head -n 1 > \"${Deploy_dir}/alma_project_meta_table.txt\""
    cat "${Deploy_dir}/alma_project_meta_table.txt.backup" | head -n 1 > "${Deploy_dir}/alma_project_meta_table.txt"
    echo_output "cat \"${Deploy_dir}/alma_project_meta_table.txt.backup\" | grep -v \'^#\' | grep -v \" ${Project_code} \" >> \"${Deploy_dir}/alma_project_meta_table.txt\""
    cat "${Deploy_dir}/alma_project_meta_table.txt.backup" | grep -v '^#' | grep -v " ${Project_code} " >> "${Deploy_dir}/alma_project_meta_table.txt"
else
    echo_output "Initializing \"${Deploy_dir}/alma_project_meta_table.txt\""
    printf "# %-15s %-20s %-25s %8s %12s %15s %11s %11s %11s %15s %15s   %-s\n" \
        'project' 'source' 'mem_ous_id' 'band' 'wavelength' 'rms' 'beam_major' 'beam_minor' 'beam_angle' 'OBSRA' 'OBSDEC' 'image_file' \
        > "${Deploy_dir}/alma_project_meta_table.txt"
fi


# list_dataset_dir
for (( i = 0; i < ${#list_image_files[@]}; i++ )); do
    image_path="${list_image_files[i]}"
    echo_output "Processing image_path \"${image_path}\""
    dataset_id=$(basename $(dirname "${image_path}"))
    project_code=""
    mem_ous_id=""
    mem_ous_id_str="" # for file name
    band=""
    if [[ "$dataset_id" == "DataSet_Merged"* ]]; then
        mem_ous_id=""
        mem_ous_id_list=()
        source_name=$(basename $(dirname $(dirname "$image_path")))
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
        image_name=$(basename "${image_path}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/^output_//g')
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
        image_name=$(basename "${image_path}" | perl -p -e 's/[ \n\r]*$//g' | perl -p -e 's/^output_//g')
    fi
    
    image_file="${project_code}.member.${mem_ous_id_str}.${image_name}"
    
    # create subset project code folder
    if [[ ! -d "${Deploy_dir}/${Subset_dir}/${project_code}" ]]; then
        echo_output "mkdir -p \"${Deploy_dir}/${Subset_dir}/${project_code}\""
        mkdir -p "${Deploy_dir}/${Subset_dir}/${project_code}"
    fi
    
    # extract fits header
    if [[ ! -f "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}.hdr" ]] || [[ $overwrite -gt 0 ]]; then
        echo_output "fitshdr \"${image_path}\" > \"${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}.hdr\""
        fitshdr "${image_path}" > "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}.hdr"
    fi
    
    # copy fits file
    if ([[ ! -f "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}" ]] && \
        [[ ! -f "${Deploy_dir}/${Subset_dir}/${project_code}${image_file}.gz" ]] \
       ) || [[ $overwrite -gt 0 ]]; then
        echo_output "cp -L \"${image_path}\" \"${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}\""
        cp -L "${image_path}" "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}"
        if [[ $nogzip -eq 0 ]]; then
            if [[ -f "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}.gz" ]]; then
                echo_output "gzip \"${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}\""
                rm "${Deploy_dir}/${Subset_dir}/${project_code}/${image_file}.gz"
            fi
            # do not run gzip here, run it later after extracting header information.
        fi
        # also copy pb and pbcor files
        pb_image_path=$(echo "${image_path}" | perl -p -e 's/.cont.I.image.fits$/.cont.I.pb.fits/g')
        pb_image_file=$(echo "${image_file}" | perl -p -e 's/.cont.I.image.fits$/.cont.I.pb.fits/g')
        if [[ -f "${pb_image_path}" ]]; then
            echo_output "cp -L \"${pb_image_path}\" \"${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}\""
            cp -L "${pb_image_path}" "${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}"
            if [[ $nogzip -eq 0 ]]; then
                if [[ -f "${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}.gz" ]]; then
                    echo_output "rm \"${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}.gz\""
                    rm "${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}.gz"
                fi
                echo_output "gzip \"${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}\""
                gzip "${Deploy_dir}/${Subset_dir}/${project_code}/${pb_image_file}"
            fi
        fi
        pbcor_image_path=$(echo "${image_path}" | perl -p -e 's/.cont.I.image.fits$/.cont.I.image.pbcor.fits/g')
        pbcor_image_file=$(echo "${image_file}" | perl -p -e 's/.cont.I.image.fits$/.cont.I.image.pbcor.fits/g')
        if [[ -f "${pbcor_image_path}" ]]; then
            echo_output "cp -L \"${pbcor_image_path}\" \"${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}\""
            cp -L "${pbcor_image_path}" "${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}"
            if [[ $nogzip -eq 0 ]]; then
                if [[ -f "${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}.gz" ]]; then
                    echo_output "rm \"${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}.gz\""
                    rm "${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}.gz"
                fi
                echo_output "gzip \"${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}\""
                gzip "${Deploy_dir}/${Subset_dir}/${project_code}/${pbcor_image_file}"
            fi
        fi
    fi
    
    # cd into the directory
    Current_dir=$(pwd -P)
    echo_output "cd \"${Deploy_dir}/${Subset_dir}/${project_code}\""
    cd "${Deploy_dir}/${Subset_dir}/${project_code}"
    # write mem_ous_id into the fits header
    if [[ $(get_fits_header_key "${image_file}" MEMBER 2>/dev/null | wc -l) -eq 0 ]]; then
        echo_output "sethead \"${image_file}\" MEMBER=\"${mem_ous_id}\""
        sethead "${image_file}" MEMBER="${mem_ous_id}"
    fi
    # compute rms
    if [[ ! -f "${image_file}.pixel.statistics.txt" ]] || [[ $overwrite -gt 0 ]]; then
        echo_output "\"${Script_dir}\"/almacosmos_get_fits_image_pixel_histogram.py \"${image_file}\""
        "${Script_dir}"/almacosmos_get_fits_image_pixel_histogram.py "${image_file}" 2>&1 > "${image_file}.get.pixel.histogram.log"
        if [[ ! -f "${image_file}.pixel.statistics.txt" ]]; then
            echo_error "Error! Could not compute pixel histogram and rms!"
            exit 255
        fi
    fi
    rms=$(cat "${image_file}.pixel.statistics.txt" | grep "^Gaussian_sigma" | cut -d '=' -f 2 | sed -e 's/^ //g')
    if [[ "$rms" == *"#"* ]]; then
        rms=$(echo "$rms" | cut -d '#' -f 1)
    fi
    rms=$(awk "BEGIN {print (${rms}) * 1e3;}") # converting from Jy/beam to mJy/beam.
    # 
    frequency=$(get_fits_header_key "${image_file}" CRVAL3)
    if [[ "$frequency"x == ""x ]]; then
        echo_error "Error! Could not get CRVAL3 key in the fits header of \"${image_file}\"!"
        exit 255
    fi
    wavelength=$(awk "BEGIN {print 2.99792458e5 / ((${frequency})/1e9);}") # convert frequency Hz to wavelength um
    # 
    OBSRA=$(get_fits_header_key "${image_file}" OBSRA)
    OBSDEC=$(get_fits_header_key "${image_file}" OBSDEC)
    if [[ "$OBSRA"x == ""x ]] || [[ "$OBSDEC"x == ""x ]]; then
        echo_error "Error! Could not get OBSRA and OBSDEC keys in the fits header of \"${image_file}\"!"
        exit 255
    fi
    # 
    BMAJ=$(get_fits_header_key "${image_file}" BMAJ)
    BMIN=$(get_fits_header_key "${image_file}" BMIN)
    BPA=$(get_fits_header_key "${image_file}" BPA)
    if [[ "$BMAJ"x == ""x ]] || [[ "$BMIN"x == ""x ]] || [[ "$BPA"x == ""x ]]; then
        echo_error "Error! Could not get BMAJ, BMIN and BPA keys in the fits header of \"${image_file}\"!"
        exit 255
    fi
    beam_major=$(awk "BEGIN {print (${BMAJ}) * 3600.0;}") # convert BMAJ deg to beam_major arcsec
    beam_minor=$(awk "BEGIN {print (${BMIN}) * 3600.0;}") # convert BMAJ deg to beam_major arcsec
    beam_angle=${BPA} # just in units of deg
    # 
    OBJECT=$(get_fits_header_key "${image_file}" OBJECT | perl -p -e 's/ /_/g')
    if [[ "$OBJECT"x == ""x ]]; then
        echo_error "Error! Could not get OBJECT key in the fits header of \"${image_file}\"!"
        exit 255
    fi
    # 
    if [[ $nogzip -eq 0 ]]; then
        echo_output "gzip \"${image_file}\""
        gzip "${image_file}"
    fi
    # 
    echo_output "cd \"${Current_dir}\""
    cd "${Current_dir}"
    
    # write to alma_project_meta_table.txt
    printf "  %-15s %-20s %-25s %8s %12g %15g %11g %11g %11g %15.10f %+15.10f   %-s\n" \
        "${project_code}" "${OBJECT}" "${mem_ous_id}" "${band}" $wavelength $rms $beam_major $beam_minor $beam_angle $OBSRA $OBSDEC "${image_file}" \
        >> "${Deploy_dir}/alma_project_meta_table.txt"
    echo_output "Written to \"${Deploy_dir}/alma_project_meta_table.txt\""
done


date +"%Y-%m-%d %Hh%Mm%Ss %Z" > "done_deploying_fits_images"
echo "pwd: $(pwd)" >> "done_deploying_fits_images"
echo "args: $@" >> "done_deploying_fits_images"







