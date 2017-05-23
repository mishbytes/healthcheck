"""
__appname__='healthcheck'
__version__='1.0.0'
"""

__appname__='healthcheck'
__version__='1.0.0'


#standard python libraies
import sys
import getopt
import os
import socket
import logging
import json
from datetime import datetime

#Fabric for ssh connections

from fabric import tasks
from fabric.api import run,env, run, execute, parallel,settings,hide
from fabric.network import disconnect_all
from fabric.exceptions import CommandTimeout,NetworkError


#Fabric setup
env.user = 'sas'
#env.password = 'mypassword' #ssh password for user
# or, specify path to server private key here:
env.key_filename = '/vagrant/va73_dist/ssh_keys/id_rsa'

#When True, Fabric will run in a non-interactive mode
#This allows users to ensure a Fabric session will always terminate cleanly
#instead of blocking on user input forever when unforeseen circumstances arise.
env.abort_on_prompts=True

#a Boolean setting determining whether Fabric exits when detecting
#errors on the remote end
env.warn_only=True

def setupLogging(default_level=logging.INFO):
    logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def disableParamikoLogging():
    logging.getLogger("paramiko").setLevel(logging.WARNING)

disableParamikoLogging()

def getHostName():
    if socket.gethostname().find('.')>=0:
        name=socket.gethostname()
    else:
        try:
            name=socket.gethostbyaddr(socket.gethostname())[0]
        except socket.gaierror:
            name=socket.gethostname()
    return name

def configValid(configFile):
        log = logging.getLogger('configValid()')
        CONFIG_LEVEL1_MUST_KEYS=['env']
        CONFIG_LEVEL2_MUST_KEYS=['applications']
        CONFIG_LEVEL3_MUST_KEYS=['protocol','hosts','port','user','password','apps','type','enabled']
        CONFIG_KEY_FOUND=[]
        INVALID_CONFIG_FILE=False
        FOUND_ENV=False
        FOUND_APPLICATIONS=False

        if os.path.exists(configFile):

                try:
                      log.info("Validating configuration file %s" % (configFile))
                      with open(configFile) as f:
                          config = json.load(f)

                      for config_env in config.keys(): #Iterate environments in configuration file
                             """
                             In TOP section
                             """

                             if config_env in CONFIG_LEVEL1_MUST_KEYS and not FOUND_ENV :
                                   FOUND_ENV=True
                                   for config_env_item in config[config_env]: #Iterate Environment attributes
                                         """
                                         In TOP > env
                                         """
                                         log.debug("Checking settings for Environment: %s  Level: %s" % (config_env_item['name'],config_env_item['level']))
                                         FOUND_APPLICATIONS=False
                                         for config_env_key in config_env_item:
                                                """
                                                In TOP > env > 'environment name'
                                                """

                                                if config_env_key in CONFIG_LEVEL2_MUST_KEYS and not FOUND_APPLICATIONS: #Look for 'Applications' key
                                                      """
                                                      In TOP > env > 'environment name' > Applications
                                                      """
                                                      FOUND_APPLICATIONS=True #Key found
                                                      for config_env_applications_key in config_env_item[config_env_key]:
                                                            """
                                                            In TOP > env > 'environment name' > Applications > values'
                                                            """
                                                            log.debug("Application ** %s **" % (config_env_applications_key['Description']))

                                                            """
                                                            Check if 'must' keys exist in settings - if not then break
                                                            """
                                                            for key in config_env_applications_key: #Iterate each key in settings
                                                                  if key in CONFIG_LEVEL3_MUST_KEYS:
                                                                        CONFIG_KEY_FOUND.append(key)

                                                            log.debug("Number of valid keys %d" % (len(CONFIG_LEVEL3_MUST_KEYS)))
                                                            log.debug("Number of keys found %d" % (len(CONFIG_KEY_FOUND)))

                                                            """
                                                            if atleast one 'must' keys not found then break from the loop
                                                            and declare configuration file as invalid
                                                            """
                                                            if not (len(CONFIG_KEY_FOUND) == len(CONFIG_LEVEL3_MUST_KEYS)):
                                                                  log.debug("Number of keys did not match")
                                                                  log.debug("*** INVALID CONFIGURATION FILE ***")
                                                                  INVALID_CONFIG_FILE=True
                                                                  break
                                                            else:
                                                                log.debug("Number of keys matched")

                                                            CONFIG_KEY_FOUND=[]

                                                else:
                                                      continue
                                         if INVALID_CONFIG_FILE:
                                               log.debug("Failed to validate Environment: %s  Level: %s " % (config_env_item['name'],config_env_item['level']))
                                         else:
                                               log.debug("Successfully validated Environment: %s  Level: %s " % (config_env_item['name'],config_env_item['level']))
                                   break
                             else:
                                   continue

                except Exception,e:
                       INVALID_CONFIG_FILE=True
                       log.error('Something went wrong while reading web configuration json file %s' % (configFile))
                       log.error(e,exc_info=True)
        else:
            log.error("Configuration File %s does not exist" % (configFile))

        if INVALID_CONFIG_FILE:
              log.info("Configuration File check Failed")
              return False
        else:
              log.info("Configuration File check Passed")
              return True

