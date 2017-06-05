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

            for host,services in service_status.iteritems():

                log.debug("Check this host %s" % host)
                for name,attributes in services.iteritems():
                    if host in self.services_status:
                        if name in self.services_status[host]:
                            log.debug("Updating existing service to services_status %s" % json.dumps(service_status,indent=4))
                            self.services_status[host][name].update(attributes)
                        else:
                            log.debug("Name not found in services list")
                            log.debug("Adding new service to services_status %s" % json.dumps(service_status,indent=4))
                            self.services_status[host][name]={}
                            self.services_status[host].update(services)
                    else:
                        log.debug("Host not found in services list")
                        log.debug("Adding new host to services_status %s" % json.dumps(service_status,indent=4))
                        self.services_status[host]={}
                        self.services_status[host].update(service_status[host])

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
                                                                                     service.service,service.hosts.keys()))
                            self.last_service=service
                            service.getStatus()
                            log.debug("Status Response" % service.status)
                            self.add(service.status)
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

        def countServices(self):
            log = logging.getLogger('HealthcheckReporter.countServices()')
            counter=0
            if self.services_status:
                for host,services in self.services_status.iteritems():
                    for service in services:
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
                for host,service in self.services_status.iteritems():
                    log.debug("Check availability for service %s" % json.dumps(service,indent=4) )
                    for name,attributes in service.iteritems():
                        if 'available' in attributes:
                            log.debug("Availability is set to %s" % attributes['available'])
                            if not attributes['available']:
                                #Service is offline
                                if not host in offline:
                                    #new offline host
                                    offline[host]={}
                                if not name in offline[host]:
                                    #new service in existing offline host list
                                    offline[host][name]={}
                                #add service to offline dictionary
                                log.debug("Added service %s to offline list" % service[name])
                                offline[host][name].update(attributes)
                                counter+=1
                            else:
                                #If service available remove it from alert list
                                id=service_attributes['service_id']
                                if id in self.servicealerts:
                                    #remove id from service alert dict
                                    del self.servicealerts[id]

            else:
                log.debug("HealthcheckReporter services list is empty")
            log.debug("Offline services %s" % json.dumps(offline,indent=4))
            return counter,offline

        def alert(self):
            log = logging.getLogger('HealthcheckReporter.alert()')
            offline_count=0
            log.debug("Services checked %s" % json.dumps(self.services_status,indent=4))
            offline_count,offline_services=self.getOfflineServices()
            log.debug("Offline services count: %d" % offline_count)
            log.debug("Offline services: %s" % offline_services)
            count_all_services=self.countServices()
            log.debug("Count of services checked %d" % self.countServices())
            hosts_fn=self.getHostsfriendlyname()
            alertservices={}
            alerts_count_for_email=0
            alert_added=False
            alert_lifetime=self.config.alert_lifetime
            for host,services in offline_services.iteritems():
                alertservices[host]={}
                for service_name,service_attributes in services.iteritems():
                    if not service_name in alertservices[host]:
                        alertservices[host][service_name]={}
                    id=service_attributes['service_id']
                    if id in self.servicealerts:
                        last_alert_time=self.servicealerts[id]
                        age_of_last_alert=time.time() - last_alert_time
                        if age_of_last_alert > alert_lifetime:
                            log.debug("Age of Alert for service %s exceeded alert life time %s" % (service_name,alert_lifetime))
                            log.debug("Add service to alert list %s" % service_name)
                            alerts_count_for_email+=1
                            self.servicealerts[id]=time.time()
                            alert_added=True
                            alertservices[host][service_name].update(service_attributes)
                        else:
                            log.debug("Last Alert for service %s not expired " % service_name)
                    else:
                        log.debug("This first alert for service %s since agent start" % service_name)
                        alerts_count_for_email+=1
                        self.servicealerts[id]=time.time()
                        alert_added=True
                        alertservices[host][service_name].update(service_attributes)
            log.debug(json.dumps(self.servicealerts,indent=4))
            log.debug("Following services will be alerted")
            log.debug(json.dumps(alertservices,indent=4))

            if alert_added:
                log.info("Number of Alert found %d " % alerts_count_for_email)
                badservice_html=generateStatusHtmlPage(path=self.template_path,
                                                       host=self.host,
                                                       time=self.getLastChecked(),
                                                       total_services=count_all_services,
                                                       total_services_unavailable=offline_count,
                                                       alerts_count_for_email=alerts_count_for_email,
                                                       hosts_friendlyname=hosts_fn,
                                                       services_status=alertservices
                                                       )
                log.debug("HTML Output")
                log.debug(badservice_html)
                self.sendemail(badservice_html)
            else:
                log.info("No alerts found for alerting")




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
