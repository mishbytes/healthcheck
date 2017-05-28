import logging
import time
import threading
from datetime import datetime

#project
from check_sas import sasLogon
from check_disk import getDiskStatus

log = logging.getLogger('Service')

class Service(object):
    def __init__(self,environment,level,name,type,hosts,port,protocol,user,password):
        self.type=type
        self.environment=environment
        self.level=environment
        self.name=name
        self.type=type
        self.hosts=hosts
        self.port=port
        self.protocol=protocol
        self.user=user
        self.password=password

        #Status keys
        self.checked=False
        self.available=False
        self.return_code=9999
        self.message=''
        self.last_checked=None
        self.command_timeoutseconds=30


    def isAvailable(self):
        return self.available

    def status(self):
        log = logging.getLogger('Service.status()')
        if self.type.upper() == 'WEBAPP':
            #response={"value":True|False,"return_code":return_code,"message":message}
            logging.debug("Checking WebApp: %s://%s:%s/%s" % (self.protocol,self.hosts,self.port,self.name))
            self.last_checked=str(datetime.now())
            response=sasLogon(self.environment,
                              self.protocol,
                              self.hosts,
                              self.port,
                              self.name,
                              self.user,
                              self.password)
            self.checked=True
            self.return_code=response["return_code"]
            self.available=response["value"]
            self.message=response["message"]

        elif self.type.upper() == 'DISK':
            logging.debug("Checking Disk")
            self.last_checked=str(datetime.now())
            response=getDiskStatus(self.environment,
                                   self.hosts,
                                   self.name)
            self.checked=True
            self.return_code=response["return_code"]
            self.available=response["value"]
            self.message=response["message"]
        else:
            log.debug("Invalid Application Type")
