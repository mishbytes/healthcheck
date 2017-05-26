"""
__appname__='healthcheck'
__version__='1.0.0'
"""

__HEALTHCHECKNAME__='healthcheck'
__HEALTHCHECKVERSION__='1.0.0'

#standard python libraies
import sys
import signal
import getopt
import os
import socket
import logging
import json
import time
from datetime import datetime


#project
from utils.pidfile import PidFile
from utils.daemon import Daemon
from check_sas import sasLogon
from check_disk import getDiskStatus
from config import validateConfig

#CONSTANTS
DEFAULT_CONFIG_FILE='config.json'
DEFAUTL_LOGGING_LEVEL='INFO'
DEFAUTL_LOG_FILENAME='healthcheck.log'
START_COMMANDS = ['start', 'restart']
DEFAULT_KILL_TIMEOUT=10

#PATHs
PROJECT_DIR=os.path.dirname(os.path.abspath(__file__))
PID_NAME = __file__
PID_DIR = PROJECT_DIR
PROJECT_LOG=PROJECT_DIR + '/' + DEFAUTL_LOG_FILENAME


#Interval
#DEFAULT_CHECK_INTERVAL=1*60*60 #1 Hour
DEFAULT_CHECK_INTERVAL=120 #Seconds
DEFAULT_CHECK_FREQUENCY=1


def setupLogging(default_level=logging.INFO,filename=None):
    if 'debug' == DEFAUTL_LOGGING_LEVEL.lower():
        default_level=logging.DEBUG
    elif 'warn' == DEFAUTL_LOGGING_LEVEL.lower():
        default_level=logging.WARN
    elif 'error' == DEFAUTL_LOGGING_LEVEL.lower():
        default_level=logging.ERROR
    else:
        default_level=logging.INFO
    if not filename == None:
        # Remove all handlers associated with the root logger object.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=filename,level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    log = logging.getLogger(__name__)



setupLogging(default_level=DEFAUTL_LOGGING_LEVEL)
#global
log = logging.getLogger(__name__)


def disableLogging():
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("utils").setLevel(logging.WARNING)
    logging.getLogger("config").setLevel(logging.WARNING)

disableLogging()

def getHostName():
    if socket.gethostname().find('.')>=0:
        name=socket.gethostname()
    else:
        try:
            name=socket.gethostbyaddr(socket.gethostname())[0]
        except socket.gaierror:
            name=socket.gethostname()
    return name


class HealthCheckApplication(object):
    def __init__(self,environment,level,name,type,hosts,port,protocol,user,password):
        self.type=type
        self.environment=environment
        self.level=environment
        self.name=name
        self.protocol=protocol
        self.hosts=hosts
        self.port=port
        self.user=user
        self.password=password
        self.timeoutseconds=30

class HealthCheckStatus(object):
    def __init__(self,hosts,application,application_type,type,value,timestamp,message):
        self.application=application
        self.application_type=application_type
        self.type=type
        self.value=value
        self.message=message
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
        _dict_status["timestamp"]=self.timestamp
        return _dict_status

