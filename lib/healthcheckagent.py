import logging
import signal
import os
import sys
import time
from datetime import datetime

#project
from utils.pidfile import PidFile
from utils.daemon import Daemon

from config import HealthCheckConfig
from config import getconfigpath
from config import getpiddir
from config import getpidname

from healthcheckreporter import HealthcheckReporter
from healthchecklogging import initializeLogging


os.umask(022)

#PATH
AGENT_DIR=os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE='config.cfg'
PID_NAME = __file__
PID_DIR = AGENT_DIR
CONFIG_FILE=AGENT_DIR + '/' + DEFAULT_CONFIG_FILE

#CONSTANTS
DEFAUTL_LOGGING_LEVEL=logging.INFO
DEFAULT_WAIT_BETWEEN_TASKS=30 #seconds
DEFAULT_WAIT_TIME_BEFORE_KILL=1*60 #1 minute
START_COMMANDS = ['start', 'restart']



#global
log = logging.getLogger(__name__)

def disableLogging():
    logging.getLogger("utils").setLevel(logging.WARNING)
    #logging.getLogger("config").setLevel(logging.WARNING)

#disableLogging()
DEFAULT_CHECK_INTERVAL=60
DEFAULT_CHECK_FREQUENCY=1

class HealthcheckAgent(Daemon):
    log = logging.getLogger('HealthCheckAgent')
    def __init__(self, pidfile):
        Daemon.__init__(self, pidfile)
        self.run_forever = True
        self.start_event=True
        self.host=''
        self.config=None
        self.healthcheckreporter = None
        self.check_interval = DEFAULT_CHECK_INTERVAL
        self.check_frequency = DEFAULT_CHECK_FREQUENCY
        self.configfile=AGENT_DIR + '/' + DEFAULT_CONFIG_FILE

        #self.host=get_hostname()

    def _handle_sigterm(self, signum, frame):
        """Handles SIGTERM and SIGINT, which gracefully stops the agent."""
        log = logging.getLogger('HealthCheckAgent._handle_sigterm()')

        if self.start_event:

            log.info("Caught sigterm. Stopping run loop.")

            #log.debug("Parent Process id is: %s" % (super(Daemon, self).pid()))
            self.run_forever = False
            self.start_event = False

            #self.healthcheckreporter.stop()

            if self.healthcheckreporter.isRunning():
                t_end = time.time() + DEFAULT_WAIT_TIME_BEFORE_KILL #One minutes
                while time.time() < t_end:
                    if self.healthcheckreporter.isRunning():
                        t_left = t_end - time.time()
                        log.debug("Healthcheck Reporter thread is running")
                        log.debug("Waiting.. Time left %d of %d seconds" % (t_left,DEFAULT_WAIT_TIME_BEFORE_KILL) )
                        time.sleep(5) #Sleep for 5 seconds
                        continue
                    else:
                        self.healthcheckreporter.stop()
                        log.debug("Healthcheck Reporter thread stopped")
                        break
                log.debug("Timed out waiting for healthcheck reporter thread to finish")
            else:
                log.debug("Healthcheck Reporter thread stopped")
            log.info("Exiting. Bye bye.")
            raise SystemExit
        else:
            log.debug("Stop already in progress")

    @classmethod
    def info(cls, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return "Info"

    def run(self):

        log = logging.getLogger("HealthCheckAgent.run()")

        """Main loop of the healthcheck"""
        # Gracefully exit on sigterm
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        config=getconfigpath()
        #Call function to Initialize logging
        initializeLogging(configfile=config)

        if config:
            log.info("Found configuration file %s" % os.path.abspath(config))
            self.config=HealthCheckConfig(config)
            if self.config.isValid():
                self.healthcheckreporter=HealthcheckReporter(self.config)
            else:
                log.info("Invalid Configuration file %s" % os.path.abspath(config))
        else:
            log.info("Configuration File is missing")

        if self.healthcheckreporter:
            try:
                log.info("HealthCheck started at %s" % str(datetime.now()))
                start_time=time.time()
                self.healthcheckreporter.run()
                total_time=time.time()-start_time
                log.info("HealthCheck finished at %s" % str(datetime.now()))
                log.info("HealthCheck took %s seconds to complete" % total_time)

                log.info("Sending message started %s" % str(datetime.now()))
                start_time=time.time()
                self.healthcheckreporter.send()
                total_time=time.time()-start_time
                log.info("Message sent at %s" % str(datetime.now()))
                log.info("Alert Check took %s seconds to complete" % total_time)
                self.healthcheckreporter.running=False
            except (KeyboardInterrupt, SystemExit):
                self.healthcheckreporter.running=False
            finally:
                self.healthcheckreporter.running=False
        else:
            log.debug("Reporter class not initialized")

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
        'configcheck',
        'emailcheck'
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
        #log.debug(CONFIG_FILE)
        #Initialize Agent
        hcagent = HealthcheckAgent(PidFile(getpidname(), getpiddir()).get_path())

    if command in START_COMMANDS:
        #log.info('Healthcheck Agent version 1.0')
        pass

    if 'start' == command:
        hcagent.start()
        #agent.start()

    elif 'stop' == command:
        hcagent.stop()
        #agent.stop()

    elif 'restart' == command:
        hcagent.restart()

    elif 'status' == command:
        hcagent.status()

    elif 'info' == command:
        return "Health Check Version: 1.0"

    elif 'configcheck' == command or 'configtest' == command:
        CONFIG_FILE=AGENT_DIR + '/' + DEFAULT_CONFIG_FILE
        config=HealthCheckConfig(CONFIG_FILE)
        if config.isValid():
            sys.stdout.write("Configuration file %s is valid \n" % CONFIG_FILE)
        else:
            sys.stdout.write("Configuration file %s is invalid \n" % CONFIG_FILE)

    elif 'emailcheck' == command:
        pass
        #config_file_abs_path=PROJECT_DIR + '/config.json'
        #healthcheck=HealthcheckReporter(AGENT_DIR + '/' + DEFAULT_CONFIG_FILE)
        #healthcheck.testEmail()

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
