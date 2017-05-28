import logging
import signal
import os
import sys
import time

#project
from utils.pidfile import PidFile
from utils.daemon import Daemon
from utils.hosts import get_hostname
from output import generateStatusHtmlPage
from config import healthcheckLogging
from healthcheckreporter import HealthcheckReporter

os.umask(022)

#CONSTANTS
DEFAULT_CONFIG_FILE='config.json'
DEFAUTL_LOGGING_LEVEL=logging.INFO
DEFAUTL_LOG_FILENAME='healthcheck.log'
ENABLE_CONSOLE_LOG=True
DEFAUTL_CONSOLE_LOG_FILENAME='console.log'
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

def consoleLogging(filename=None):
    if filename:
        healthcheckLogging(filename=DEFAUTL_CONSOLE_LOG_FILENAME,default_level=DEFAUTL_LOGGING_LEVEL)
    else:
        healthcheckLogging(default_level=DEFAUTL_LOGGING_LEVEL)

consoleLogging()
#global
log = logging.getLogger(__name__)

def disableLogging():
    logging.getLogger("utils").setLevel(logging.WARNING)
    #logging.getLogger("config").setLevel(logging.WARNING)

#disableLogging()

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
        self.config_file=''
        self.host=get_hostname()

    def _handle_sigterm(self, signum, frame):
        """Handles SIGTERM and SIGINT, which gracefully stops the agent."""
        log = logging.getLogger('HealthCheckAgent._handle_sigterm()')
        log.info("Caught sigterm. Stopping run loop.")

        log.debug("Parent Process id is: %s" % (super(Daemon, self).pid()))
        self.run_forever = False
        self.start_event = False

        if self.healthcheckreporter:
            t_end = time.time() + 1*60 #One minutes
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
        log.info("Exit")
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

            self.healthcheckreporter=HealthcheckReporter(config_file_abs_path)
            self.check_interval=self.healthcheckreporter.getRunIntervalSeconds()
            self.check_frequency=self.healthcheckreporter.getRunCounter()
            #self.healthcheck=Healthcheck(config)

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
                    log.info("Starting HealthCheck instance# %d" % i)
                    if self.healthcheckreporter:
                        try:
                            self.healthcheckreporter.start()
                            badservice_html=generateStatusHtmlPage(path=PROJECT_DIR,
                                               host=self.host,
                                               time=self.healthcheckreporter.getLastChecked(),
                                               total_services=self.healthcheckreporter.getAllServicesCount(),
                                               total_services_unavailable=self.healthcheckreporter.getBadServicesCount(),
                                               services_status=self.healthcheckreporter.getBadServicesbyHostJSON()
                                               )
                            #self.healthcheckreporter.showAlerts()
                            #self.healthcheckreporter.stop()
                            self.healthcheckreporter.sendemail(badservice_html)
                            self.healthcheckreporter.running=False
                        finally:
                            self.healthcheckreporter.running=False
                    else:
                        self.healthcheckreporter.stop()
                        log.error("Unable to to run HealthCheck")
                    log.info("Finished HealthCheck instance# %d" % i)
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
        config_file_abs_path=PROJECT_DIR + '/config.json'
        healthcheckreporter=HealthcheckReporter(config_file_abs_path,configcheck=True)
        if healthcheckreporter.valid():
            log.info("Configuration file %s is valid" % config_file_abs_path)
        else:
            log.info("Configuration file %s is invalid" % config_file_abs_path)

    elif 'emailcheck' == command:
        config_file_abs_path=PROJECT_DIR + '/config.json'
        #healthcheck=Healthcheck(config_file_abs_path)
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
