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
            self.servicealerts={}
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
                                                                                     service.name,service.hosts.keys()))
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

        def getHostsfriendlyname(self):
            log = logging.getLogger('Healthcheck.getHostsfriendlyname()')
            hosts_desc={}
            for service in self.allservices:
                for host,desc in service.hosts.items():
                    hosts_desc[host]=desc
            log.debug("Host friendly names %s" % json.dumps(hosts_desc,indent=4))
            return hosts_desc


        def getOfflineServices(self):
            log = logging.getLogger('Healthcheck.getOfflineServices()')
            output={}
            if self.allservices:
                for service in self.allservices:
                    for host in service.hosts:
                        log.debug("Service Host %s" % str(host))
                        host_str=str(host)
                        service_id=hashlib.md5(host_str + service.name).hexdigest()
                        if isinstance(service.available, bool):
                            #single host service availablility
                            log.debug("Service %s" % service.available)
                            availablility=service.available
                            message=service.message
                        elif isinstance(service.available, dict):
                            #multiple host service availablility
                            log.debug("Service %s" % service.available[host])
                            availablility=service.available[host]
                            message=service.message[host]
                        else:
                            log.debug("Unknown available data type")

                        if not host in output:
                            output[host]=[]

                        output[host].append(
                                            {
                                                "service":service.name,
                                                "type":service.type,
                                                "status":availablility,
                                                "last_checked":service.last_checked,
                                                "additional_info":message,
                                                "service_id":service_id
                                            }
                                            )


            log.debug("Bad Services")
            log.debug(json.dumps(output,indent=4))
            return output

                    #self.return_code=response["return_code"]
                    #self.available=response["value"]
                    #self.message=response["message"]


        def alert(self):
            log = logging.getLogger('Healthcheck.alert()')
            badservices=self.getOfflineServices()
            hosts_fn=self.getHostsfriendlyname()
            alertservices={}
            alert_added=False
            alert_lifetime=self.config.alert_lifetime
            for host,services in badservices.iteritems():
                alertservices[host]=[]
                for service in services:
                    id=service['service_id']
                    if id in self.servicealerts:
                        last_alert_time=self.servicealerts[id]
                        age_of_last_alert=time.time() - last_alert_time
                        if age_of_last_alert > alert_lifetime:
                            log.debug("Age of Alert for service %s exceeded alert life time %s" % (service,alert_lifetime))
                            log.debug("Add service to alert list %s" % service)
                            self.servicealerts[id]=time.time()
                            alert_added=True
                            alertservices[host].append(service)
                        else:
                            log.debug("Last Alert for service %s not expired " % service)
                    else:
                        log.debug("This first alert for service %s since agent start" % service)
                        self.servicealerts[id]=time.time()
                        alert_added=True
                        alertservices[host].append(service)


            log.debug(json.dumps(self.servicealerts,indent=4))
            log.debug("Following services will be alerted")
            log.debug(json.dumps(alertservices,indent=4))
            #service_alert_id=hashlib.md5(host + service['service']).hexdigest()
            if alert_added:

                badservice_html=generateStatusHtmlPage(path=self.template_path,
                                                       host=self.host,
                                                       time=self.getLastChecked(),
                                                       total_services=self.getAllServicesCount(),
                                                       total_services_unavailable=self.getBadServicesCount(),
                                                       hosts_friendlyname=hosts_fn,
                                                       services_status=alertservices
                                                       )
                log.debug("HTML Output")
                log.debug(badservice_html)
                self.sendemail(badservice_html)
            else:
                log.debug("No alerts found for alerting")

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
                    log.debug("Alert email sent at %s " % str(datetime.now()))
                    conn.quit()
                except (socket.error,socket.gaierror,smtplib.SMTPException) as e:
                    log.error("Failed to send email: %s" % str(e))
                    #log.exception(e)
            else:
                log.debug("Email feature disabled in config file")
                log.debug("set sendemail to yes in config file to send email")
