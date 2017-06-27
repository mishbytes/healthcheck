#!/bin/bash

BINPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export HC_CONFIG_FILE=${BINPATH}/../conf.d/all7am.cfg
python $BINPATH/../test/getconfig.py
