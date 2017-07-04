
import json
import socket
import logging
import time
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import HealthCheckConfig
from config import gethtmltemplatedir
from config import getconfigpath
from messages import MessageDatabase
from output import full_status_html

def send(config,messagesdb):
    log = logging.getLogger('alert.send()')
    summary={}
    messages_to_send=None
    summary=messagesdb.summary()
    log.debug("%s" % summary)
    if 'ALL' == config.report_type.upper():
        log.debug("Sending all messages")
        messages_to_send=dict(messagesdb)
    elif 'ALERT' == config.report_type.upper():
        log.debug("Sending only alerts")
        alertcount,messages_to_send=messagesdb.getAlerts(alert_lifetime=config.alert_lifetime)
        log.info("Number of Alerts Found: %s" % alertcount)

    if messages_to_send:
        #convert messages into HTML using jinja2
        log.debug(json.dumps(messages_to_send,indent=4))
        email_html=full_status_html(gethtmltemplatedir(),summary,messages_to_send)
        email(config,email_html)
    else:
        log.debug("No messages found")



def email(config,content):
    log = logging.getLogger('Healthcheck.sendemail()')
    if config.email_enabled:
        curr_time=time.time()
        log.debug("Sending Email at %s " % str(datetime.now()))
        try:
            # Create message container - the correct MIME type is multipart/alternative.
            log = logging.getLogger('alert.email()')
            msg = MIMEMultipart('alternative')
            msg['Subject'] = config.email_subject
            msg['From'] = config.smtp_sender
            msg['To'] = ", ".join(config.smtp_receiver)
            html_content=""


            html_content = content

            part1 = MIMEText(html_content, 'html')

            # Attach parts into message container.
            # According to RFC 2046, the last part of a multipart message, in this case
            # the HTML message, is best and preferred.
            msg.attach(part1)

            # Send the message via local SMTP server.
            #s = smtplib.SMTP('smtp.gmail.com',465)
            conn = smtplib.SMTP(config.smtp_host,config.smtp_port, timeout=30)
            #conn.starttls()
            #user,password = ('Demo','Test')
            #conn.login(user,password)

            # sendmail function takes 3 arguments: sender's address, recipient's address
            # and message to send - here it is sent as one string.
            conn.sendmail(config.smtp_sender, config.smtp_receiver, msg.as_string())
            log.info("Alert email sent at %s " % str(datetime.now()))
            conn.quit()
        except (socket.error,socket.gaierror,smtplib.SMTPException) as e:
            log.error("Failed to send email: %s" % str(e))
            #log.exception(e)
    else:
        log.debug("Email feature disabled in config file")
        log.debug("set email_enabled to yes in config file")


if __name__ == '__main__':
    myjson={"testserver": {
                               "SASStudio": {
                                               "available": False,
                                               "return_code": 300,
                                               "last_checked": "2017-06-05 11:56:42.181631",
                                               "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                               "message": "[Errno 8] nodename nor servname provided, or not known",
                                               "type": "webapp",
                                               "group":"SAS Web applications"
                                             },
                               "SASStudio2": {
                                               "available": True,
                                               "return_code": 300,
                                               "last_checked": "2017-06-05 11:56:42.181631",
                                               "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                               "message": "[Errno 8] nodename nor servname provided, or not known",
                                               "type": "webapp"
                                             }

                            },
            "testserver3": {
                                       "SASStudio": {
                                                       "available": False,
                                                       "return_code": 300,
                                                       "last_checked": "2017-06-05 11:56:42.181631",
                                                       "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                                       "message": "[Errno 8] nodename nor servname provided, or not known",
                                                       "type": "webapp"
                                                     },
                                       "SASStudio2": {
                                                       "available": True,
                                                       "return_code": 300,
                                                       "last_checked": "2017-06-05 11:56:42.181631",
                                                       "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                                       "message": "[Errno 8] nodename nor servname provided, or not known",
                                                       "type": "webapp",
                                                       "environment":"unknown"
                                                     }

                                    }
              }

    try:
        #from healthchecklogging import initializeLogging
        #initializeLogging(default_level=logging.DEBUG)
        config=HealthCheckConfig(getconfigpath())
        logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        cls3=MessageDatabase()
        cls3.add(myjson)
    except ValueError as e:
        print "cls3 not created: %s" % e
    else:
        send(config,cls3)
