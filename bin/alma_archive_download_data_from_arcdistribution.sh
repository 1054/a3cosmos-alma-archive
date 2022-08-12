#!/bin/bash
# 
# Thanks to EU ALMA ARC Node's calibrated measurement request service, 
# we can request calibrated measurement sets from the Helpdesk. 
# This script can be used to easily download the distributed data.
# 


#list_of_urls=(
#https://almascience.eso.org/arcdistribution/preview/f4c853cc8cffeccd9c9ef4c3729bc080/
#)


# usage
if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_download_data_from_arcdistribution.sh \\"
    echo "        https://almascience.eso.org/arcdistribution/preview/url_1 \\"
    echo "        https://almascience.eso.org/arcdistribution/preview/url_2 \\"
    echo "        https://almascience.eso.org/arcdistribution/preview/url_3"
    exit
fi



# read urls from command line arguments
list_of_urls=()
i=1
while [[ $i -le $# ]]; do
    #echo "${!i}"
    if [[ "${!i}" == "http"* ]]; then
        list_of_urls+=("${!i}")
    fi
    i=$((i+1))
done
echo "Input URLs: ${list_of_urls[@]} (${#list_of_urls[@]})"


# loop urls and download them, and get actual path from a log file in it and create link
list_of_paths=()
for (( i=0; i<${#list_of_urls[@]}; i++ )); do
    
    inputurl="${list_of_urls[i]}"
    if [[ "$inputurl" != *"/" ]]; then
        inputurl="$inputurl/"
    fi
    outdir=$(echo "$inputurl" | perl -p -e 's%^(https|http)://%%g' | perl -p -e 's%/$%%g')
    skip=0
    if [[ -d "$outdir" ]]; then
        if [[ $(ls -1 "$outdir" | wc -l) -gt 0 ]]; then
            echo "Found \"$outdir\". Skip."
            skip=1
        fi
    fi
    if [[ $skip -eq 0 ]]; then
        echo "Downloading to \"$outdir\""
        wget -r -e robots=off --no-parent --reject "index.html*" --reject "robots.*" "$inputurl"
    fi


    actualpath=$(head -n 1 "$outdir/makecalms-out.txt" | perl -p -e 's%^.*/([^/]+/science_goal.uid___[^/]+/group.uid___[^/]+/member.uid___[^/]+/calibrated)/.*$%\1%g')
    #echo "$actualpath"
    list_of_paths+=("$actualpath")

    if [[ ! -d "$actualpath" ]]; then 
        echo mkdir -p "$actualpath"
        mkdir -p "$actualpath"
    fi

    list_of_tar_files=($(find "$outdir" -maxdepth 1 -mindepth 1 -type f -name "*.tar" -o -name "*.tar.gz"))
    echo "Found tar files: ${list_of_tar_files[@]} (${#list_of_tar_files[@]})"
    for (( k=0; k<${#list_of_tar_files[@]}; k++ )); do
        tarfilepath="${list_of_tar_files[k]}"
        actualname=$(basename "$tarfilepath" | perl -p -e 's%^(.+)\.(tar|tar.gz)$%\1%g')
        actualsuffix=$(basename "$tarfilepath" | perl -p -e 's%^(.+)\.(tar|tar.gz)$%\2%g')
        echo "Extracting to $actualpath/$actualname"
        if [[ ! -f "$actualpath/$actualname" ]] && [[ ! -d "$actualpath/$actualname" ]]; then
            #currentpath=$(pwd -P)
            if [[ "$actualsuffix" == "tar" ]]; then
                echo tar -xf "$tarfilepath" -C "$actualpath/"
                tar -xf "$tarfilepath" -C "$actualpath/"
            elif [[ "$actualsuffix" == "tar.gz" ]]; then
                echo tar -xzf "$tarfilepath" -C "$actualpath/"
                tar -xzf "$tarfilepath" -C "$actualpath/"
            fi
        fi
    done

done