class HealthCheckApplication(object):
    def __init__(self,environment,level,name,type,hosts,port,protocol):
        self.type=type
        self.environment=environment
        self.level=environment
        self.name=name
        self.protocol=protocol
        self.hosts=hosts
        self.port=port
        self.timeoutseconds=30

class HealthCheckStatus(object):
    def __init__(self,hosts,application,application_type,type,value,timestamp,message,errormessage):
        self.application=application
        self.application_type=application_type
        self.type=type
        self.value=value
        self.message=message
        self.errormessage=errormessage
        self.timestamp=timestamp
        self.hosts=hosts

    def asDict(self):
        _dict_status={}
        _dict_status["hosts"]=self.hosts
        _dict_status["application_type"]=self.application_type
        _dict_status["application"]=self.application
        _dict_status["type"]=self.type
        _dict_status["value"]=self.value
        _dict_status["message"]=self.message
        _dict_status["errormessage"]=self.errormessage
        _dict_status["timestamp"]=self.timestamp
        return _dict_status

class HealthCheckConfig(object):

    def __init__(self,configFile):
        log = logging.getLogger('HealthCheckConfig')
        self.configFilename=configFile
        self.applications=[]
        if configValid(configFile):
            with open(configFile) as f:
                config_data=json.load(f)
                self.initialize(config_data)

    def initialize(self,config):
        log = logging.getLogger('HealthCheckConfig.initialize()')
        log.debug("** HealthCheck intialization started **")
        for config_key in config:
            if config_key == 'env':
                for environment in config[config_key]:
                    if environment['enabled'].upper() == 'YES': #Check if Environment check is enabled in Configuraiton file
                        for environment_key in environment:
                                if environment_key == 'applications':
                                    for application in environment[environment_key]:
                                        if application["enabled"].upper() == 'YES': #Check if Application check is enabled in Configuraiton file
                                            for name in application['apps']:
                                                self.applications.append(HealthCheckApplication(environment['name'],
                                                                         environment['level'],
                                                                         name,
                                                                         application['type'],
                                                                         application['hosts'],
                                                                         application['port'],
                                                                         application['protocol']
                                                                         ))
                                        else:
                                            log.debug("Skipping Application %s in environment %s because it is not enabled in configuration file" % (application["Description"],environment["name"]))
                    else:
                        log.debug("** Environment %s skipped **" % (environment["name"]))
        log.debug("** HealthCheck intialization completed **")




class FabricException(Exception):
    def __init__(self, message, result):
        Exception.__init__(self, message)
        self.result = result

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
            result = run(command,timeout=default_timeout)
            log.info(">>>>>>>>>> Finished \'%s\' on host %s  return code %d" % (command,env.host_string,result.return_code))
            if result.return_code == 0:
                status=True
        except CommandTimeout as connerr:
            log.error("Disk %s did not respond %s" % (connerr))
        except NetworkError as neterr:
            log.error("Unable to connect to %s" % (env.host_string))
            log.error(neterr)
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

