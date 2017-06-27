#!/bin/sh

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

export HC_CONFIG_FILE=${BINPATH}/../conf.d/all7am.cfg

${BINPATH}/healthcheckagent.sh start

echo "send full report"
