#!/bin/bash

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

. ${BINDIR}/setpath.sh

#echo $PYTHONPATH

python "$@"
