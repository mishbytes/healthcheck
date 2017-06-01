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
            self.services_status={}
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

        def add(self,service_status):
            log = logging.getLogger('HealthcheckReporter.add()')

            log.debug("Before adding service: services_status %s" % json.dumps(self.services_status,indent=4))

            log.debug("Adding service %s" % json.dumps(service_status,indent=4))

            for host,service in service_status.items():

                log.debug("Check this host %s" % host)
                for name,attributes in service.items():
                    if host in self.services_status:
                        log.debug("Current services in host %s %s " % (host,self.services_status[host]))
                        if name in self.services_status[host]:
                            log.debug("Adding service %s" % name)
                            self.services_status[host][name].update(attributes)
                        else:
                            log.debug("Name not found in services list")
                            self.services_status[host].update(service)
                    else:
                        log.debug("Host not found in services list")
                        log.debug("Adding new host to services_status %s" % json.dumps(service_status,indent=4))
                        self.services_status[host]={}
                        self.services_status[host].update(service_status[host])
                    log.debug("New services_status %s" % json.dumps(self.services_status,indent=4))

            log.debug("After adding service: services_status %s" % json.dumps(self.services_status,indent=4))

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
                            service.getStatus()
                            self.add(service.status)
                        log.debug("** Status check ends **")
                    else:
                        log.debug("No applications loaded")
                except Exception as e:
                    log.exception("Exception occurred")
            else:
                pass


        def save(self,type="",filename=''):
            log = logging.getLogger('HealthcheckReporter.save()')


        def getLastChecked(self):
            log = logging.getLogger('HealthcheckReporter.getLastChecked()')
            return self.last_checked

        def countCheckedServices(self):
            log = logging.getLogger('HealthcheckReporter.getAllServicesCount()')
            counter=0
            if self.services_status:
                for host,service in self.services_status.items():
                    log.debug("Service found, increment counter %s" % json.dumps(service,indent=4))
                    counter+=1
            else:
                log.debug("HealthcheckReporter services list is empty")
            return counter

        def getOfflineServices(self):
            log = logging.getLogger('HealthcheckReporter.getOfflineServices()')
            offline={}
            counter=0
            if self.services_status:
                for host,service in self.services_status.items():
                    log.debug("Check availability for service %s" % json.dumps(service,indent=4) )
                    for name,attributes in service.items():
                        log.debug("Availability is set to %s" % attributes['available'])
                        if 'available' in attributes:
                            if not attributes['available']:
                                if not host in offline:
                                    offline[host]={}
                                offline[host].update(service)
                                counter+=1
            else:
                log.debug("HealthcheckReporter services list is empty")
            log.debug("Offline services %s" % json.dumps(offline,indent=4))
            return counter,offline

        def alert(self):
            log = logging.getLogger('HealthcheckReporter.alert()')
            offline_count=0
            log.debug("Alert")
            log.debug("Count of services checked %d" % self.countCheckedServices())
            log.debug("Services checked %s" % json.dumps(self.services_status,indent=4))
            offline_count,offline_services=self.getOfflineServices()
            log.debug("Offline services count: %d" % offline_count)
            log.debug("Offline services: %s" % offline_services)


        def getBadServicesCount(self):
            log = logging.getLogger('HealthcheckReporter.getBadServicesCount()')
            countbadservices=0
            if self.allservices:
                for service in self.allservices:
                    for host in service.hosts:
                        if isinstance(service.available, bool):
                            available=service.available
                        elif isinstance(service.available, dict):
                            available=service.available[host]
                        else:
                            log.debug("Unknown available data type")
                        if not available:
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


        def getOfflineServices2(self):
            log = logging.getLogger('Healthcheck.getOfflineServices()')
            output={}
            count=0
            if self.allservices:
                for service in self.allservices:
                    for host in service.hosts:
                        log.debug("Service Host %s" % str(host))
                        host_str=str(host)
                        service_id=hashlib.md5(host_str + service.name).hexdigest()
                        if isinstance(service.available, bool):
                            #single host service availablility
                            log.debug("Service %s" % service.available)
                            available=service.available
                            message=service.message
                        elif isinstance(service.available, dict):
                            #multiple host service availablility
                            log.debug("Service %s" % service.available[host])
                            available=service.available[host]
                            message=service.message[host]
                        else:
                            log.debug("Unknown available data type")

                        if not host in output:
                            output[host]=[]

                        if not available:
                            output[host].append(
                                                {
                                                    "service":service.name,
                                                    "type":service.type,
                                                    "status":available,
                                                    "last_checked":service.last_checked,
                                                    "additional_info":message,
                                                    "service_id":service_id
                                                }
                                                )
                            count+=1
                            log.debug("Service %s on host %s added to unavailable list" % (service.name,host))
                        else:
                            log.debug("Service %s on host %s is available" % (service.name,host))


            log.debug("Offline Services")
            log.debug(json.dumps(output,indent=4))
            return output,count

                    #self.return_code=response["return_code"]
                    #self.available=response["value"]
                    #self.message=response["message"]



        def alert2(self):
            log = logging.getLogger('Healthcheck.alert()')
            count_all_services=self.countServices()
            badservices,count_badservices=self.getOfflineServices()
            hosts_fn=self.getHostsfriendlyname()
            alertservices={}
            alerts_count_for_email=0
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
                            alerts_count_for_email+=1
                            self.servicealerts[id]=time.time()
                            alert_added=True
                            alertservices[host].append(service)
                        else:
                            log.debug("Last Alert for service %s not expired " % service)
                    else:
                        log.debug("This first alert for service %s since agent start" % service)
                        alerts_count_for_email+=1
                        self.servicealerts[id]=time.time()
                        alert_added=True
                        alertservices[host].append(service)


            log.debug(json.dumps(self.servicealerts,indent=4))
            log.debug("Following services will be alerted")
            log.debug(json.dumps(alertservices,indent=4))
            #service_alert_id=hashlib.md5(host + service['service']).hexdigest()
            if alert_added:

                log.info("Number of Alert found %d " % alerts_count_for_email)
                badservice_html=generateStatusHtmlPage(path=self.template_path,
                                                       host=self.host,
                                                       time=self.getLastChecked(),
                                                       total_services=count_all_services,
                                                       total_services_unavailable=count_badservices,
                                                       alerts_count_for_email=alerts_count_for_email,
                                                       hosts_friendlyname=hosts_fn,
                                                       services_status=alertservices
                                                       )
                log.debug("HTML Output")
                log.debug(badservice_html)
                self.sendemail(badservice_html)
            else:
                log.info("No alerts found for alerting")

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
