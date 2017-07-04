#!/bin/bash

#https://stackoverflow.com/questions/59895/getting-the-source-directory-of-a-bash-script-from-within
BINDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

. ${BINDIR}/setpath.sh

#echo $PYTHONPATH

AGENT_CMD="python ${BINDIR}/../lib/healthcheckagent.py"
#AGENT_CMD="python ${SCRIPT_PATH}/config.py"

# Get argument
case "$1" in
   start | -start)

          $AGENT_CMD start

         ;;
   stop | -stop)

         $AGENT_CMD stop

         ;;
   status | -status)

         $AGENT_CMD status

         ;;
   restart | -restart)

         $AGENT_CMD restart

         ;;
   *)
         echo "Usage: $SCRIPT {-}{start|stop|status|restart}"
         exit 1
esac

exit 0
