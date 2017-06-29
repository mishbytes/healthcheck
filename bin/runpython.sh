#!/bin/bash

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

APPLICATION_LIB=${BINPATH}/../lib:
PYTHON_MODULES=${BINPATH}/../lib/utils/python-modules

export PYTHONPATH=${PYTHON_MODULES}/jinja2-2.9.6/lib:\
${PYTHON_MODULES}/markupsafe/lib:\
${PYTHON_MODULES}/Fabric-1.13.2/lib:\
${PYTHON_MODULES}/paramiko-1.18.2/lib:\
${PYTHON_MODULES}/ecdsa-0.13/lib:\
${PYTHON_MODULES}/pycrypto-2.6.1/lib:\
${APPLICATION_LIB}

#echo $PYTHONPATH

python "$@"
