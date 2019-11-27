#!/bin/bash
# 

# check input argument

if [[ $# -eq 0 ]]; then
    echo "Usage: "
    echo "    alma_archive_unpack_tar_files_with_verification.sh ../*.cache/*.tar -log alma_archive_unpack_tar_list.log"
    echo ""
    exit
fi

# check previous unpack progress, so that we can avoid repeating unpack same tar file.

list_of_unpacked_tar=()
list_of_unpacked_ok=()
log_of_unpacking="alma_archive_unpack_tar_list.txt"

for (( i=1; i<$#; i++ )); do
    if [[ "${!i}" == "-log" ]]; then
        j=$((i+1))
        log_of_unpacking="${!j}"
    fi
done

# check previous unpack progress, so that we can avoid repeating unpack same tar file.

if [[ -f "$log_of_unpacking" ]]; then
    list_of_unpacked_tar=($(cat "$log_of_unpacking" | grep -v "&#" | sed -e 's/^ *//g' | tr -s ' ' | cut -d ' ' -f 2))
    list_of_unpacked_ok=($(cat "$log_of_unpacking" | grep -v "&#" | sed -e 's/^ *//g' | tr -s ' ' | cut -d ' ' -f 1))
fi

list_of_tar=()
list_of_ok=()

for (( i=1; i<=$#; i++ )); do
    if [[ "${!i}" == *".tar" ]]; then
        # check already unpacked tar
        check_already_unpacked="No"
        for (( j=0; j<=${#list_of_unpacked_tar[@]}; j++ )); do
            if [[ "${!i}" == "${list_of_unpacked_tar[j]}" ]]; then
                if [[ "${list_of_unpacked_ok[j]}" == "Yes" ]]; then
                    check_already_unpacked="Yes"
                    echo "\"${!i}\" has already been unpacked successfully! skip!"
                fi
            fi
        done
        if [[ "$check_already_unpacked" == "No" ]]; then
            list_of_tar+=("${!i}")
            echo "\"${!i}\" is being unpacked ... (tar -xf \"${!i}\" -C .)"
            tar -xf "${!i}" -C .
            if [[ $? -ne 0 ]]; then
                echo "tar unsuccessful?!"
                list_of_ok+=("No")
            else
                list_of_ok+=("Yes")
            fi
        fi
    fi
done

for (( i=0; i<${#list_of_tar[@]}; i++ )); do
    if [[ $i == 0 ]] && [[ ! -f "$log_of_unpacking" ]]; then
        printf "# %-16s %-s\n" "Successful" "TarFile" > "$log_of_unpacking"
    fi
    printf "  %-16s %-s\n" "${list_of_ok[i]}" "${list_of_tar[i]}" >> "$log_of_unpacking"
done

echo ""
echo "cat \"$log_of_unpacking\""
cat "$log_of_unpacking"

