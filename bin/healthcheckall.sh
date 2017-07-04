#!/bin/sh

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export HC_CONFIG_PATH=${BINDIR}/../conf.d/reportall.cfg

${BINDIR}/healthcheckagent.sh "$@"

exit $?
