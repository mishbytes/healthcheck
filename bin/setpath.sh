#!/bin/bash

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

APPLICATION_LIB=${BINDIR}/../lib:
PYTHON_MODULES=${BINDIR}/../lib/utils/python-modules

export PYTHONPATH=${PYTHON_MODULES}/jinja2-2.9.6/lib:\
${PYTHON_MODULES}/markupsafe/lib:\
${PYTHON_MODULES}/Fabric-1.13.2/lib:\
${PYTHON_MODULES}/paramiko-1.18.2/lib:\
${PYTHON_MODULES}/ecdsa-0.13/lib:\
${PYTHON_MODULES}/pycrypto-2.6.1/lib:\
${APPLICATION_LIB}
