from messages import Messages
import json
import logging
from datetime import datetime
import time
import os

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#from output import generateStatusHtmlPage
from config import HealthCheckConfig
from healthchecklogging import HealthCheckLogging
from output import createSummaryHTML

def send(config,messages):
    log = logging.getLogger('alert.send()')
    summary={}
    summary=messages.getGoodAndBadStatusCountbyGroup()
    all_messages=dict(messages)
    log.debug("%s" % summary)
    if all_messages:
        email_html=createSummaryHTML(os.path.dirname(os.path.abspath(__file__)),summary,all_messages)
        email(config,email_html)
    else:
        log.debug("Status is Empty")


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


def findbymessagetype(messages,message_type="all",alert_lifetime=7200):
    log = logging.getLogger('alert.findMessagesForEmail()')
    message_valid_type=["ALL","GOOD","BAD"]
    if message_type.upper() in message_valid_type:
        if message_type.upper() == "ALL":
            log.info("Send all messages")
            log.info("%s" % json.dumps(dict(messages),indent=6))
        elif message_type.upper() == "GOOD":
            log.info("Send good messages")
        elif message_type.upper() == "BAD":
            log.info("Send bad messages")
    else:
        log.info("Invalid messgae type return none")





if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        HealthCheckLogging(default_level=logging.DEBUG)
        config=HealthCheckConfig("config.json")
        cls3=Messages()
        cls3.add(myjson)
    except ValueError as e:
        print "cls3 not created: %s" % e
    else:
        send(config,cls3)
