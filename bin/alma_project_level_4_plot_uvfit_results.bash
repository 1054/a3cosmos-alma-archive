#!/bin/bash
# 

# 20200215 dzliu: created to copy uvfit results "*.result.obj_1.txt" and make final spectrum plot

#source ~/Softwares/CASA/SETUP.bash
#source ~/Softwares/GILDAS/SETUP.bash
#source ~/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash


# read input Project_code

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_project_level_4_plot_uvfit_results.bash Project_code"
    echo "Example: "
    echo "    alma_project_level_4_plot_uvfit_results.bash 2013.1.00034.S"
    echo "Notes: "
    echo "    This code will run uv_fit for all uvt files under Level_4_Data_uvt and output catalog into Level_4_Plot_uvfit_results"
    exit
fi

Project_code="$1"

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


# check CASA
#if [[ ! -d "$HOME/Softwares/CASA" ]]; then
#    echo_error "Error! \"$HOME/Softwares/CASA\" was not found!" \
#               "Sorry, we need to put all versions of CASA under \"$HOME/Softwares/CASA/Portable/\" directory!"
#    exit 1
#fi
#if [[ ! -f "$HOME/Softwares/CASA/SETUP.bash" ]]; then
#    echo_error "Error! \"$HOME/Softwares/CASA/SETUP.bash\" was not found!" \
#               "Sorry, please ask Daizhong by emailing dzliu@mpia.de!"
#    exit 1
#fi
#casa_setup_script_path="$HOME/Softwares/CASA/SETUP.bash"


# check GNU coreutils
if [[ $(uname -s) == "Darwin" ]]; then
    if [[ $(type gln 2>/dev/null | wc -l) -eq 0 ]]; then
        echo_error "Error! We need GNU ln! Please install \"coreutils\" via MacPorts or HomeBrew!"
        exit 1
    fi
    cmd_ln=gln
else
    cmd_ln=ln
fi


# check GILDAS
if [[ $(type mapping 2>/dev/null | wc -l) -eq 0 ]]; then
    # if not executable in the command line, try to find it in "$HOME/Software/GILDAS/"
    if [[ -d "$HOME/Software/GILDAS" ]] && [[ -f "$HOME/Software/GILDAS/SETUP.bash" ]]; then
        source "$HOME/Software/GILDAS/SETUP.bash"
    elif [[ -d "$HOME/Softwares/GILDAS" ]] && [[ -f "$HOME/Softwares/GILDAS/SETUP.bash" ]] && [[ ! -d "$HOME/Software/GILDAS" ]] && [[ ! -f "$HOME/Software/GILDAS/SETUP.bash" ]]; then
        source "$HOME/Softwares/GILDAS/SETUP.bash"
    else
        # if not executable in the command line, nor in "$HOME/Software/GILDAS/", report error.
        echo_error "Error! \"mapping\" is not executable in the command line! Please check your \$PATH!"
        exit 1
    fi
fi


# check Crab.Toolkit.PdBI
if [[ $(type pdbi-uvt-go-uvfit 2>/dev/null | wc -l) -eq 0 ]]; then
    # if not executable in the command line, try to find it in "$HOME/Software/GILDAS/"
    if [[ -d "$HOME/Cloud/Github/Crab.Toolkit.PdBI" ]] && [[ -f "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash" ]]; then
        source "$HOME/Cloud/Github/Crab.Toolkit.PdBI/SETUP.bash"
    else
        # if not executable in the command line, nor in "$HOME/Software/GILDAS/", report error.
        echo_error "Error! \"pdbi-uvt-go-uvfit\" is not executable in the command line! Please check your \$PATH!"
        exit 1
    fi
fi


# check meta data table file
if [[ ! -f "meta_data_table.txt" ]]; then
    echo_error "Error! \"meta_data_table.txt\" was not found! Please run previous steps first!"
    exit 255
fi


