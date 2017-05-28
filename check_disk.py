#std imports
import logging
import socket

#Fabric for ssh connections
from fabric import tasks
from fabric.api import run,env, run, execute, parallel,settings,hide
from fabric.network import disconnect_all
from fabric.exceptions import CommandTimeout,NetworkError

log = logging.getLogger(__name__)

def disableLogging():
    logging.getLogger("paramiko").setLevel(logging.WARNING)

disableLogging()
#CONSTANTS

#Fabric setup
env.user = 'sas'
#env.password = 'mypassword' #ssh password for user
# or, specify path to server private key here:
#env.key_filename = '/my/ssh_keys/id_rsa'

env.key_filename='/vagrant/va73_dist/ssh_keys/id_rsa'

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
    return_code=0
    message=''
    if not mount:
        log.debug('Mount is empty')
    else:
        command="ls %s" % (mount)
        #if run("ls %s" % (mount),timeout=5):
        try:
            log.debug(">>>>>>>>>> Running \'%s\' on host %s  Command timeout %d seconds" % (command,env.host_string,default_timeout))
            status=False
            result = run(command,timeout=default_timeout)
            log.debug(">>>>>>>>>> Finished \'%s\' on host %s  return code %d" % (command,env.host_string,result.return_code))
            return_code=result.return_code
            if return_code == 0:
                status=True
        except CommandTimeout as connerr:
            message="Disk %s did not respond" % mount
            log.debug("Disk %s did not respond %s" % (mount,connerr))
        except NetworkError as neterr:
            message="Unable to connect to %s" % (env.host_string)
            log.debug("Unable to connect to %s" % (env.host_string))
            log.debug(neterr)
        except SystemExit as syserror:
            log.debug("exit %s" % (syserror))
            #status=False
        except Exception as err:
            message="Unknown Error occurred in diskStatus()"
            log.debug("Unknown Error occurred in diskStatus() %s" % (err))

    output={"host":env.host_string,"value":status,"return_code":return_code,"message":message}
    return output


def getDiskStatus(environment,hosts_list,mountpath):
    log = logging.getLogger('getDiskStatus()')
    normalized_output={}
    normalized_output["value"]={}
    normalized_output["message"]={}
    normalized_output["return_code"]={}

    if hosts_list:
        env.hosts = hosts_list
        env.parallel=True
        env.eagerly_disconnect=True
        with hide('everything'):
            log.debug(">> BEGIN: Environment: %s Disk: %s check" %(environment,mountpath))
            disk_output = tasks.execute(diskStatus,mountpath)
            log.debug(">> END: Environment: %s Disk: %s check" %(environment,mountpath))
            disconnect_all() # Call this when you are done, or get an ugly exception!
        #normalize output
        """
        {
        "value": {'hostname1':True,
                  'hostname2':False
                 },
        "return_code": {'hostname1':0,
                        'hostname2':1
                 }
        }
        """
        for host in disk_output:
            for host_key in disk_output[host]:
                if "VALUE" == host_key.upper():
                    normalized_output["value"][host]=disk_output[host][host_key]
                elif "MESSAGE" == host_key.upper():
                    normalized_output["message"][host]=disk_output[host][host_key]
                elif "RETURN_CODE" == host_key.upper():
                    normalized_output["return_code"][host]=disk_output[host][host_key]

    return normalized_output
