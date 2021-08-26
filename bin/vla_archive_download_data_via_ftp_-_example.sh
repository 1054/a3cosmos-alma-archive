#!/bin/bash
# 

#source ~/Cloud/GitLab/Crab.Toolkit.System/SETUP.bash

list_of_sbs=(\
13B-289.sb24960057.eb25237743.56540.16448928241 \
13B-289.sb24815807.eb25239879.56541.120912488426 \
13B-289.sb24959539.eb25319335.56542.689519375 \
13B-289.sb24818075.eb25328089.56544.09201956019 \
13B-289.sb24815621.eb25386254.56546.07604925926 \
13B-289.sb24817500.eb25437464.56547.04215003472 \
13B-289.sb24819037.eb25440353.56548.039455370366 \
13B-289.sb24214184.eb25496909.56549.9197524537 \
13B-289.sb24817881.eb25498534.56551.01052434028 \
13B-289.sb24815478.eb25498536.56551.13523325232 \
13B-289.sb24815288.eb25516397.56551.9651859375 \
13B-289.sb24815109.eb25576213.56552.962636585646 \
13B-289.sb24960203.eb25675150.56554.08539194445 \
13B-289.sb24817703.eb25765209.56557.807578101856 \
)


i_downloaded=0 # Oct 21, 2020
i_downloaded=5 # Dec 10, 2020
for (( i=$i_downloaded; i<${#list_of_sbs[@]}; i++ )); do
    this_sb="${list_of_sbs[i]}"
    if [[ ! -f "${this_sb}/SysPower.bin" ]]; then
        mkdir -p "${this_sb}/"
        cd "${this_sb}/"
        echo "pwd \"$(pwd)\""
        #echo "wgetsite \"ftp://ftp.aoc.nrao.edu/e2earchive/${this_sb}/\" | tee \"../log_downloading_${this_sb}.txt\""
        #wgetsite "ftp://ftp.aoc.nrao.edu/e2earchive/${this_sb}/" | tee "../log_downloading_${this_sb}.txt"
        #wgetsite -c --limit-rate 1000k
        echo "wget -r -e robots=off --no-parent --no-host --cut-dirs=2 --reject \"index.html*\" --reject \"robots.*\" \"ftp://ftp.aoc.nrao.edu/e2earchive/${this_sb}/\" > \"../log_downloading_${this_sb}.txt\""
        wget -r -e robots=off --no-parent --no-host --cut-dirs=2 --reject "index.html*" --reject "robots.*" "ftp://ftp.aoc.nrao.edu/e2earchive/${this_sb}/" > "../log_downloading_${this_sb}.txt"
        cd "../"
    else
        echo "Found \"${this_sb}/SysPower.bin\""
    fi
done


