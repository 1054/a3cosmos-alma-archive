#!/bin/bash
# 

if [[ $# -lt 1 ]]; then
    echo "Usage: alma_archive_run_tclean_for_continuum.sh \"XXX.ms\""
    exit
fi

echo casa --no-gui --log2term -c "sys.path.append(\"$(dirname ${BASH_SOURCE[0]})\"); import alma_archive_run_tclean_for_continuum; alma_archive_run_tclean_for_continuum.go(\"$1\")"
casa --no-gui --log2term -c "sys.path.append(\"$(dirname ${BASH_SOURCE[0]})\"); import alma_archive_run_tclean_for_continuum; alma_archive_run_tclean_for_continuum.go(\"$1\")"
