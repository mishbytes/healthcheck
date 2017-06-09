import logging
import json
import os
import sys

DEFAUTL_LOGGING_LEVEL=logging.INFO

def HealthCheckLogging(configfile=None,default_level=logging.INFO,filename=None):

    if configfile:
        try:
            with open(configfile) as f:
                config=json.load(f)
                for config_key in config.keys():
                    if 'VERBOSE' == config_key.upper():
                        if 'YES' == config[config_key].upper():
                            default_level=logging.DEBUG
                        elif 'NO' == config[config_key].upper():
                            default_level=logging.INFO
                    if 'LOG' == config_key.upper():
                        filename = config[config_key]
        except Exception as err:
            log.exception(err)

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not filename == None:
        try:
            #Ensure log file is valid and writable
            createLog(configfile)
            logging.basicConfig(filename=filename,level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        except (IOError, OSError) as e:
            logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            log.error(e)
            sys.exit(2)
    else:
        logging.basicConfig(level=default_level,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def createLog(configfile):
    try:
        with open(configfile) as f:
            config=json.load(f)
        if 'log' in config:
            logfile=config['log']
            if os.path.isfile(logfile):
                if os.access(logfile, os.W_OK):
                    sys.stdout.write('Log file %s \n' % logfile)
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
        HealthCheckLogging(filename='console.log',default_level=DEFAUTL_LOGGING_LEVEL)
    else:
        HealthCheckLogging(default_level=DEFAUTL_LOGGING_LEVEL)

if __name__ == '__main__':
    HealthCheckLogging(default_level=DEFAUTL_LOGGING_LEVEL)
