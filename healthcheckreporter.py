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
from config import HealthCheckConfigStore
from utils.hosts import get_hostname
from output import generateStatusHtmlPage
from messages import Messages


log = logging.getLogger('HealthCheckReporter')

class HealthcheckReporter(threading.Thread):

        def __init__(self,configfile,configcheck=False):
            threading.Thread.__init__(self)
            self.finished = threading.Event()
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
            self.config=HealthCheckConfigStore(self.configfile,configcheck=configcheck)

            #self.template_path should point to directort where jinja2 template file is
            self.template_path=os.path.dirname(os.path.abspath(__file__))
            self.allservices=[]
            self.services_status={}
            self.servicealertstimer={}
            self.responsetime=0
            self.messages=Messages()
            #As this class is a thread, disable sys stdout and stderr
            sys.stdout = open('/dev/null', 'w')
            sys.stderr = open('/dev/null', 'w')


        def stop(self):
            self.start_event=False
            self.running=False
            log.info("Stopping HealthcheckReporter thread")
            self.finished.set()
            log.info("HealthcheckReporter thread stopped")

        def getInterval(self):
            return self.config.interval

        def getFrequency(self):
            return self.config.frequency

        def valid(self):
            return self.config.valid


        def start(self):
            self.responsetime=0
            #Empty messages before checking every service
            self.messages.reset()
            if self.start_event:
                self.running=True
                log = logging.getLogger('Healthcheck.start()')
                status_output=[]
                try:
                    if self.config.services:
                        log.debug("** Status check begins **")
                        self.last_checked = str(datetime.now())
                        for service in self.config.services:
                            log.debug("Environment: %s Application: %s Hosts: %s" % (self.config.env_name,
                                                                                     service.service,service.hosts.keys()))
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


        def alert(self):
            log = logging.getLogger('HealthcheckReporter.alert()')

            offline_count=0
            alertservices={}
            alerts_count_for_email=0
            alert_added=False

            #count messages
            count_all_services=len(self.messages)
            #get messages which are unavailable
            offline_count,offline_services=self.messages.getUnavailableAsDict()
            #get friendly hostnames from config
            hosts_fn=self.getHostsfriendlyname()
            #get messages for alert
            alerts_count_for_email,alertservices=self.messages.getAlertMessagesAsDict(alert_lifetime=self.config.alert_lifetime)

            log.debug("Number of services checked %d" % count_all_services)
            log.debug("Services checked %s" % json.dumps(dict(self.messages),indent=4))
            log.info("Number of offline services: %d" % offline_count)
            log.debug("Offline services: %s" % offline_services)

            if alertservices:
                log.info("Number of Alert found %d " % alerts_count_for_email)
                badservice_html=generateStatusHtmlPage(path=self.template_path,
                                                       host=self.host,
                                                       time=self.getLastChecked(),
                                                       total_services=count_all_services,
                                                       total_services_unavailable=offline_count,
                                                       alerts_count_for_email=alerts_count_for_email,
                                                       hosts_friendlyname=hosts_fn,
                                                       services_status=alertservices,
                                                       reporter_responsetime=self.responsetime
                                                       )
                log.debug("HTML Output")
                log.debug(badservice_html)
                self.sendemail(badservice_html)
            else:
                log.debug("No alerts found for alerting")




        def getHostsfriendlyname(self):
            log = logging.getLogger('Healthcheck.getHostsfriendlyname()')
            hosts_desc={}
            for service in self.config.services:
                for host,desc in service.hosts.iteritems():
                    hosts_desc[host]=desc
            log.debug("Host friendly names %s" % json.dumps(hosts_desc,indent=4))
            return hosts_desc



        def sendemail(self,content):
            log = logging.getLogger('Healthcheck.sendemail()')
            if self.config.email_enabled:
                curr_time=time.time()
                log.debug("Sending Email at %s " % str(datetime.now()))
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
                    log.info("Alert email sent at %s " % str(datetime.now()))
                    conn.quit()
                except (socket.error,socket.gaierror,smtplib.SMTPException) as e:
                    log.error("Failed to send email: %s" % str(e))
                    #log.exception(e)
            else:
                log.debug("Email feature disabled in config file")
                log.debug("set email_enabled to yes in config file")
