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

class HealthCheckConfig(object):

    def __init__(self,configfile,configcheck=False):
        self.configfile=configfile
        self.services=[]
        self.checkonly=configcheck
        self.logfile='logfile.log'
        self.enabled=False
        self.smtp_host=''
        self.smtp_port=25
        self.smtp_user=''
        self.smpt_password=''
        self.smtp_sender=''
        self.smtp_receiver=''
        self.env_name=''
        self.env_level=''
        self.run_interval_seconds=0
        self.run_counter=0
        self.valid=False
        self.sendemail=False
        self.email_subject='Email from HealthCheck'
        self.alert_lifetime=2*60*60 # 2 hours
        self.status_jinja2_html_template='status.html.template'
        self.logging_level=DEFAUTL_LOGGING_LEVEL
        self.ssh_private_key_filename='~/.ssh/id_rsa'
        self.getConfig()


    def getConfig(self):
        log = logging.getLogger('config.HealthCheckConfig.getConfig()')
        try:
            with open(self.configfile) as f:
                config_data=json.load(f)

            if self.checkonly:
                #Configuration Check does not run as daemon, therefore its log can be sent to console
                healthcheckLogging(default_level=self.logging_level)
                log.info("Configuration check only")
            else:
                #set get verbose and logfile options from config.json
                self.setLogOptions(config_data)
                rc=healthcheckLogging(default_level=self.logging_level,filename=self.logfile) #Write to log

        except (IOError, OSError) as e:
            log.error("Error occurred while loading json file")
            log.error(e)
            sys.exit(2)

        self.valid=self.validate(self.configfile)

        if self.valid:
            if not self.checkonly:
                self.getServices(config_data)
                healthcheckLogging(default_level=self.logging_level,filename=self.logfile)
            else:
                log.info("Configuration check only, skipped loading")
        else:
            log.debug("Configuration File is invalid")

    def valid(self):
        return self.valid

    def setLogOptions(self,config):
        for config_key in config.keys():
            if 'VERBOSE' == config_key.upper():
                if 'YES' == config[config_key].upper():
                    self.logging_level=logging.DEBUG
            elif 'LOG' == config_key.upper():
                self.logfile= config[config_key]



    def getServices(self,config):
        log = logging.getLogger('HealthCheckConfig.getServices()')
        log.debug("** Fetching Applications **")
        CONFIG_OPTIONS=['name','smtp','log','output','env','comment','run_interval_seconds','run_counter','verbose']
        CONFIG_SMTP_OPTIONS=['host','port','user','password']
        for config_key in config.keys():
            if 'NAME' == config_key.upper():
                pass
            elif 'LOG' == config_key.upper():
                self.logfile= config[config_key]
            elif 'VERBOSE' == config_key.upper():
                if 'YES' == config[config_key].upper():
                    self.logging_level=logging.DEBUG
            elif 'RUN_INTERVAL_SECONDS' == config_key.upper():
                self.run_interval_seconds= config[config_key]
            elif 'ALERT_LIFETIME' == config_key.upper():
                self.alert_lifetime= config[config_key]
            elif 'RUN_COUNTER' == config_key.upper():
                self.run_counter= config[config_key]
            elif 'STATUS_JINJA2_HTML_TEMPLATE' == config_key.upper():
                self.status_jinja2_html_template= config[config_key]
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
            elif 'SENDEMAIL' == config_key.upper():
                if 'YES' == config_key.upper():
                    self.sendemail=True
            elif 'EMAIL_SUBJECT' == config_key.upper():
                self.email_subject=config[config_key]
            elif 'ENV' == config_key.upper():
                for env_key in config[config_key]:
                    if 'NAME' == env_key.upper():
                        self.env_name=config[config_key][env_key]
                    elif 'LEVEL' == env_key.upper():
                        self.env_level=config[config_key][env_key]
                    elif 'ENABLED' == env_key.upper():
                        self.enabled=config[config_key][env_key]
                    elif 'SERVICES' == env_key.upper():
                        for service in config[config_key][env_key]:
                            if  'YES' == service["enabled"].upper():

                                for service_key in service:

                                    #convert key names to upper case
                                    service_key_upper_case=[]
                                    for k in service:
                                        service_key_upper_case.append(k.upper())
                                    log.debug("Service keys upper case %s" % service_key_upper_case)

                                    if 'APPS' == service_key.upper():
                                        for name in service[service_key]:
                                            if "SSH_PRIVATE_KEY_FILENAME" in service_key_upper_case:
                                                keyfilename=service['ssh_private_key_filename']
                                                log.debug("Private key file for ssh connection is %s " % keyfilename)
                                            else:
                                                keyfilename=''
                                            log.debug("Check debug key in %s" % service)
                                            if "DEBUG" in service_key_upper_case:
                                                if "YES" == service['debug'].upper():
                                                    debug_boolean=True
                                                    log.debug("Debug set to Yes for application %s " % name)
                                                else:
                                                    log.debug("Debug not set to YES for service %s" % name)
                                                    debug_boolean=False
                                            else:
                                                log.debug("Debug option is missing %s" % name)
                                                debug_boolean=False

                                            self.services.append(Service(self.env_name,
                                                                     self.env_level,
                                                                     name,
                                                                     service['type'],
                                                                     service['hosts'],
                                                                     service['port'],
                                                                     service['protocol'],
                                                                     service['user'],
                                                                     service['password'],
                                                                     debug=debug_boolean,
                                                                     ssh_private_key_filename=keyfilename
                                                                     ))
                                            log.debug("Added Service %s to check" % service)
                            else:
                                log.debug("Removed Service %s from check" % service)

    def validate(self,configfile):
        log = logging.getLogger('config.HealthCheckConfig.validateConfig()')
        CONFIG_TOP_KEYS=['env','log','status_jinja2_html_template']
        CONFIG_TOP_ENVKEY='ENV'
        CONFIG_ENVKEYS=['services','name','level']
        CONFIG_SERVICE_KEY='SERVICES'
        CONFIG_SERVICEKEYS=['protocol','hosts','port','user','password','apps','type','enabled']

        CONFIG_TOP_KEYCHECK_RESULT=[]
        CONFIG_ENV_KEYCHECK_RESULT=[]
        CONFIG_SERVICE_KEYCHECK_RESULT=[]

        INVALID_CONFIG_FILE=False
        FOUND_ENV=False
        FOUND_APPLICATIONS=False

        if os.path.exists(configfile):
                try:
                      log.debug("validating configuration %s" % (configfile))
                      with open(configfile) as f:
                          config = json.load(f)

                      for config_env in config.keys(): #Iterate environments in configuration file
                             """
                             In TOP section
                             """
                             if config_env.upper() == CONFIG_TOP_ENVKEY and not FOUND_ENV :
                                 log.debug("Found env key")
                                 CONFIG_TOP_KEYCHECK_RESULT.append(config_env)
                                 FOUND_ENV=True
                                 """
                                 In TOP > env
                                 """
                                 log.debug("config_env_item ----" % config[config_env])
                                 log.debug("Checking settings for Environment: %s  Level: %s" % (config[config_env]['name'],config[config_env]['level']))
                                 FOUND_APPLICATIONS=False

                                 for config_service_key in config[config_env]:
                                        """
                                        In TOP > env > 'items'
                                        """
                                        if config_service_key.lower() in CONFIG_ENVKEYS:
                                            CONFIG_ENV_KEYCHECK_RESULT.append(config_service_key)
                                            if config_service_key.upper() == CONFIG_SERVICE_KEY:
                                                #process application list
                                                """
                                                In TOP > env > 'Applications'
                                                """
                                                for services in config[config_env][config_service_key]:
                                                    #log.info(applications)
                                                    CONFIG_SERVICE_KEYCHECK_RESULT=[]
                                                    for services_key in services.keys():
                                                        if services_key in CONFIG_SERVICEKEYS:
                                                            log.debug("Application Key found %s" % services_key)
                                                            CONFIG_SERVICE_KEYCHECK_RESULT.append(services_key)

                                                    log.debug("Number of valid Application keys %d" % (len(CONFIG_SERVICEKEYS)))
                                                    log.debug("Number of Application keys found %d" % (len(CONFIG_SERVICE_KEYCHECK_RESULT)))

                                                    if not (len(CONFIG_SERVICE_KEYCHECK_RESULT) == len(CONFIG_SERVICEKEYS)):
                                                        log.debug("Number of Application keys did not match")
                                                        log.debug("*** INVALID CONFIGURATION FILE ***")
                                                        INVALID_CONFIG_FILE=True
                                                        break

                                            else:
                                                pass

                                 if not (len(CONFIG_ENV_KEYCHECK_RESULT) == len(CONFIG_ENVKEYS)):
                                     log.debug("Number of environment keys did not match")
                                     INVALID_CONFIG_FILE=True

                                 break
                             else:
                                 log.debug("Looking for env key")
                                 continue

                except Exception,e:
                       INVALID_CONFIG_FILE=True
                       log.error('Something went wrong while reading web configuration json file %s' % (configfile))
                       log.error(e,exc_info=True)
        else:
            log.error("Configuration File %s does not exist" % (configFile))

        if INVALID_CONFIG_FILE:
              log.info("Configuration check Failed")
              return False
        else:
              log.info("Configuration check Passed")
              return True

if __name__ == '__main__':
    hc_config=HealthCheckConfig('config.json',configcheck=True)
