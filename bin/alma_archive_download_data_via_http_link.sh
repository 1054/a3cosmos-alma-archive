#!/bin/bash


# This script runs on Linux and MaxOS and downloads all the selected files to the current working directory in up to 5 parallel download streams.
# Should a download be aborted just run the entire script again, as partial downloads will be resumed. Please play nice with the download systems
# at the ARCs and do not increase the number of parallel streams.


if ! (command -v "wget" > /dev/null 2>&1 || command -v "curl" > /dev/null 2>&1); then
   echo "ERROR: neither 'wget' nor 'curl' are available on your computer. Please install one of them.";
   exit 1
fi

function start_session {
  if [[ $# -ge 1 ]]; then export USERNAME="$1"; else export USERNAME="anonymous"; fi #<Added><dzliu># 
  if [[ $# -ge 2 ]]; then export PASSWORD="$2"; else export PASSWORD="invalid"; fi #<Added><dzliu># 
  export AUTHENTICATION_STATUS=0
  if [[ "${USERNAME}"x == ""x ]]; then
    USERNAME="anonymous"
  fi
  if [ "${USERNAME}" != "anonymous" ]; then
    if [ "${PASSWORD}" == "invalid" ]; then
      echo ""
      echo -n "Please enter the password for ALMA account ${USERNAME}: "
      read -s PASSWORD
      echo ""
      export PASSWORD
    fi
    
    if command -v "wget" > /dev/null 2>&1; then
      LOGINCOMMAND=(wget --quiet --delete-after --no-check-certificate --auth-no-challenge --keep-session-cookies --save-cookies alma-rh-cookie.txt "--http-user=${USERNAME}" "--http-password=${PASSWORD}")
    elif command -v "curl" > /dev/null 2>&1; then
      LOGINCOMMAND=(curl -s -k -o /dev/null -c alma-rh-cookie.txt "-u" "${USERNAME}:${PASSWORD}")
    fi
    # echo "${LOGINCOMMAND[@]}" "https://almascience.nrao.edu/dataPortal/api/login"
    # $("${LOGINCOMMAND[@]}" "https://almascience.nrao.edu/dataPortal/api/login") # 20240922
    $("${LOGINCOMMAND[@]}" "https://almascience.nao.ac.jp/dataPortal/downloads/login")
    AUTHENTICATION_STATUS=$?
    if [ $AUTHENTICATION_STATUS -eq 0 ]; then
      echo "            OK: credentials accepted."
    else
      echo "            ERROR: login credentials were wrong. Error code is ${AUTHENTICATION_STATUS}"
    fi
  fi
}

function end_session {
  rm -fr alma-rh-cookie.txt
}

function download {
  # wait for some time before starting - this is to stagger the load on the server (download start-up is relatively expensive)
  sleep $[ ( $RANDOM % 10 ) + 2 ]s

  if command -v "wget" > /dev/null 2>&1; then
    DOWNLOADCOMMAND=(wget -c -q -nv --no-check-certificate --auth-no-challenge --load-cookies alma-rh-cookie.txt)
  elif command -v "curl" > /dev/null 2>&1; then
    DOWNLOADCOMMAND=(curl -C - -s -k -O -f -b alma-rh-cookie.txt)
  fi

  # 20240922
  if [[ x"$DownloadViaInterface" != x"" ]]; then
      echo "DownloadViaInterface: $DownloadViaInterface"
      DOWNLOADCOMMAND=(curl -C - -s -k -O -f -b alma-rh-cookie.txt --interface $DownloadViaInterface)
  fi

  echo "starting download of `basename $1`"
  $("${DOWNLOADCOMMAND[@]}" "$1")
  # echo "${DOWNLOADCOMMAND[@]}" "$1"
  STATUS=$?
  # echo "status ${STATUS}"
  if [ ${STATUS} -eq 0 ]; then
     echo "            succesfully downloaded `basename $1`"
     
  else
     echo "            ERROR downloading `basename $1`, error code is ${STATUS}"
  fi
}
export -f download

#echo "Downloading ${LIST} in up to 5 parallel streams. Total size is 7.9GB."
#echo "We now support resuming interrupted downloads - just re-run the script."
# tr converts spaces into newlines. Written legibly (spaces replaced by '_') we have: tr "\_"_"\\n"
# IMPORTANT. Please do not increase the parallelism. This may result in your downloads being throttled.
# Please do not split downloads of a single file into multiple parallel pieces.

if [[ $# -eq 0 ]]; then
    echo "Usage:"
    echo "    alma_archive_download_tar_with_auto_username.py http://........ --user ALMA_USER_NAME"
    exit
fi



# check system variable INPUT_USERNAME and INPUT_PASSWORD
if [[ -z "${INPUT_USERNAME}" ]]; then
    USERNAME="anonymous"
else
    USERNAME="${INPUT_USERNAME}"
fi

if [[ -z "${INPUT_PASSWORD}" ]]; then
    PASSWORD="invalid"
else
    PASSWORD="${INPUT_PASSWORD}"
fi


# read from commandline input
for (( i=1; i<=$#; i++ )); do
    if [[ "${!i}" == "--user" ]]; then
        if [[ i -lt $# ]]; then
            j=$((i+1))
            USERNAME="${!j}"
        fi
    fi
    if [[ "${!i}" == "--password" ]]; then
        if [[ i -lt $# ]]; then
            j=$((i+1))
            PASSWORD="${!j}"
        fi
    fi
done


# start session
start_session "$USERNAME" "$PASSWORD"


# if failed, check USERNAME in URL
if [[ $AUTHENTICATION_STATUS -eq 0 ]]; then
	#echo "your downloads will start shortly...."
	#echo ${LIST} | tr \  \\n | xargs -P1 -n1 -I '{}' bash -c 'download {};'
  for (( i=1; i<=$#; i++ )); do
      if [[ "${!i}" == "http"* ]]; then
          
          USERNAME_FROM_URL=$(echo "${!i}" | perl -p -e "s%http.*/requests/([a-zA-Z0-9_]+)/.*%\1%g")
          
          # get USERNAME from URL
          #if [[ x"$USERNAME_FROM_URL" != x"" ]]; then #<20210219><DZLIU># fixing issue
          if [[ x"$USERNAME_FROM_URL" != x"" ]] && [[ x"$USERNAME_FROM_URL" != x"${!i}" ]]; then
              if [[ "$USERNAME_FROM_URL" != "$USERNAME" ]]; then
                  echo "Username from the download link is $USERNAME_FROM_URL!"
                  echo "We will start the download session with this username!"
                  if [[ "$USERNAME_FROM_URL" != "anonymous" ]]; then
                      echo "Password will likely be required! Please input it when required!"
                  fi
                  end_session
                  start_session "$USERNAME_FROM_URL"
                  if [[ $AUTHENTICATION_STATUS -eq 0 ]]; then
                      echo "Error! Failed authentication!"
                      exit 255
                  else
                      USERNAME="$USERNAME_FROM_URL"
                  fi
              fi
          fi
          
          download "${!i}"
      fi
  done
fi
end_session
echo "Done."
