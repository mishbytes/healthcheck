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
import paramiko
import fabric.version

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
env.timeout=10
env.keepalive=10

#a Boolean setting determining whether Fabric exits when detecting
#errors on the remote end
env.warn_only=True

def runsasserverstatus(scriptpath,default_timeout=30):
    #log.info(env.hosts)
    log = logging.getLogger('runsasserverstatus()')


    collect_status={}

    ignore_services=["SAS Environment Manager"]

    #When using .* expression Python 2.6 throws nothing to repeat error
    #Replace .* with .+
    format_pat= re.compile(
                            r'(?:(?P<down_service_name>.+)(?=(.+)?\sis\sNOT\sup(.+)?$))?'
                            r'(?:(?P<up_service_name>.+)(?=(.+)?\sis\sUP(.+)?$))?'
                            r'(?:(?P<started_service_name>.+)(?=(.+)?\sis\sstarted(.+)?$))?'
                            r'(?:(?P<stopped_service_name>.+)(?=(.+)?\sis\sstopped(.+)?$))?'
                      )
    #format_pat= re.compile(
    #                        r'(?:(?P<down_service_name>.*)(?=.*\sis\sNOT\sup.*$))?'
    #                        r'(?:(?P<up_service_name>.*)(?=.*\sis\sUP.*$))?'
    #                       )

    status=False
    return_code=1
    message=''
    valid_response=False
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
                    ignore_response=False
                    log.debug("    %s" % response)
                    for ignore_service in ignore_services:
                        if ignore_service in response:
                            log.debug("List of services to be ignored from report %s" % ignore_services)
                            log.debug("Response: %s" % response)
                            log.debug("Response ignored as it contains service which is in ignore list")
                            ignore_response=True

                    if ignore_response:
                        #do not proceed further if response is in ignore list
                        continue

                    match_dict = format_pat.match(response)
                    if match_dict:
                        output_line = dict(match_dict.groupdict())
                        log.debug("    Regex groups: %s" % output_line)
                        if output_line['down_service_name']:
                            service=output_line['down_service_name']
                            status=False
                            valid_response=True
                        elif output_line['up_service_name']:
                            service=output_line['up_service_name']
                            status=True
                            valid_response=True
                        elif output_line['started_service_name']:
                            service=output_line['started_service_name']
                            status=True
                            valid_response=True
                        elif output_line['stopped_service_name']:
                            service=output_line['stopped_service_name']
                            status=True
                            valid_response=True
                        else:
                            #reject response and go back to main loop
                            continue
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
                        log.debug("Unable to find match for \"is UP\" or \"is NOT up\" or \"is started\" or \"is stopped\" in sas.servers status command output")
                        log.debug("sas.servers command output %s" % response)
            else:
                #capture message as it may be an error message
                message=result
                valid_response=True


        except CommandTimeout as connerr:
            message="%s did not respond" % scriptpath
            log.debug("%s did not respond %s" % (scriptpath,connerr))
            log.exception(connerr)
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

    if not valid_response:
        collect_status={}
        service="sas.servers status"
        status=False
        service_id=hashlib.md5(env.host_string + scriptpath).hexdigest()
        last_checked=str(datetime.now())
        output_status={"available":status,
                "return_code":return_code,
                "message":message,
                "type":"sasserver.sh",
                "service_id":service_id,
                "last_checked":last_checked
                }
        if not scriptpath in collect_status:
            collect_status[scriptpath]={}
        collect_status[scriptpath]=output_status

    return collect_status


def getsasserverstatus(environment,hosts_list,username,scriptpath,private_key='',debug=False):
    log = logging.getLogger('getsasserverstatus()')
    log.debug("Is Fabric debug enabled in configuration? %s" % debug)
    sasserverstatus_output={}
    if not debug:
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    else:
        logging.getLogger("paramiko").setLevel(logging.DEBUG)

    log.debug(hosts_list)
    log.debug("Paramiko Version: %s" % paramiko.__version__)
    log.debug("Fabric Version: %s   " % fabric.version.get_version())
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
            log.debug(">> BEGIN: Environment: %s Command: %s check" %(environment,scriptpath))
            sasserverstatus_output = tasks.execute(runsasserverstatus,scriptpath)
            log.debug(sasserverstatus_output)
            log.debug(">> END: Environment: %s Command: %s check" %(environment,scriptpath))
            disconnect_all() # Call this when you are done, or get an ugly exception!

    #print disk_output
    return sasserverstatus_output

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    hosts=["192.168.56.201"]
    getsasserverstatus('test',hosts,'sas','/tmp/sasserver.sh',private_key='/vagrant/va73_dist/ssh_keys/id_rsa',debug=True)
