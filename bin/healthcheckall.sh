#!/bin/sh

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export HC_CONFIG_PATH=${BINPATH}/../conf.d/reportall.cfg

${BINPATH}/healthcheckagent.sh "$@"

exit $?
