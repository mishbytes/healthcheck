"""
__appname__='healthcheck'
__version__='1.0.0'
"""

__HEALTHCHECKNAME__='healthcheck'
__HEALTHCHECKVERSION__='1.0.0'

#standard python libraies
import sys
import os
import socket
import logging
import json
import time
import threading
import hashlib

from datetime import datetime

#email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#project
from service import Service
from config import HealthCheckConfig
from utils.hosts import get_hostname
from output import generateStatusHtmlPage
from messages import Messages
from alert import send

log = logging.getLogger('HealthCheckReporter')

class HealthcheckReporter(object):

        def __init__(self,configfile,configcheck=False):
            self.host=get_hostname()
            self.last_service=None
            self.running=False
            self.start_event=True
            self.alert_sent=False
            self.alert_sent_time=0
            self.alert_expiry_time=0
            self.last_checked = ''
            self.status_output=[]
            #Initialize Health check from configuration file config.json
            self.configfile=configfile
            self.config=HealthCheckConfig(self.configfile,configcheck=configcheck)

            #self.template_path should point to directort where jinja2 template file is
            self.template_path=os.path.dirname(os.path.abspath(__file__))
            self.allservices=[]
            self.services_status={}
            self.servicealertstimer={}
            self.responsetime=0
            self.messages=Messages()



        def stop(self):
            self.start_event=False

        def isRunning(self):
            return self.running

        def getInterval(self):
            return self.config.interval

        def getFrequency(self):
            return self.config.frequency

        def valid(self):
            return self.config.valid


        def run(self):
            self.responsetime=0
            #Discard old messages
            self.messages.reset()
            if self.start_event:
                log = logging.getLogger('HealthcheckReporter.start()')
                status_output=[]
                try:
                    if self.config.services:
                        log.debug("** Status check begins **")
                        self.last_checked = str(datetime.now())
                        for service in self.config.services:
                            #If thread stop event is called then break from while loop
                            if self.start_event:
                                self.running=True
                                log.debug("checking service %s" % json.dumps(dict(service),indent=4))
                                self.last_service=service
                                start_time=time.time()
                                service.getStatus()
                                elapsed=time.time()-start_time
                                self.responsetime+=elapsed
                                log.debug("Status Response" % service.status)
                                try:
                                    self.messages.add(service.status)
                                except ValueError as e:
                                    log.debug("Invalid status format")
                                    log.exception(e)
                                self.running=False
                            else:
                                self.running=False
                                break

                        log.debug("** Status check ends **")
                    else:
                        log.debug("No applications loaded")
                except Exception as e:
                    log.exception("Exception occurred")
            else:
                log.info("HealthCheckReporter has been disabled")


        def getLastChecked(self):
            log = logging.getLogger('HealthcheckReporter.getLastChecked()')
            return self.last_checked

        def send(self):
            log = logging.getLogger('HealthcheckReporter.send()')
            send(self.config,self.messages)