class HealthCheckConfig(object):

    def __init__(self,configFile,configCheck=False):
        log = logging.getLogger('HealthCheckConfig')
        self.configFilename=configFile
        self.applications=[]
        self.config_check=configCheck
        self.logfile='logfile.log'
        self.enabled=False
        self.outputfile='output.txt'
        self.smpt_host=None
        self.smpt_port=None
        self.smpt_user=None
        self.smpt_password=None
        self.env_name=''
        self.env_level=''

        if self.config_check:
            log.info("configuration check requested")
        self.config_valid=validateConfig(configFile)
        if self.config_valid and not self.config_check:
            with open(configFile) as f:
                config_data=json.load(f)
                self.loadApplications(config_data)
                setupLogging(default_level=DEFAUTL_LOGGING_LEVEL,filename=self.logfile)

    def isConfigValid(self):
        return self.config_valid

    def loadApplications_disabled(self,config):
        log = logging.getLogger('HealthCheckConfig.loadApplications()')
        log.debug("** Fetching Applications **")
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
                                                                         application['protocol'],
                                                                         application['user'],
                                                                         application['password']
                                                                         ))
                                        else:
                                            log.info("Skipping Application %s in environment %s because it is not enabled in configuration file" % (application["Description"],environment["name"]))
                    else:
                        log.info("** Environment %s skipped **" % (environment["name"]))
        log.debug("** HealthCheck intialization completed **")

    def loadApplications(self,config):
        log = logging.getLogger('HealthCheckConfig.loadApplications()')
        log.debug("** Fetching Applications **")
        CONFIG_OPTIONS=['name','smtp','log','output','env''comment']
        CONFIG_SMTP_OPTIONS=['host','port','user','password']
        for config_key in config.keys():
            if 'NAME' == config_key.upper():
                pass
            elif 'LOG' == config_key.upper():
                self.logfile=PROJECT_DIR + '/' + config[config_key]
            elif 'OUTPUT' == config_key.upper():
                self.outputfile=PROJECT_DIR + '/' + config[config_key]
            elif 'SMTP' == config_key.upper():
                for smtp_key in config[config_key]:
                    if 'HOST' == smtp_key.upper():
                        self.smpt_host = config[config_key][smtp_key]
                    if 'PORT' == smtp_key.upper():
                        self.smpt_port = config[config_key][smtp_key]
                    if 'USER' == smtp_key.upper():
                        self.smpt_user = config[config_key][smtp_key]
                    if 'PASSWORD' == smtp_key.upper():
                        self.smpt_password = config[config_key][smtp_key]
            elif 'ENABLED' == config_key.upper():
                if 'YES' == config_key.upper():
                    self.enabled=True
            elif 'ENV' == config_key.upper():
                for env_key in config[config_key]:
                    if 'NAME' == env_key.upper():
                        self.env_name=config[config_key][env_key]
                    elif 'LEVEL' == env_key.upper():
                        self.env_level=config[config_key][env_key]
                    elif 'ENABLED' == env_key.upper():
                        self.enabled=config[config_key][env_key]
                    elif 'APPLICATIONS' == env_key.upper():
                        for application in config[config_key][env_key]:
                            if  'YES' == application["enabled"].upper():
                                for application_key in application:
                                    if 'apps' == application_key.upper():
                                        for name in application[application_key]:
                                            self.applications.append(HealthCheckApplication(self.env_name,
                                                                     self.env_level,
                                                                     name,
                                                                     application['type'],
                                                                     application['hosts'],
                                                                     application['port'],
                                                                     application['protocol'],
                                                                     application['user'],
                                                                     application['password']
                                                                     ))
                                log.debug("Added Application %s to check" % application)
                            else:
                                log.debug("Removed Application %s from check" % application)

class Healthcheck(object):
    
        def __init__(self,configFile,configCheck=False):
            self.status_dict={}
            self.status_dict["hostname"]="myhost"
            self.status_dict["timestamp"]=str(datetime.now())
            self.status_dict["output"]=[]
            self.status_output=[]
            self.running=False
            self.start_event=True
            self.hc_config=HealthCheckConfig(configFile,configCheck=configCheck)
            if self.hc_config and self.hc_config.config_valid:
                log = logging.getLogger("Healthcheck")
                log.info('Healthcheck Initialized')


        def addStatus(self,data):
            self.status_dict["output"].append(data)

        def isConfigValid(self):
            return self.hc_config.isConfigValid()

        def start(self):
            if self.start_event:
                self.running=True
                log = logging.getLogger('Healthcheck.getStatus()')
                status_output=[]
                try:
                    if self.hc_config.applications:
                        log.info("** Status check begins **")
                        for application in self.hc_config.applications:
                            log.debug("Environment: %s Application: %s Hosts: %s" % (application.environment,
                                                                                     application.name,application.hosts))
                            if application.type.upper() == 'WEBAPP':
                                #log.debug("Environment: %s Application: %s" % (application.environment,application.name))
                                #sasLogon(environment,protocol,host,port,application,user,password)
                                response=sasLogon(application.environment,application.protocol,application.hosts,application.port,application.name,application.user,application.password)
                                self.addStatus(HealthCheckStatus(application.hosts,
                                                                    application.name,
                                                                    application.type,
                                                                    'Availability',
                                                                    response["value"],
                                                                    str(datetime.now()),
                                                                    response["message"]).asDict())
                            elif application.type.upper() == 'DISK':
                                response=getDiskStatus(application.environment,application.hosts,application.name)
                                self.addStatus(HealthCheckStatus(application.hosts,
                                                                    application.name,
                                                                    application.type,
                                                                    'Availability',
                                                                    response,
                                                                    str(datetime.now()),
                                                                    '').asDict())
                            else:
                                log.info("Invalid Application Type")
                        log.info("** Status check ends **")
                    else:
                        log.info("No applications loaded")
                except Exception as e:
                    log.info("Exception occurred")
            else:
                pass


        def stop(self):
            self.start_event=False
            #self.running=False
            #raise SystemExit
            #sys.exit(0)

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

        def showAlerts(self):
            log = logging.getLogger('Healthcheck.showAlerts()')
            self.running=True
            if self.status_dict:
                for status_property in self.status_dict:
                    if status_property.upper() == "OUTPUT":
                        for output in self.status_dict["output"]:
                            if isinstance(output["value"], dict):
                                for dict_key, dict_value in output["value"].iteritems():
                                    if not dict_value:
                                        log.info("%s:%s is unavailable via host %s" % (output["application_type"],output["application"],dict_key))
                            elif not output["value"]:
                                log.info("%s:%s is unavailable via host %s" % (output["application_type"],output["application"],output["hosts"]))

                                #log.info(output["application"])

            else:
                log.info("Empty status, nothing to save")




