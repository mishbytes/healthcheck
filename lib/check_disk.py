#std imports
import logging
import socket
import hashlib
import sys
from datetime import datetime

#Fabric for ssh connections
from fabric import tasks
from fabric.api import run,env, run, execute, parallel,settings,hide
from fabric.network import disconnect_all
from fabric.exceptions import CommandTimeout,NetworkError

log = logging.getLogger(__name__)

#CONSTANTS

#Fabric setup
env.user = 'sas'
#env.password = 'mypassword' #ssh password for user
# or, specify path to server private key here:
#env.key_filename = '/my/ssh_keys/id_rsa'

env.key_filename='~/.ssh/id_rsa'

#When True, Fabric will run in a non-interactive mode
#This allows users to ensure a Fabric session will always terminate cleanly
#instead of blocking on user input forever when unforeseen circumstances arise.
env.abort_on_prompts=True

env.timeout=30

#a Boolean setting determining whether Fabric exits when detecting
#errors on the remote end
env.warn_only=True

def diskStatus(environment,group,mount,default_timeout=30):
    #log.info(env.hosts)
    log = logging.getLogger('diskStatus()')
    status=False
    return_code=1
    message=''
    if not mount:
        log.debug('Mount is empty')
    else:
        command="ls %s" % (mount)
        #if run("ls %s" % (mount),timeout=5):
        try:
            log.debug(">>>>>>>>>> Running \'%s\' on host %s  Command timeout %d seconds" % (command,env.host_string,default_timeout))
            status=False
            result = run(command,timeout=default_timeout,pty=False)
            log.debug(">>>>>>>>>> Finished \'%s\' on host %s  return code %d" % (command,env.host_string,result.return_code))
            return_code=result.return_code
            if return_code == 0:
                #discard message
                status=True
            else:
                #capture message as it may be an error message
                message=result
        except (KeyboardInterrupt,SystemExit) as syserr:
            log.exception("sigint signal recieved %s" % env.host_string)
            sys.exit(1)
        except CommandTimeout as connerr:
            message="Disk %s did not respond" % mount
            log.debug("Disk %s did not respond %s" % (mount,connerr))
            log.exception(connerr)
        except NetworkError as neterr:
            message="Unable to connect to %s" % (env.host_string)
            log.debug("Unable to connect to %s" % (env.host_string))
            log.exception(neterr)

        except IOError as ioerr:
            message=str(ioerr)
            log.exception(ioerr)
        except Exception as err:
            message="Unknown Error occurred in diskStatus()"
            log.exception(err)

    service_id=hashlib.md5(env.host_string + mount).hexdigest()
    last_checked=str(datetime.now())
    output={"available":status,
            "return_code":return_code,
            "message":message,
            "type":"disk",
            "service_id":service_id,
            "last_checked":last_checked,
            "environment":environment,
            "group":group
            }
    _status={mount:output}
    return _status


def getDiskStatus(environment,group,hosts_list,username,mountpath,private_key='',debug=False):
    log = logging.getLogger('getDiskStatus()')

    log.debug("Is Fabric debug enabled in configuration? %s" % debug)
    if not debug:
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    else:
        logging.getLogger("paramiko").setLevel(logging.DEBUG)
        logging.getLogger("fabric").setLevel(logging.DEBUG)
        log.debug("Debug enabled")

    if hosts_list:
        env.hosts = hosts_list
        env.parallel=True
        env.eagerly_disconnect=True
        #with hide('everything'):
        with settings(
                        hide('everything'),
                        key_filename=private_key,
                        user = username,
                        keepalive=60,
                        timeout=60
                      ):
            log.debug(">> BEGIN: Environment: %s Disk: %s check" %(environment,mountpath))
            disk_output = tasks.execute(diskStatus,environment,group,mountpath)
            log.debug(">> END: Environment: %s Disk: %s check" %(environment,mountpath))
            disconnect_all() # Call this when you are done, or get an ugly exception!

    #print disk_output
    return disk_output

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    getDiskStatus('test','SAS Web Applications','localhost','blank','/tmp',private_key='',debug=True)