# check Level_4_Data_uvt folder
if [[ ! -d Level_4_Data_uvt ]]; then 
    echo_error "Error! \"Level_4_Data_uvt\" does not exist! Please run previous steps first!"
    exit 255
fi


# set overwrite
overwrite=0


# read Level_4_Data_uvt/DataSet_*
list_of_datasets=($(ls -1d Level_4_Data_uvt/DataSet_* | sort -V))


# prepare Level_4_Plot_uvfit_results folder
if [[ ! -d Level_4_Plot_uvfit_results ]]; then 
    echo_output "mkdir Level_4_Plot_uvfit_results"
    mkdir Level_4_Plot_uvfit_results
fi
echo_output "cd Level_4_Plot_uvfit_results"
cd Level_4_Plot_uvfit_results


# loop datasets and run CASA split then GILDAS importuvfits
for (( i = 0; i < ${#list_of_datasets[@]}; i++ )); do
    
    DataSet_dir=$(basename ${list_of_datasets[i]})
    
    # print message
    echo_output "Now looping sources in \"$DataSet_dir\""
    
    # check Level_4_Run_uvfit subdirectories
    list_of_source_dirs=($(ls -1d ../Level_4_Run_uvfit/$DataSet_dir/* ) )
    if [[ ${#list_of_source_dirs[@]} -eq 0 ]]; then
        echo_error "Error! \"../Level_4_Run_uvfit/$DataSet_dir/\" does not contain any subdirectories?! Please run Level_4_Run_uvfit first! We will skip this dataset for now."
        continue
    fi
    
    # read source names
    list_of_unique_source_names=($(find ../Level_4_Run_uvfit/$DataSet_dir -mindepth 1 -maxdepth 1 -type d | perl -p -e 's%.*/([^/]+)%\1%g' | sort -V | uniq ) )
    if [[ ${#list_of_unique_source_names[@]} -eq 0 ]]; then
        echo_error "Error! Failed to find \"../Level_4_Run_uvfit/$DataSet_dir/*\" and get unique source names!"
        exit 255
    fi
    
    # loop list_of_unique_source_names and make dir for each source and link ms files
    for (( j = 0; j < ${#list_of_unique_source_names[@]}; j++ )); do
        source_name=${list_of_unique_source_names[j]}
        if [[ ! -d "${source_name}/$DataSet_dir" ]]; then
            echo_output mkdir -p "${source_name}/$DataSet_dir"
            mkdir -p "${source_name}/$DataSet_dir"
        fi
        
        # cd source_name dataset_dir dir
        echo_output "cd ${source_name}/$DataSet_dir"
        cd "${source_name}/$DataSet_dir"
        
        # find and loop uvfit result files
        list_of_uvt_result_files=($(ls -1 ../../../Level_4_Run_uvfit/"$DataSet_dir"/"${source_name}"/run_uvfit_"${source_name}"_spw*_width*_SP/output_point_model_fixed_pos.result.obj_1.txt))
        
        for (( k = 0; k < ${#list_of_uvt_result_files[@]}; k++ )); do
            uvfit_name=$(basename $(dirname "${list_of_uvt_result_files[k]}") ) # | perl -p -e 's/.*_(spw[0-9]+)_.*/\1/g'
            echo cp "${list_of_uvt_result_files[k]}" "./${DataSet_dir}_{uvfit_name}_point_model_fixed_pos.result.obj_1.txt"
            cp "${list_of_uvt_result_files[k]}" "./${DataSet_dir}_{uvfit_name}_point_model_fixed_pos.result.obj_1.txt"
        done
        
        # cd back (out of source_name dataset_dir dir)
        echo_output "cd ../../"
        cd ../../
        
    done
    
    # cd back
    echo_output "cd ../"
    cd ../
    
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
# Level_4_Data_uvfits
# Level_4_Data_uvt
# Level_4_Run_clean
# Level_4_Plot_uvfit_results
# Level_5_Sci
