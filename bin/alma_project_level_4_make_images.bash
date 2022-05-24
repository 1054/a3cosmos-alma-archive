#!/bin/bash
# 

#source ~/Software/CASA/SETUP.bash 5.4.0
#source ~/Software/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_5_make_images.bash Project_code [-dataset DataSet_01]"
    echo "Example: "
    echo "    alma_project_level_5_make_images.bash 2013.1.00034.S"
    echo "Options: "
    echo "    -width 25km/s"
    echo "    -maximsize 2000"
    echo "    -dataset DataSet_Merged_A"
    echo "Notes: "
    echo "    This code will make clean cube images using ms data under \"Level_3_Split\" and store into \"Level_4_Data_Images\" classified by source names."
    exit
fi

Project_code="$1"; shift

# read user input
iarg=1
width="*" # "25km/s"
maximsize=2000
overwrite=0
keepfiles=0
skipcalibrators=1
select_dataset=()
while [[ $iarg -le $# ]]; do
    istr=$(echo ${!iarg} | tr '[:upper:]' '[:lower:]')
    if [[ "$istr" == "-width" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); width="${!iarg}"; echo "Setting width=\"${!iarg}\""
    fi
    if ([[ "$istr" == "-maximsize" ]] || [[ "$istr" == "-imsize" ]]) && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); maximsize="${!iarg}"; echo "Setting maximsize=\"${!iarg}\""
    fi
    if [[ "$istr" == "-dataset" ]] && [[ $((iarg+1)) -le $# ]]; then
        iarg=$((iarg+1)); select_dataset+=("${!iarg}"); echo "Selecting dataset \"${!iarg}\""
    fi
    if [[ "$istr" == "-skipcalibrators" ]] || [[ "$istr" == "-skip-calibrators" ]]; then
        skipcalibrators=1
    elif [[ "$istr" == "-noskipcalibrators" ]] || [[ "$istr" == "-do-not-skip-calibrators" ]]; then
        skipcalibrators=0
    fi
    if [[ "$istr" == "-overwrite" ]]; then
        overwrite=$((overwrite+1))
    fi
    if [[ "$istr" == "-keepfiles" ]]; then
        keepfiles=$((keepfiles+1))
    fi
    iarg=$((iarg+1))
done

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


# begin
echo_output "Began processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"


# check meta data table file
if [[ ! -f "meta_data_table.txt" ]]; then
    echo_error "Error! \"meta_data_table.txt\" was not found! Please run previous steps first!"
    exit 255
fi


# check Level_3_Split folder
if [[ ! -d Level_3_Split ]]; then 
    echo_error "Error! \"Level_3_Split\" does not exist! Please run previous steps first!"
    exit 255
fi


# read Level_3_Split/DataSet_*
if [[ ${#select_dataset[@]} -eq 0 ]]; then
    # if user has not input -dataset, then process all datasets
    list_of_datasets=($(ls -1d Level_3_Split/DataSet_* | sort -V))
else
    list_of_datasets=()
    for (( i = 0; i < ${#select_dataset[@]}; i++ )); do
        if [[ ! -d "Level_3_Split/${select_dataset[i]}" ]]; then
            echo "Error! \"Level_3_Split/${select_dataset[i]}\" was not found!"
            exit
        fi
        list_of_datasets+=($(ls -1d "Level_3_Split/${select_dataset[i]}"))
    done
fi


# check python casa lib dir
lib_python_dzliu_dir=$(dirname ${BASH_SOURCE[0]})
if [[ ! -d "$lib_python_dzliu_dir" ]]; then
    echo "Error! lib_python_dzliu directory \"$lib_python_dzliu_dir\" was not found! It should be shipped with this code!"
    exit 255
fi


# prepare calibrator list


# prepare Level_4_Data_Images folder
if [[ ! -d Level_4_Data_Images ]]; then 
    mkdir Level_4_Data_Images
fi
echo_output cd Level_4_Data_Images
cd Level_4_Data_Images


# loop datasets and run CASA split then GILDAS importuvfits
for (( i = 0; i < ${#list_of_datasets[@]}; i++ )); do
    
    DataSet_dir=$(basename ${list_of_datasets[i]})
    
    # print message
    echo_output "Now sorting out unique sources in \"$DataSet_dir\" and linking *.ms"
    
    # check Level_3_Split DataSet_dir
    if [[ ! -d ../Level_3_Split/$DataSet_dir ]]; then
        echo_error "Error! \"../Level_3_Split/$DataSet_dir\" was not found! Please run Level_3_Split first! We will skip this dataset for now."
        continue
    fi
    
    # check Level_3_Split listobs file
    if [[ $skipcalibrators -gt 0 ]] && [[ ! -f ../Level_3_Split/$DataSet_dir/calibrated.ms.listobs.txt ]]; then
        echo_error "Error! \"../Level_3_Split/$DataSet_dir/calibrated.ms.listobs.txt\" was not found! Please run Level_3_Split first! We will skip this dataset for now."
        continue
    fi
    
    # read source names
    if [[ x"${width}" == x*"km/s" ]] || [[ x"${width}" == x*"KM/S" ]]; then
        width_val=$(echo "${width}" | sed -e 's%km/s%%g' | sed -e 's%KM/S%%g')
        width_str="${width_val}kms"
    else
        width_str="${width}"
    fi
    list_of_unique_source_names=($(find ../Level_3_Split/$DataSet_dir/ -type d -name "split_*_spw*_width${width_str}.ms" | perl -p -e 's%.*split_(.*?)_spw[0-9]+_width[0-9kmsKMS]+.ms$%\1%g' | sort -V | uniq ) )
    if [[ ${#list_of_unique_source_names[@]} -eq 0 ]]; then
        echo_error "Error! Failed to find \"../Level_3_Split/$DataSet_dir/split_*_spw*_width${width_str}.ms\" and get unique source names!"
        exit 255
    fi
    
    # loop list_of_unique_source_names and make dir for each source and link ms files
    for (( j = 0; j < ${#list_of_unique_source_names[@]}; j++ )); do
        source_name=${list_of_unique_source_names[j]}
        
        # check observe_target and skip calibrators
        if [[ $skipcalibrators -gt 0 ]] && [[ -f ../Level_3_Split/$DataSet_dir/calibrated.ms.listobs.txt ]]; then
            if [[ $(cat ../Level_3_Split/$DataSet_dir/calibrated.ms.listobs.txt | grep "OBSERVE_TARGET" | wc -l) -gt 0 ]]; then
                cat ../Level_3_Split/$DataSet_dir/calibrated.ms.listobs.txt | grep "OBSERVE_TARGET" > list_of_observe_target_in_$DataSet_dir.txt
                if [[ $(grep " ${source_name} " list_of_observe_target_in_$DataSet_dir.txt | wc -l) -eq 0 ]]; then
                    continue
                fi
            fi
        fi
        #if [[ " $source_name " =~ " ${calibrator_list} " ]]; then
        #    continue
        #fi
        
        # make source_name dataset_dir dir
        if [[ ! -d "${source_name}/$DataSet_dir" ]]; then
            echo_output mkdir -p "${source_name}/$DataSet_dir"
            mkdir -p "${source_name}/$DataSet_dir"
        fi
        
        # cd source_name dataset_dir dir
        echo_output "cd ${source_name}/$DataSet_dir"
        cd "${source_name}/$DataSet_dir"
        
        # find each ms data
        #list_of_ms_data=($(find ../../../Level_3_Split/$DataSet_dir/ -type d -name "split_${source_name}_spw*_width${width_str}.ms" | sort -V ) )
        # 20210510 now also considered mosaic subfields
        list_of_ms_data=($(find ../../../Level_3_Split/$DataSet_dir/ -type d \( -name "split_${source_name}_spw*_width${width_str}.ms" -o -name "split_${source_name}_spw*_width${width_str}_mosaic_*.ms" \) | sort -V ) )
        
        # prepare to get list of continuum ms data
        list_of_continuum_ms_data=()
        list_of_concatenated_spws=()
        list_of_run_tclean_dirs=()
        
        # loop each ms data
        for (( k = 0; k < ${#list_of_ms_data[@]}; k++ )); do
            
            ms_data=$(basename "${list_of_ms_data[k]}") # this includes the suffix ".ms"
            ms_name=$(echo "${ms_data}" | perl -p -e 's/\.ms$//g')
            ms_spw=$(echo "${ms_data}" | perl -p -e 's/split_.*_spw([0-9]+)_.*\.ms$/\1/g')
            
            # check existing images
            if ([[ -f "${ms_name}_cube_clean.image.fits" ]] && [[ "${width}" != "0" ]]) && ([[ -f "${ms_name}_cont_clean.image.fits" ]]); then
                echo "Found image cube \"${ms_name}_{cube,cont}_clean.image.fits\". Will not overwrite. Continue."
                continue
            fi
            
            # make processing dir
            if [[ ! -d "processing" ]]; then
                mkdir "processing"
            fi
            echo_output "cd processing"
            cd "processing"
            
            # link ms data for processing
            if [[ ! -L "${ms_data}" ]]; then
                echo_output ln -fsT "../${list_of_ms_data[k]}" "${ms_data}"
                ln -fsT "../${list_of_ms_data[k]}" "${ms_data}"
            fi
            run_script="run_tclean_${ms_name}.bash"
            py_script="run_tclean_${ms_name}.py"
            log_script="run_tclean_${ms_name}.log"
            done_script="run_tclean_${ms_name}.done"
            if [[ ! -f "${run_script}" ]]; then
                if [[ -f "${done_script}" ]]; then
                    mv "${done_script}" "${done_script}.backup" # remove previous done_script
                fi
                # write bash script which will launch CASA and run the python script
                echo "#!/bin/bash"                                                    >  "${run_script}"
                echo "#"                                                              >> "${run_script}"
                echo "if [[ \$(type casa 2>/dev/null | wc -l) -eq 0 ]]; then"         >> "${run_script}"
                echo "    if [[ -f ~/Software/CASA/SETUP.bash ]]; then"               >> "${run_script}"
                echo "        source ~/Software/CASA/SETUP.bash"                      >> "${run_script}" # here I try to see if we have CASA
                echo "    else"                                                       >> "${run_script}"
                echo "        echo \"Error! casa command does not exist!\"; exit 255" >> "${run_script}"
                echo "    fi"                                                         >> "${run_script}"
                echo "fi"                                                             >> "${run_script}"
                echo ""                                                               >> "${run_script}"
                echo "casa --nogui --nologger --log2term -c \"${py_script}\" "        >> "${run_script}"
                echo ""                                                               >> "${run_script}"
                echo "if [[ \$? -eq 0 ]]; then"                                       >> "${run_script}"
                echo "    date \"+%Y-%m-%d %Hh%Mm%Ss %Z\" > ${done_script}"           >> "${run_script}"
                echo "fi"                                                             >> "${run_script}"
                echo ""                                                               >> "${run_script}"
                chmod +x "${run_script}"
                # write the python script which will load the 'dzliu_clean.py' library and run cube clean
                # here we make a full channel range cube if width != 0
                echo "# run this in CASA"                                             >  "${py_script}"
                echo "sys.path.append(\"${lib_python_dzliu_dir}\")"                   >> "${py_script}"
                echo "import dzliu_clean"                                             >> "${py_script}"
                echo "reload(dzliu_clean)"                                            >> "${py_script}"
                echo ""                                                               >> "${py_script}"
                if [[ "${width}" != "0" ]]; then
                echo "dzliu_clean.dzliu_clean(\\"                                     >> "${py_script}"
                echo "    \"${ms_data}\", \\"                                         >> "${py_script}"
                echo "    make_line_cube=True, \\"                                    >> "${py_script}"
                echo "    make_continuum=False, \\"                                   >> "${py_script}"
                echo "    line_name='cube', \\"                                       >> "${py_script}"
                echo "    line_velocity=-1, \\"                                       >> "${py_script}"
                echo "    line_velocity_width=-1, \\"                                 >> "${py_script}"
                echo "    max_imsize=${maximsize}, \\"                                >> "${py_script}"
                echo "    )"  >> "${py_script}"                                       >> "${py_script}"
                echo ""                                                               >> "${py_script}"
                fi
                echo "dzliu_clean.dzliu_clean(\\"                                     >> "${py_script}"
                echo "    \"${ms_data}\", \\"                                         >> "${py_script}"
                echo "    make_line_cube=False, \\"                                   >> "${py_script}"
                echo "    make_continuum=True, \\"                                    >> "${py_script}"
                echo "    max_imsize=${maximsize}, \\"                                >> "${py_script}"
                echo "    )"                                                          >> "${py_script}"
                echo ""                                                               >> "${py_script}"
                chmod +x "${py_script}"
            fi
            if [[ ! -f "${done_script}" ]] || [[ $overwrite -ge 1 ]]; then
                chmod +x "${run_script}"
                echo_output "Running ${run_script} > ${log_script}"
                ./"${run_script}" > "${log_script}" 2>&1
                if [[ ! -f "${done_script}" ]]; then
                    echo "Error! Failed to run the script \"${run_script}\"!"
                    exit 255
                fi
            fi
            if [[ ! -f ../"${ms_name}_cube_clean.image.fits" ]] && [[ "${width}" != "0" ]]; then
                echo_output "Copying result \"${ms_name}_cube_clean.image.fits\""
                cp "run_tclean_${ms_name}/${ms_name}_cube_clean.image.fits" ../
                echo_output "Copying result \"${ms_name}_cube_clean.pb.fits\""
                cp "run_tclean_${ms_name}/${ms_name}_cube_clean.pb.fits" ../
                echo_output "Copying result \"${ms_name}_cube_clean.image.pbcor.fits\""
                cp "run_tclean_${ms_name}/${ms_name}_cube_clean.image.pbcor.fits" ../
            fi
            #if [[ ! -f ../"output_${source_name}.cube.I.image.fits" ]] && [[ "${width}" != "0" ]]; then
            #    echo_output "Copying result \"${ms_name}_cube_clean.image.fits\" as \"output_${source_name}.cube.I.image.fits\""
            #    cp "run_tclean_${ms_name}/${ms_name}_cube_clean.image.fits" ../"output_${source_name}.cube.I.image.fits"
            #fi
            #if [[ ! -f ../"${ms_name}_cont_clean.image.fits" ]]; then
            #    echo_output "Copying result \"${ms_name}_cont_clean.image.fits\""
            #    cp "run_tclean_${ms_name}/${ms_name}_cont_clean.image.fits" ../
            #fi
            
            list_of_run_tclean_dirs+=("run_tclean_${ms_name}")
            list_of_continuum_ms_data+=("run_tclean_${ms_name}/${ms_name}_cont.ms")
            list_of_concatenated_spws+=("$ms_spw")
            
            
            # concatenate continuum ms data
            if [[ ${#list_of_continuum_ms_data[@]} -eq ${#list_of_ms_data[@]} ]]; then
                # 
                output_concat_spw_str=$(echo "${list_of_concatenated_spws[@]}" | sed -e 's/ /_/g')
                output_concat_ms_data=merged_"${source_name}"_spw${output_concat_spw_str}.ms
                output_concat_ms_name=$(echo "${output_concat_ms_data}" | perl -p -e 's/\.ms$//g')
                # 
                run_script="run_continuum_concat_and_tclean_${source_name}.bash"
                py_script="run_continuum_concat_and_tclean_${source_name}.py"
                log_script="run_continuum_concat_and_tclean_${source_name}.log"
                done_script="run_continuum_concat_and_tclean_${source_name}.done"
                if [[ ! -f "${run_script}" ]]; then
                    if [[ -f "${done_script}" ]]; then
                        mv "${done_script}" "${done_script}.backup" # remove previous done_script
                    fi
                    # write bash script which will launch CASA and run the python script
                    echo "#!/bin/bash"                                                    >  "${run_script}"
                    echo "#"                                                              >> "${run_script}"
                    echo "if [[ \$(type casa 2>/dev/null | wc -l) -eq 0 ]]; then"         >> "${run_script}"
                    echo "    if [[ -f ~/Software/CASA/SETUP.bash ]]; then"               >> "${run_script}"
                    echo "        source ~/Software/CASA/SETUP.bash"                      >> "${run_script}" # here I try to see if we have CASA
                    echo "    else"                                                       >> "${run_script}"
                    echo "        echo \"Error! casa command does not exist!\"; exit 255" >> "${run_script}"
                    echo "    fi"                                                         >> "${run_script}"
                    echo "fi"                                                             >> "${run_script}"
                    echo ""                                                               >> "${run_script}"
                    echo "casa --nogui --nologger --log2term -c \"${py_script}\" "        >> "${run_script}"
                    echo ""                                                               >> "${run_script}"
                    echo "if [[ \$? -eq 0 ]]; then"                                       >> "${run_script}"
                    echo "    date \"+%Y-%m-%d %Hh%Mm%Ss %Z\" > ${done_script}"           >> "${run_script}"
                    echo "fi"                                                             >> "${run_script}"
                    echo ""                                                               >> "${run_script}"
                    chmod +x "${run_script}"
                    # write the python script which will load the 'dzliu_concat.py' and 'dzliu_clean.py' library and run concat and clean
                    echo "# run this in CASA"                                             >  "${py_script}"
                    echo "sys.path.append(\"${lib_python_dzliu_dir}\")"                   >> "${py_script}"
                    echo "import dzliu_concat"                                            >> "${py_script}"
                    echo "reload(dzliu_concat)"                                           >> "${py_script}"
                    echo "import dzliu_clean"                                             >> "${py_script}"
                    echo "reload(dzliu_clean)"                                            >> "${py_script}"
                    echo ""                                                               >> "${py_script}"
                    echo "dzliu_concat.dzliu_concat(\\"                                   >> "${py_script}"
                    echo "    [\\"                                                        >> "${py_script}"
                    for (( l = 0; l < ${#list_of_continuum_ms_data[@]}; l++ )); do
                    echo "        \"${list_of_continuum_ms_data[l]}\", \\"                >> "${py_script}"
                    done
                    echo "    ], \\"                                                      >> "${py_script}"
                    echo "    \"${output_concat_ms_data}\", \\"                           >> "${py_script}"
                    echo "    )"                                                          >> "${py_script}"
                    echo ""                                                               >> "${py_script}"
                    echo "dzliu_clean.dzliu_clean(\\"                                     >> "${py_script}"
                    echo "    \"${output_concat_ms_data}\", \\"                           >> "${py_script}"
                    echo "    make_line_cube=False, \\"                                   >> "${py_script}"
                    echo "    make_continuum=True, \\"                                    >> "${py_script}"
                    echo "    max_imsize=${maximsize}, \\"                                >> "${py_script}"
                    echo "    skip_split=True, \\"                                        >> "${py_script}"
                    echo "    )"                                                          >> "${py_script}"
                    echo ""                                                               >> "${py_script}"
                    chmod +x "${py_script}"
                fi
                if [[ ! -f "${done_script}" ]] || [[ $overwrite -ge 1 ]]; then
                    chmod +x "${run_script}"
                    echo_output "Running ${run_script} > ${log_script}"
                    ./"${run_script}" > "${log_script}" 2>&1
                    if [[ ! -f "${done_script}" ]]; then
                        echo "Error! Failed to run the script \"${run_script}\"!"
                        exit 255
                    fi
                fi
                if [[ ! -f ../"output_${source_name}.cont.I.image.fits" ]]; then
                    echo_output "Copying result \"${output_concat_ms_name}_cont_clean.image.fits\" as \"output_${source_name}.cont.I.image.fits\""
                    cp "run_tclean_${output_concat_ms_name}/${output_concat_ms_name}_cont_clean.image.fits" ../"output_${source_name}.cont.I.image.fits"
                    echo_output "Copying result \"${output_concat_ms_name}_cont_clean.pb.fits\" as \"output_${source_name}.cont.I.pb.fits\""
                    cp "run_tclean_${output_concat_ms_name}/${output_concat_ms_name}_cont_clean.pb.fits" ../"output_${source_name}.cont.I.pb.fits"
                    echo_output "Copying result \"${output_concat_ms_name}_cont_clean.image.pbcor.fits\" as \"output_${source_name}.cont.I.image.pbcor.fits\""
                    cp "run_tclean_${output_concat_ms_name}/${output_concat_ms_name}_cont_clean.image.pbcor.fits" ../"output_${source_name}.cont.I.image.pbcor.fits"
                fi
            fi
            
            # cd back (out of processing dir)
            echo_output "cd ../"
            cd ../
            
        done
        
        # clean up
        if [[ $keepfiles -eq 0 ]]; then
            if ([[ -f ../"${ms_name}_cube_clean.image.fits" ]] && [[ "${width}" != "0" ]]) && \
               ([[ -f "output_${source_name}.cont.I.image.fits" ]]); then
                for (( l = 0; l < ${#list_of_run_tclean_dirs[@]}; l++ )); do
                    find "processing/${list_of_run_tclean_dirs[l]}" -type d -maxdepth 1 -print0 | xargs -0 -I % rm -rf %
                    # clean up folders but keep fits, log and txt files
                done
            fi
        fi
        
        # cd back (out of source_name dataset_dir dir)
        echo_output "cd ../../"
        cd ../../
        
    done
    
    # print message
    if [[ $i -gt 0 ]]; then
        echo ""
        echo ""
    fi
    
done


echo_output "cd ../"
cd ../


# finish
echo_output "Finished processing ALMA project ${Project_code} with $(basename ${BASH_SOURCE[0]})"
echo_output ""
echo_output ""


# 
# common data directory structure:
# Level_1_Raw
# Level_2_Calib
# Level_3_Split
# Level_4_Data_Images
# Level_4_Data_uvt
# Level_4_Run_clean
# Level_4_Run_uvfit
# Level_5_Sci
