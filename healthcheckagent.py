import logging
import signal
import os
import sys
import time
from datetime import datetime

#project
from utils.pidfile import PidFile
from utils.daemon import Daemon
from config import healthcheckLogging
from config import createLogfile
from healthcheckreporter import HealthcheckReporter

os.umask(022)

#CONSTANTS
DEFAULT_CONFIG_FILE='config.json'
DEFAUTL_LOGGING_LEVEL=logging.INFO
DEFAUTL_LOG_FILENAME='healthcheck.log'
DEFAULT_WAIT_TIME_BEFORE_KILL=1*60

START_COMMANDS = ['start', 'restart']


#PATH
DEFAULT_CONFIG_FILE='config.json'
AGENT_DIR=os.path.dirname(os.path.abspath(__file__))
PID_NAME = __file__
PID_DIR = AGENT_DIR
AGENT_LOG=AGENT_DIR + '/' + DEFAUTL_LOG_FILENAME


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
        self.healthcheckreporter = None
        self.check_interval = DEFAULT_CHECK_INTERVAL
        self.check_frequency = DEFAULT_CHECK_FREQUENCY
        self.configfile=AGENT_DIR + '/' + DEFAULT_CONFIG_FILE
        #self.host=get_hostname()

    def _handle_sigterm(self, signum, frame):
        """Handles SIGTERM and SIGINT, which gracefully stops the agent."""
        log = logging.getLogger('HealthCheckAgent._handle_sigterm()')
        log.info("Caught sigterm. Stopping run loop.")

        #log.debug("Parent Process id is: %s" % (super(Daemon, self).pid()))
        self.run_forever = False
        self.start_event = False

        if self.healthcheckreporter:
            t_end = time.time() + DEFAULT_WAIT_TIME_BEFORE_KILL #One minutes
            while time.time() < t_end:
                if self.healthcheckreporter.running:
                    t_left = t_end - time.time()
                    log.debug("Waiting for current healthcheck to finish Time left %d of %d seconds" % (t_left,60) )
                    time.sleep(5) #Sleep for 5 seconds
                    continue
                else:
                    log.debug("There are no healthcheck current")
                    break
        if self.healthcheckreporter.running:
            log.debug("Timed out waiting for current healthcheck reporter to finish")
            self.healthcheckreporter.stop()
        log.info("Exiting. Bye bye.")
        raise SystemExit

    @classmethod
    def info(cls, verbose=None):
        logging.getLogger().setLevel(logging.ERROR)
        return "Info"

    def run(self, config=DEFAULT_CONFIG_FILE):
        log = logging.getLogger("HealcheckAgent.run()")

        """Main loop of the healthcheck"""
        # Gracefully exit on sigterm
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        if config:
            self.healthcheckreporter=HealthcheckReporter(self.configfile)
            self.check_interval=self.healthcheckreporter.getInterval()
            self.check_frequency=self.healthcheckreporter.getFrequency()

        log.debug("Run %s time at interval %s" % (self.check_frequency,self.check_interval))
        while self.run_forever:
            i=1
            while i <= self.check_frequency:
                if self.run_forever:
                    if i > 1 :
                        t_end=time.time() + self.check_interval
                        while time.time() < t_end:
                            if self.run_forever:
                                log.debug("waiting to run next event %s" % self.healthcheckreporter.start_event)
                                time.sleep(DEFAULT_KILL_TIMEOUT)
                            else:
                                break


                    if self.healthcheckreporter:
                        try:

                            log.info("HealthCheck started at %s" % str(datetime.now()))
                            start_time=time.time()
                            self.healthcheckreporter.start()
                            total_time=time.time()-start_time
                            log.info("HealthCheck finished at %s" % str(datetime.now()))
                            log.info("HealthCheck took %s seconds to complete" % total_time)

                            log.info("Alert Check started at %s" % str(datetime.now()))
                            start_time=time.time()
                            self.healthcheckreporter.alert()
                            total_time=time.time()-start_time
                            log.info("Alert Check finished at %s" % str(datetime.now()))
                            log.info("Alert Check took %s seconds to complete" % total_time)

                            self.healthcheckreporter.running=False
                        finally:
                            self.healthcheckreporter.running=False
                    else:
                        self.healthcheckreporter.stop()
                        log.error("Unable to to run HealthCheck")


                    i+=1

                else:
                    self.healthcheckreporter.stop()
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
        #following line added for py 2.6
        LOG_FILENAME=AGENT_DIR + '/' + DEFAULT_CONFIG_FILE
        #Ensure agent can write to Log
        createLogfile(LOG_FILENAME)
        #Initialize Agent
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
        healthcheckreporter=HealthcheckReporter(AGENT_DIR + '/' + DEFAULT_CONFIG_FILE,configcheck=True)
        if healthcheckreporter.valid():
            log.info("Configuration file %s is valid" % config_file_abs_path)
        else:
            log.info("Configuration file %s is invalid" % config_file_abs_path)

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
