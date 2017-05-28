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

from datetime import datetime

#email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


#project
from service import Service
from config import HealthCheckConfig

def getHostName():
    if socket.gethostname().find('.')>=0:
        name=socket.gethostname()
    else:
        try:
            name=socket.gethostbyaddr(socket.gethostname())[0]
        except socket.gaierror:
            name=socket.gethostname()
    return name


log = logging.getLogger('HealthCheckReporter')

class HealthcheckReporter(threading.Thread):

        def __init__(self,configfile,configcheck=False):
            threading.Thread.__init__(self)
            self.finished = threading.Event()
            self.last_service=None
            self.running=False
            self.start_event=True
            self.alert_sent=False
            self.alert_sent_time=0
            self.alert_expiry_time=0
            self.last_checked = ''
            self.status_output=[]
            #Initialize Health check from configuration file config.json
            self.config=HealthCheckConfig(configfile,configcheck=configcheck)
            self.allservices=[]
            #As this class is a thread, disable sys stdout and stderr
            sys.stdout = open('/dev/null', 'w')
            sys.stderr = open('/dev/null', 'w')


        def stop(self):
            self.start_event=False
            self.running=False
            log.info("Stopping HealthcheckReporter thread")
            self.finished.set()
            log.info("HealthcheckReporter thread stopped")

        def getRunIntervalSeconds(self):
            return self.config.run_interval_seconds

        def getRunCounter(self):
            return self.config.run_counter

        def valid(self):
            return self.config.valid

        def start(self):
            if self.start_event:
                self.running=True
                log = logging.getLogger('Healthcheck.start()')
                status_output=[]
                try:
                    if self.config.services:
                        log.debug("** Status check begins **")
                        self.last_checked = str(datetime.now())
                        for service in self.config.services:
                            log.debug("Environment: %s Application: %s Hosts: %s" % (service.environment,
                                                                                     service.name,service.hosts))
                            self.last_service=service
                            service.status()
                            self.allservices.append(service)
                        log.debug("** Status check ends **")
                    else:
                        log.debug("No applications loaded")
                except Exception as e:
                    log.exception("Exception occurred")
            else:
                pass


        def save(self,type="",filename=''):
            log = logging.getLogger('Healthcheck.save()')


        def getLastChecked(self):
            log = logging.getLogger('Healthcheck.getLastChecked()')
            return self.last_checked

        def getAllServicesCount(self):
            log = logging.getLogger('Healthcheck.getAllServicesCount()')
            log.debug("Available services %s" % len(self.allservices))
            if self.allservices:
                log.debug("Available services %s" % len(self.allservices))
                return len(self.allservices)
            else:
                return 0
        def getBadServicesCount(self):
            log = logging.getLogger('Healthcheck.getBadServicesCount()')
            countbadservices=0
            if self.allservices:
                for service in self.allservices:
                    if not service.available:
                        countbadservices+=1
            return countbadservices

        def getBadServicesbyHostJSON(self):
            log = logging.getLogger('Healthcheck.getBadServicesbyHostJSON()')
            output={}
            if self.allservices:
                for service in self.allservices:
                        if isinstance(service.hosts, list):
                            for host in service.hosts:
                                if not service.available[host]:
                                    log.debug("Check whether service %s is available on %s host" % (service.name,host))
                                    if not host in output:
                                        output[host]=[]
                                    output[host].append(
                                                {"service":service.name,
                                                  "type":service.type,
                                                  "status":service.available[host],
                                                  "last_checked":service.last_checked,
                                                  "additional_info":service.message[host]
                                                  }
                                                )
                                else:
                                    #Service Available
                                    pass
                                #output[host]={"additional_info":service.message}
                        else:
                            log.debug("Check whether service %s is available on %s host" % (service.name,service.hosts))
                            if not service.available:
                                host=service.hosts
                                if not host in output:
                                    output[host]=[]
                                output[host].append(
                                            {"service":service.name,
                                              "type":service.type,
                                              "status":service.available,
                                              "last_checked":service.last_checked,
                                              "additional_info":service.message
                                              }
                                            )


            log.debug("Bad Services")
            log.debug(json.dumps(output,indent=4))
            return output

                    #self.return_code=response["return_code"]
                    #self.available=response["value"]
                    #self.message=response["message"]

        def sendemail(self,content):
            log = logging.getLogger('Healthcheck.sendemail()')
            curr_time=time.time()

            if (curr_time > self.alert_expiry_time or not self.alert_sent):
                    log.debug("Sending Email")
                    self.alert_sent=True
                    self.alert_sent_time=curr_time
                    self.alert_expiry_time=curr_time+ self.config.alert_expiry
                    try:
                        # Create message container - the correct MIME type is multipart/alternative.
                        log = logging.getLogger('Healthcheck.sendemail()')
                        msg = MIMEMultipart('alternative')
                        msg['Subject'] = self.config.email_subject
                        msg['From'] = self.config.smtp_sender
                        msg['To'] = self.config.smtp_receiver
                        html_content=""


                        html_content = content

                        part1 = MIMEText(html_content, 'html')

                        # Attach parts into message container.
                        # According to RFC 2046, the last part of a multipart message, in this case
                        # the HTML message, is best and preferred.
                        msg.attach(part1)

                        # Send the message via local SMTP server.
                        #s = smtplib.SMTP('smtp.gmail.com',465)
                        conn = smtplib.SMTP(self.config.smtp_host,self.config.smtp_port, timeout=30)
                        #conn.starttls()
                        #user,password = ('Demo','Test')
                        #conn.login(user,password)

                        # sendmail function takes 3 arguments: sender's address, recipient's address
                        # and message to send - here it is sent as one string.
                        conn.sendmail(self.config.smtp_sender, self.config.smtp_receiver, msg.as_string())
                        conn.quit()
                    except (socket.error,socket.gaierror,smtplib.SMTPException) as e:
                        log.error("Failure to send email: %s" % str(e))
                        #log.exception(e)
            else:
                log.debug("Last Alert sent has not expired yet")
