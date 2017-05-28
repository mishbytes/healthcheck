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
            self.status_dict={}
            self.status_dict["hostname"]="myhost"
            self.status_dict["timestamp"]=str(datetime.now())
            self.status_dict["output"]=[]
            self.status_output=[]
            #Initialize Health check from configuration file config.json
            self.config=HealthCheckConfig(configfile,configcheck=configcheck)
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
                        for service in self.config.services:
                            log.debug("Environment: %s Application: %s Hosts: %s" % (service.environment,
                                                                                     service.name,service.hosts))
                            self.last_service=service
                            service.status()
                        log.debug("** Status check ends **")
                    else:
                        log.debug("No applications loaded")
                except Exception as e:
                    log.exception("Exception occurred")
            else:
                pass


        def save(self,type="",filename=''):
            log = logging.getLogger('Healthcheck.save()')

        def showAlerts(self):
            log = logging.getLogger('Healthcheck.showAlerts()')
            self.running=True
            collect_alerts=[]
            if self.status_dict:
                for status_property in self.status_dict:
                    if status_property.upper() == "OUTPUT":
                        for output in self.status_dict["output"]:
                            if isinstance(output["value"], dict):
                                for dict_key, dict_value in output["value"].iteritems():
                                    if not dict_value:
                                        msg = "%s:%s is unavailable via host %s <br>" % (output["application_type"],output["application"],dict_key)
                                        collect_alerts.append(msg)
                            elif not output["value"]:
                                log.info("%s:%s is unavailable via host %s" % (output["application_type"],output["application"],output["hosts"]))

                                #log.info(output["application"])
                #self.sendemail(collect_alerts)

            else:
                log.info("Empty status, nothing to save")

        def sendemail(self,content):
            try:
                # Create message container - the correct MIME type is multipart/alternative.
                log = logging.getLogger('Healthcheck.sendemail()')
                msg = MIMEMultipart('alternative')
                msg['Subject'] = "Email from Python Program"
                msg['From'] = self.config.smtp_sender
                msg['To'] = self.config.smtp_receiver
                html_content=""


                begin_html="""
                              <html>
                                <head></head>
                                <body>
                           """
                end_html="""
                                </body>
                              </html>
                          """
                for alertmsg in content:
                  html_content += alertmsg

                html_content = begin_html + html_content + end_html

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
                conn.sendmail(self.hc_config.smtp_sender, self.hc_config.smtp_receiver, msg.as_string())
                conn.quit()
            except (socket.error,socket.gaierror,smtplib.SMTPException) as e:
                log.error("Failure to send email: %s" % str(e))
                #log.exception(e)
