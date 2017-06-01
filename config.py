#std libs
import logging
import json
import os
import sys

#project
from service import Service

#constants
DEFAUTL_LOGGING_LEVEL=logging.INFO

def healthcheckLogging(default_level=logging.INFO,filename=None):
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not filename == None:
        try:
            logging.basicConfig(filename=filename,level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        except (IOError, OSError) as e:
            logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            log.error(e)
            sys.exit(2)
    else:
        logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


healthcheckLogging(default_level=DEFAUTL_LOGGING_LEVEL)
#global
log = logging.getLogger(__name__)

class HealthCheckConfigStore(object):

    def __init__(self,configfile,configcheck=False):
        self.configfile=configfile
        self.services=[]
        self.checkonly=configcheck
        self.logfile='logfile.log'
        self.enabled=False
        self.smtp_host='Unknown'
        self.smtp_port=25
        self.smtp_user='Unknown'
        self.smpt_password=''
        self.smtp_sender='Unknown'
        self.smtp_receiver='Unknown'
        self.env_name='Unknown'
        self.env_level='Unknown'
        self.interval=0
        self.frequency=0
        self.valid=False
        self.email_enabled=False
        self.email_subject='Email from HealthCheck'
        self.alert_lifetime=2*60*60 # 2 hours
        self.jinja2_template='status.html.template'
        self.logging_level=DEFAUTL_LOGGING_LEVEL
        self.ssh_id_rsa_filename='~/.ssh/id_rsa'
        self.read()


    def read(self):
        log = logging.getLogger('config.HealthCheckConfig.read()')

        CONFIG_GOLDEN_OPTIONS=['log','interval','frequency','services']
        CONFIG_EMAIL_OPTIONS=['smtp','email_enabled','email_subject']
        CONFIG_OTHER_OPTIONS=['env_name','env_level','alert_lifetime','jinja2_template','verbose','version','comment']
        CONFIG_ALL_OPTIONS=CONFIG_GOLDEN_OPTIONS + CONFIG_EMAIL_OPTIONS + CONFIG_OTHER_OPTIONS

        CONFIG_SERVICES_GOLDEN_OPTIONS=['type2','service','protocol','hosts','port','user','password']
        CONFIG_SERVICES_OTHER_OPTIONS=['enabled','debug','description']
        CONFIG_SERVICES_TYPE_VALID_VALUES=['webapp','disk']
        CONFIG_SERVICES_ALL_OPTIONS= CONFIG_SERVICES_GOLDEN_OPTIONS + CONFIG_SERVICES_OTHER_OPTIONS

        if self.checkonly:
            #Configuration Check does not run as daemon, therefore its log can be sent to console
            healthcheckLogging(default_level=self.logging_level)
            log.info("Configuration check only")
        else:
            with open(self.configfile) as f:
                config=json.load(f)
                f.close()
            self.setLogOptions(config)
            healthcheckLogging(default_level=self.logging_level,filename=self.logfile) #Write to log

        self.valid=self.validate(self.configfile)

        if self.valid:
            try:
                with open(self.configfile) as f:
                    config=json.load(f)

                #Set top level properties
                for config_key in config:
                    if config_key in CONFIG_ALL_OPTIONS:
                        log.debug("Found key:pair %s:%s" % (config_key.upper(),config[config_key]))
                        if 'ENV_NAME' == config_key.upper():
                            self.env_name= config[config_key]
                        elif 'LOG' == config_key.upper():
                            self.logfile= config[config_key]
                        elif 'VERBOSE' == config_key.upper():
                            if 'YES' == config[config_key].upper():
                                self.logging_level=logging.DEBUG
                        elif 'INTERVAL' == config_key.upper():
                            self.interval= config[config_key]
                        elif 'ALERT_LIFETIME' == config_key.upper():
                            self.alert_lifetime= config[config_key]
                        elif 'FREQUENCY' == config_key.upper():
                            self.frequency= config[config_key]
                        elif 'JINJA2_TEMPLATE' == config_key.upper():
                            self.jinja2_template= config[config_key]
                        elif 'SMTP' == config_key.upper():
                            for smtp_key in config[config_key]:
                                if 'HOST' == smtp_key.upper():
                                    self.smtp_host = config[config_key][smtp_key]
                                if 'PORT' == smtp_key.upper():
                                    self.smtp_port = config[config_key][smtp_key]
                                if 'USER' == smtp_key.upper():
                                    self.smtp_user = config[config_key][smtp_key]
                                if 'PASSWORD' == smtp_key.upper():
                                    self.smtp_password = config[config_key][smtp_key]
                                if 'SENDER' == smtp_key.upper():
                                    self.smtp_sender = config[config_key][smtp_key]
                                if 'RECEIVER' == smtp_key.upper():
                                    self.smtp_receiver = config[config_key][smtp_key]
                        elif 'ENABLED' == config_key.upper():
                            if 'YES' == config_key.upper():
                                self.enabled=True
                        elif 'EMAIL_ENABLED' == config_key.upper():
                            if 'YES' == config[config_key].upper():
                                log.debug("email feature enabled")
                                self.email_enabled=True
                        elif 'EMAIL_SUBJECT' == config_key.upper():
                            self.email_subject=config[config_key]


                #Find and add services
                for services in config["services"]:

                    service_upper_case=[]
                    for k in services:
                        service_upper_case.append(k.upper())

                    for service_upcase_property in service_upper_case:
                        log.debug("upper case service properties %s " % service_upcase_property)

                    if "ENABLED" in service_upper_case:
                        if "NO" == services["enabled"].upper():
                            service_enabled=False
                        else:
                            service_enabled=True
                    else:
                        service_enabled=True

                    if "SSH_ID_RSA_FILENAME" in service_upper_case:
                        ssh_id_rsa_filename=services["ssh_id_rsa_filename"]
                        log.debug("Set non-default ssh private key  %s" % ssh_id_rsa_filename)
                    else:
                        ssh_id_rsa_filename=''

                    if "DEBUG" in service_upper_case:
                        if "YES" == services["debug"].upper():
                            debug=True
                        else:
                            debug=False
                            log.debug("Set debug to yes to enable debug logging")
                    else:
                        debug=False

                    if  service_enabled:
                        for service in services['service']:
                            self.services.append(Service(self.env_name,
                                                     self.env_level,
                                                     service,
                                                     services['type'],
                                                     services['hosts'],
                                                     services['port'],
                                                     services['protocol'],
                                                     services['user'],
                                                     services['password'],
                                                     debug=debug,
                                                     ssh_private_key_filename=ssh_id_rsa_filename
                                                     ))
                            log.debug("Added Service %s to check" % service)
                    else:
                        log.debug("Removed Service %s from check" % services)

            except (IOError, OSError) as e:
                log.error("Exception occurred while loading config file")
                log.error(e)
                sys.exit(2)



    def setLogOptions(self,config):
        for config_key in config.keys():
            if 'VERBOSE' == config_key.upper():
                if 'YES' == config[config_key].upper():
                    self.logging_level=logging.DEBUG
            elif 'LOG' == config_key.upper():
                self.logfile= config[config_key]

    def valid(self):
        return self.valid



    def validate(self,configfile):
        log = logging.getLogger('config.HealthCheckConfig.validate()')
        VALID_CONFIG_FILE=True
        CONFIG_GOLDEN_OPTIONS=['log','interval','frequency','services']
        CONFIG_SERVICES_GOLDEN_OPTIONS=['type','service','protocol','hosts','port','user','password']

        if os.path.exists(configfile):
                try:
                    log.debug("validating configuration %s" % (configfile))
                    with open(configfile) as f:
                        config = json.load(f)
                    log.debug(json.dumps(config,indent=4))
                    #check golden keys
                    CONFIG_OPTIONS=[]
                    for golden_key in CONFIG_GOLDEN_OPTIONS:
                        if not golden_key in config:
                            log.debug("Property %s is missing in config file" % golden_key)
                            VALID_CONFIG_FILE=False
                            #return False

                    if not VALID_CONFIG_FILE:
                        log.debug("Configuration check Failed")
                        return False
                    else:
                        log.debug("Config Golden keys passed")

                    for service_item in config["services"]:
                        for service_golden_key in CONFIG_SERVICES_GOLDEN_OPTIONS:
                            if not service_golden_key in service_item:
                                log.debug('key:value \"%s:value\" is missing for service %s' % (service_golden_key,service_item))
                                VALID_CONFIG_FILE=False

                    if not VALID_CONFIG_FILE:
                        log.debug("Configuration check Failed")
                        return False
                    else:
                        log.debug("Config Golden Service keys present")
                    config={}
                    log.info("Configuration check Passed")
                    return True

                except Exception,e:
                       log.error('Exception occurred while loading configuration json file %s' % (configfile))
                       log.error(e,exc_info=True)

def createLogfile(configfile):
    try:
        with open(configfile) as f:
            config=json.load(f)
        if 'log' in config:
            logfile=config['log']
            if os.path.isfile(logfile):
                if os.access(logfile, os.W_OK):
                    sys.stdout.write('Log file %s \n' % logfile)
                    healthcheckLogging(default_level=logging.INFO,filename=logfile)
                else:
                    sys.stdout.write('Write access to log %s denied\n' % logfile)
                    sys.stdout.write('Exit\n')
                    sys.exit(2)
            else:
                if not os.path.isdir(logfile):
                    if os.path.isdir(os.path.dirname(os.path.abspath(logfile))):
                        sys.stdout.write('Writing to log file %s \n' % logfile)
                        #touch file
                        with open(logfile, 'a'):
                            os.utime(logfile, None)
                    else:
                        sys.stdout.write('Log directory %s do not exist\n' % logfile)


                else:
                    sys.stdout.write('Invalid log %s\n' % logfile)
                    sys.exit(2)

        else:
            sys.stderr.write('Property log is missing\n')
            sys.exit(2)

    except (IOError, OSError) as e:
        sys.stderr.write("Following exception occurred while reading config file\n")
        sys.stderr.write(str(e)+'\n')
        sys.exit(2)

def consoleLogging(filename=None):
    if filename:
        healthcheckLogging(filename='console.log',default_level=DEFAUTL_LOGGING_LEVEL)
    else:
        healthcheckLogging(default_level=DEFAUTL_LOGGING_LEVEL)

if __name__ == '__main__':
    #hc_config=HealthCheckConfig('configv2.json',configcheck=True)
    createLogfile('configv2.json')
