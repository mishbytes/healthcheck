#std imports
import logging
import socket

#Fabric for ssh connections
from fabric import tasks
from fabric.api import run,env, run, execute, parallel,settings,hide
from fabric.network import disconnect_all
from fabric.exceptions import CommandTimeout,NetworkError

log = logging.getLogger(__name__)

#CONSTANTS

#Fabric setup
env.user = 'srv-sasanl-m'
#env.password = 'mypassword' #ssh password for user
# or, specify path to server private key here:
#env.key_filename = '/my/ssh_keys/id_rsa'

#When True, Fabric will run in a non-interactive mode
#This allows users to ensure a Fabric session will always terminate cleanly
#instead of blocking on user input forever when unforeseen circumstances arise.
env.abort_on_prompts=True

#a Boolean setting determining whether Fabric exits when detecting
#errors on the remote end
env.warn_only=True

def diskStatus(mount,default_timeout=30):
    #log.info(env.hosts)
    log = logging.getLogger('diskStatus()')
    status=False
    if not mount:
        log.debug('Mount is empty')
    else:
        command="ls %s" % (mount)
        #if run("ls %s" % (mount),timeout=5):
        try:
            log.info(">>>>>>>>>> Running \'%s\' on host %s  Command timeout %d seconds" % (command,env.host_string,default_timeout))
            status=False
            result = run(command,timeout=default_timeout)
            log.info(">>>>>>>>>> Finished \'%s\' on host %s  return code %d" % (command,env.host_string,result.return_code))
            if result.return_code == 0:
                status=True
        except CommandTimeout as connerr:
            log.error("Disk %s did not respond %s" % (connerr))
        except NetworkError as neterr:
            log.error("Unable to connect to %s" % (env.host_string))
            log.error(neterr)
        except SystemExit as syserror:
            log.error("exit %s" % (syserror))
            #status=False
        except Exception as err:
            log.error("Unknown Error occurred in diskStatus() %s" % (err))

    return status


def getDiskStatus(environment,hosts_list,mountpath):
    log = logging.getLogger('getDiskStatus()')
    if hosts_list:
        env.hosts = hosts_list
        env.parallel=True
        env.eagerly_disconnect=True
        with hide('everything'):
            log.info(">> BEGIN: Environment: %s Disk: %s check" %(environment,mountpath))
            disk_output = tasks.execute(diskStatus,mountpath)
            log.info(">> END: Environment: %s Disk: %s check" %(environment,mountpath))
            disconnect_all() # Call this when you are done, or get an ugly exception!
        return disk_output
    else:
        return []
