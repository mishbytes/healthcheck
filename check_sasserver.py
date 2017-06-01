#std imports
import logging
import socket
import hashlib
from datetime import datetime
import re

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

#a Boolean setting determining whether Fabric exits when detecting
#errors on the remote end
env.warn_only=True

def runsasserverstatus(scriptpath,default_timeout=30):
    #log.info(env.hosts)
    log = logging.getLogger('runsasserverstatus()')


    collect_status={}

    format_pat= re.compile(
                            r'(?:(?P<down_service_name>.*)(?=.*\sis\sNOT\sup.*$))?'
                            r'(?:(?P<up_service_name>.*)(?=.*\sis\sUP.*$))?'
                           )

    status=False
    return_code=1
    message=''
    if not scriptpath:
        log.debug('scriptpath is blank')
    else:
        command=scriptpath + ' status'
        #if run("ls %s" % (mount),timeout=5):
        try:
            log.debug(">>>>>>>>>> Running \'%s\' on host %s  Command timeout %d seconds" % (command,env.host_string,default_timeout))
            status=False
            result = run(command,timeout=default_timeout)
            log.debug(">>>>>>>>>> Finished \'%s\' on host %s  return code %d" % (command,env.host_string,result.return_code))
            return_code=result.return_code
            if return_code == 0:
                #discard message
                #status=True
                log.debug(result)
                collect_status={}
                for response in result.split('\n'):
                    log.debug("    %s" % response)
                    match_dict = format_pat.match(response)
                    if match_dict:

                        d = dict(match_dict.groupdict())
                        log.debug("    Regex groups: %s" % d)
                        if d['down_service_name']:
                            service=d['down_service_name']
                            status=False
                        elif d['up_service_name']:
                            service=d['up_service_name']
                            status=True
                        else:
                            service="sas.servers"
                            status=True
                        message=response.rstrip("\n\r")
                        service_id=hashlib.md5(env.host_string + service).hexdigest()
                        last_checked=str(datetime.now())
                        output_status={"available":status,
                                "return_code":return_code,
                                "message":message,
                                "type":"sasserver.sh",
                                "service_id":service_id,
                                "last_checked":last_checked
                                }
                        if not service in collect_status:
                            collect_status[service]={}
                        collect_status[service]=output_status
                    else:
                        log.debug("Unable to find match for \"is UP\" or \"is NOT up\" in sas.servers status command output")
                        log.debug("sas.servers command output %s" % response)
            else:
                #capture message as it may be an error message
                service="sas.servers"
                status=False
                message=result
                service_id=hashlib.md5(env.host_string + service).hexdigest()
                last_checked=str(datetime.now())
                output_status={"available":status,
                        "return_code":return_code,
                        "message":message,
                        "type":"sasserver.sh",
                        "service_id":service_id,
                        "last_checked":last_checked
                        }

        except CommandTimeout as connerr:
            message="%s did not respond" % scriptpath
            log.debug("%s did not respond %s" % (scriptpath,connerr))
        except NetworkError as neterr:
            message="Unable to connect to %s" % (env.host_string)
            log.debug("Unable to connect to %s" % (env.host_string))
            log.debug(neterr)
        except SystemExit as syserror:
            log.debug("Error-code while establising ssh connection is non-zero: %s" % str(syserror))
            #status=False
        except IOError as ioerr:
            message=str(ioerr)
            log.exception("Command failed with error %s" % (ioerr))
        except Exception as err:
            message="Unknown Error occurred when executing sasserverstatus command"
            log.debug("Unknown Error occurred when executing sasserverstatus command %s" % (err))

    return collect_status


def getsasserverstatus(environment,hosts_list,username,scriptpath,private_key='',debug=False):
    log = logging.getLogger('getsasserverstatus()')
    log.debug("Is Fabric debug enabled in configuration? %s" % debug)
    if not debug:
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    else:
        log.debug("Debug enabled")

    log.debug(hosts_list)
    if hosts_list:
        env.hosts = hosts_list
        env.parallel=True
        env.eagerly_disconnect=True
        #with hide('everything'):
        with settings(
                        hide('everything'),
                        key_filename=private_key,
                        user = username
                      ):
            log.debug(">> BEGIN: Environment: %s Command: %s check" %(environment,scriptpath))
            sasserverstatus_output = tasks.execute(runsasserverstatus,scriptpath)
            log.debug(sasserverstatus_output)
            log.debug(">> END: Environment: %s Command: %s check" %(environment,scriptpath))
            disconnect_all() # Call this when you are done, or get an ugly exception!

    #print disk_output
    return sasserverstatus_output

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    hosts=["192.168.56.201","192.168.56.202"]
    getsasserverstatus('test',hosts,'sas','/tmp/sasserver.sh',private_key='/vagrant/va73_dist/ssh_keys/id_rsa',debug=False)