class Healthcheck(object):
        def __init__(self,configFile):
            self.status_dict={}
            self.status_dict["hostname"]=getHostName()
            self.status_dict["timestamp"]=str(datetime.now())
            self.status_dict["output"]=[]
            self.status_output=[]
            self.hc_config=HealthCheckConfig(configFile)

        def addStatus(self,data):
            self.status_dict["output"].append(data)

        def getStatus(self):
            log = logging.getLogger('Healthcheck.getStatus()')
            status_output=[]
            if self.hc_config.applications:
                log.info("** Status check begins **")
                for application in self.hc_config.applications:
                    log.debug("Environment: %s Application: %s Hosts: %s" % (application.environment,
                                                                             application.name,application.hosts))
                    if application.type.upper() == 'WEBAPP':
                        #log.debug("Environment: %s Application: %s" % (application.environment,application.name))
                        self.addStatus(HealthCheckStatus(application.hosts,
                                                            application.name,
                                                            application.type,
                                                            'Availability',
                                                            'True',
                                                            str(datetime.now()),
                                                            'Success',
                                                            '200 OK').asDict())
                    elif application.type.upper() == 'DISK':
                        status_value=getDiskStatus(application.environment,application.hosts,application.name)
                        self.addStatus(HealthCheckStatus(application.hosts,
                                                            application.name,
                                                            application.type,
                                                            'Availability',
                                                            status_value,
                                                            str(datetime.now()),
                                                            '',
                                                            '').asDict())
                    else:
                        log.info("Invalid Application Type")
                log.info("** Status check ends **")
            else:
                log.info("No applications loaded")

        def save(self,type="",filename=''):
            log = logging.getLogger('Healthcheck.save()')
            TYPE_VALID_VALUES=["log","file"]
            if self.status_dict:
                if type in TYPE_VALID_VALUES:
                    if type.upper() == 'LOG':
                        log.info(json.dumps(self.status_dict,indent=4))
                    elif type.upper() == 'FILE':
                        if filename:
                            log.info('Writing status to File %s' % (filename))
                            try:
                               with open(filename, 'w') as f:
                                   json.dump(self.status_dict, f,indent=6)
                            except IOError, msg:
                               log.error("Error: can\'t write to file %s" % (filename))
                               log.error(msg)
                            else:
                               log.info("Written content in %s successfully" % (filename))
                        else:
                            log.debug("Filename is empty")
                else:
                    log.debug("Save disabled")
            else:
                log.info("Empty status, nothing to save")


def help():
  help = """
        -h --help                               Help
        -config -c my.config                    Configuration File
        -logconfig -c logging.properties        Log configuration File
      """
  print help


def main(argv):
    fname = ""
    out=""
    config=""
    try:
        options, remainders = getopt.getopt(argv, 'h',["config=","out="])
        if not options:
            help()
            sys.exit()
    except getopt.GetoptError as err:
        print err
        help()
        sys.exit(2)
    for opt, arg in options:
        if opt in ("-h", "--help"):
            help()
            sys.exit()
        elif opt in ("--config"):
            config=os.path.abspath(arg)
        elif opt in ("--out"):
            out = os.path.abspath(arg)
        else:
            usage()
            sys.exit(2)

    hostname=getHostName()
    print "Host: %s running %s version: %s" % (hostname,__appname__,__version__)
    #print options
    print "-config %s  -out %s " % (config,out)
    if (config and out):
        setupLogging(default_level=logging.INFO)
        log = logging.getLogger('healthcheck')
        hc=Healthcheck(config)
        hc.getStatus()
        hc.save(type='file',filename=out)
    else:
      usage()
      sys.exit(2)
########################################

if __name__ == "__main__":
    main(sys.argv[1:])
