#std libs
import logging
import json
import os

def validateConfig(configFile):
        log = logging.getLogger('configValid()')
        CONFIG_LEVEL1_MUST_KEYS=['env']
        CONFIG_LEVEL1_ENV_KEY='ENV'
        """
        env is a list [] with the following dictionary items
        """
        CONFIG_LEVEL2_MUST_KEYS=['applications','name','level']
        CONFIG_LEVEL2_APPLICATION_KEY='APPLICATIONS'
        """
        applications is a list [] with the following dictionary items
        """
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
                             log.info(config_env)
                             if config_env.upper() == CONFIG_LEVEL1_ENV_KEY and not FOUND_ENV :
                                 FOUND_ENV=True
                                 """
                                 In TOP > env
                                 """
                                 log.info("config_env_item ----" % config[config_env])
                                 log.info("Checking settings for Environment: %s  Level: %s" % (config[config_env]['name'],config[config_env]['level']))
                                 FOUND_APPLICATIONS=False
                                 log.info(config[config_env])
                                 for config_env_key in config[config_env]:
                                        """
                                        In TOP > env > 'environment name'
                                        """
                                        log.info(config_env_key)
                                        if config_env_key == CONFIG_LEVEL2_APPLICATION_KEY and not FOUND_APPLICATIONS: #Look for 'Applications' key
                                              """
                                              In TOP > env > 'environment name' > Applications
                                              """
                                              FOUND_APPLICATIONS=True #Key found
                                              log.info(config[config_env_key][config_env_key])
                                              for config_env_applications_key in config[config_env_key]:
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
