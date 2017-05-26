#std libs
import logging
import json
import os

def validateConfig(configFile):
        log = logging.getLogger('configValid()')
        CONFIG_TOP_KEYS=['env']
        CONFIG_TOP_ENVKEY='ENV'
        """
        env is a list [] with the following dictionary items
        """
        CONFIG_ENVKEYS=['applications','name','level']
        CONFIG_APPLICATION_KEY='APPLICATIONS'
        """
        applications is a list [] with the following dictionary items
        """
        CONFIG_APPLICATIONKEYS=['protocol','hosts','port','user','password','apps','type','enabled']


        CONFIG_TOP_KEYCHECK_RESULT=[]
        CONFIG_ENV_KEYCHECK_RESULT=[]
        CONFIG_APPLICATIONS_KEYCHECK_RESULT=[]

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
                             log.info(config_env)
                             if config_env.upper() == CONFIG_TOP_ENVKEY and not FOUND_ENV :
                                 CONFIG_TOP_KEYCHECK_RESULT.append(config_env)
                                 FOUND_ENV=True
                                 """
                                 In TOP > env
                                 """
                                 log.info("config_env_item ----" % config[config_env])
                                 log.info("Checking settings for Environment: %s  Level: %s" % (config[config_env]['name'],config[config_env]['level']))
                                 FOUND_APPLICATIONS=False

                                 for config_app_key in config[config_env]:
                                        """
                                        In TOP > env > 'items'
                                        """
                                        if config_app_key in CONFIG_ENVKEYS:
                                            CONFIG_ENV_KEYCHECK_RESULT.append(config_app_key)
                                            if config_app_key.upper() == CONFIG_APPLICATION_KEY:
                                                #process application list
                                                """
                                                In TOP > env > 'Applications'
                                                """
                                                for applications in config[config_env][config_app_key]:
                                                    #log.info(applications)
                                                    CONFIG_APPLICATIONS_KEYCHECK_RESULT=[]
                                                    for applications_key in applications.keys():
                                                        if applications_key in CONFIG_APPLICATIONKEYS:
                                                            log.info(applications_key)
                                                            CONFIG_APPLICATIONS_KEYCHECK_RESULT.append(applications_key)

                                                    log.debug("Number of valid Application keys %d" % (len(CONFIG_APPLICATIONKEYS)))
                                                    log.debug("Number of Application keys found %d" % (len(CONFIG_APPLICATIONS_KEYCHECK_RESULT)))

                                                    if not (len(CONFIG_APPLICATIONS_KEYCHECK_RESULT) == len(CONFIG_APPLICATIONKEYS)):
                                                        log.debug("Number of Application keys did not match")
                                                        log.debug("*** INVALID CONFIGURATION FILE ***")
                                                        INVALID_CONFIG_FILE=True
                                                        break

                                            else:
                                                pass

                                 if not (len(CONFIG_ENV_KEYCHECK_RESULT) == len(CONFIG_ENVKEYS)):
                                     log.debug("Number of environment keys did not match")
                                     INVALID_CONFIG_FILE=False




                                 #if INVALID_CONFIG_FILE:
                                 #      log.info("Failed to validate Environment: %s  Level: %s " % (config[config_env]['name'],config[config_env]['level']))
                                 #else:
                                        #log.info("Successfully validated Environment: %s  Level: %s " % (config[config_env]['name'],config[config_env]['level']))

                                  #ENV found, now break from IF condition
                                 break
                             else:
                                 log.debug("Looking for env key")
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