class HealthcheckAgent(Daemon):
    log = logging.getLogger('HealthCheckAgent')
    def __init__(self, pidfile):
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.start_event=True
        self.healthcheck = None
        self.check_interval = DEFAULT_CHECK_INTERVAL
        self.check_frequency = DEFAULT_CHECK_FREQUENCY
        self.config_file=''

    def _handle_sigterm(self, signum, frame):
        """Handles SIGTERM and SIGINT, which gracefully stops the agent."""
        log = logging.getLogger('HealthCheckAgent._handle_sigterm()')
        log.info("Caught sigterm. Stopping run loop.")
        self.run_forever = False
        self.start_event = False
        if self.healthcheck:
            self.healthcheck.stop()
            #log.info("waiting for current healthcheck to finish")
            t_end = time.time() + 1*60 #Two minutes
            while time.time() < t_end:
                if self.healthcheck.running:
                    t_left = t_end - time.time()
                    log.info("Waiting for current healthcheck to finish Time left %d of %d seconds" % (t_left,60) )
                    time.sleep(5) #Sleep for 5 seconds
                    continue
                else:
                    log.info("Current healthcheck stopped")
                    break
        if self.healthcheck.running:
            log.info("Timed out waiting for current healthcheck to finish")
        raise SystemExit

    @classmethod
    def info(cls, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return "Info"

    def run(self, config='config.json'):
        log = logging.getLogger("HealcheckAgent.run()")
        """Main loop of the healthcheck"""
        # Gracefully exit on sigterm
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        if config:
            config_file_abs_path=PROJECT_DIR + '/' + config
            self.healthcheck=Healthcheck(config_file_abs_path)
            #self.healthcheck=Healthcheck(config)

        while self.run_forever:
            i=1
            while i <= self.check_frequency:
                if self.run_forever:
                    if i > 1 :
                        t_end=time.time() + self.check_interval
                        while time.time() < t_end:
                            if self.run_forever:
                                log.info("waiting to run next event %s" % self.healthcheck.start_event)
                                time.sleep(DEFAULT_KILL_TIMEOUT)
                            else:
                                break

                    if self.healthcheck:
                        log.info("Starting HealthCheck instance# %d" % i)
                        try:
                            self.healthcheck.start()
                            self.healthcheck.showAlerts()
                            self.healthcheck.running=False
                            log.info("Finished HealthCheck instance# %d" % i)
                        finally:
                            self.healthcheck.running=False
                    else:
                        log.error("Unable to to run HealthCheck")
                    i+=1

                else:
                    break

            # Explicitly kill the process, because it might be running as a daemon.
            log.info("Exiting. Bye bye.")
            sys.exit(0)


def main(argv):
    log = logging.getLogger('healthcheck')
    COMMANDS_AGENT = [
        'start',
        'stop',
        'restart',
        'status'
    ]

    COMMANDS_NO_AGENT = [
        'info',
        'check',
        'configcheck'
    ]

    COMMANDS = COMMANDS_AGENT + COMMANDS_NO_AGENT

    if len(sys.argv[1:]) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = sys.argv[1]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    if command in COMMANDS_AGENT:
        hcagent = HealthcheckAgent(PidFile(PID_NAME, PID_DIR).get_path())

    if command in START_COMMANDS:
        #log.info('Healthcheck Agent version 1.0')
        pass

    if 'start' == command:
        hcagent.start()
        #agent.start()

    elif 'stop' == command:
        log.info('Stopping Agent')
        hcagent.stop()
        #agent.stop()

    elif 'restart' == command:
        log.info('Restarting Agent')
        hcagent.restart()

    elif 'status' == command:
        log.info('Checking Status')
        hcagent.status()

    elif 'info' == command:
        return "Health Check Version: 1.0"

    elif 'configcheck' == command or 'configtest' == command:
        log.info("Validating config")
        config_file_abs_path=PROJECT_DIR + '/config.json'
        log.info("Reading configuration from %s" % config_file_abs_path)
        healthcheck=Healthcheck(config_file_abs_path,configCheck=True)
        if healthcheck.isConfigValid():
            print "Configuration file %s is valid" % config_file_abs_path
        else:
            print "Configuration file %s is invalid" % config_file_abs_path

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[0:]))
    except StandardError:
        # Try our best to log the error.
        try:
            log.exception("Uncaught error running the Health Check Agent")
        except Exception:
            pass
        raise
