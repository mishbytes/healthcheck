import logging
import time
import threading
from datetime import datetime

#project
from check_sas import sasLogon
from check_disk import getDiskStatus

log = logging.getLogger('Service')

class Service(object):
    def __init__(self,environment,level,name,type,hosts,port,protocol,user,password,debug=False,ssh_private_key_filename='~/.ssh/id_rsa'):
        self.type=type
        self.environment=environment
        self.level=environment
        self.name=name
        self.type=type
        self.hosts_list=[]
        self.hosts=hosts
        self.hosts_str='unknown'
        self.port=port
        self.protocol=protocol
        self.user=user
        self.password=password
        self.debug_boolean=debug
        self.ssh_private_key_filename=ssh_private_key_filename

        #Status keys
        self.checked=False
        self.available=False
        self.return_code=9999
        self.message=''
        self.last_checked=None
        self.command_timeoutseconds=30

        #Extract host from dictionary key
        if len(self.hosts) > 1:
            for hosts in  self.hosts:
                self.hosts_list.append(str(hosts))
        else:
            self.hosts_str=str(hosts.keys()[0])


    def isAvailable(self):
        return self.available

    def status(self):
        log = logging.getLogger('Service.status()')
        log.debug("Is debug enabled for service %s? %s" % (self.name,self.debug_boolean))
        hosts_list=[]
        hosts_str=''


        if self.type.upper() == 'WEBAPP':
            #response={"value":True|False,"return_code":return_code,"message":message}
            #log.debug("Checking WebApp: %s://%s:%s/%s" % (self.protocol,self.hosts,self.port,self.name))
            self.last_checked=str(datetime.now())
            response=sasLogon(self.environment,
                              self.protocol,
                              self.hosts_str,
                              self.port,
                              self.name,
                              self.user,
                              self.password,
                              debug=self.debug_boolean)
            self.checked=True
            self.return_code=response["return_code"]
            self.available=response["value"]
            self.message=response["message"]

        elif self.type.upper() == 'DISK':
            logging.debug("Checking Disk")
            self.last_checked=str(datetime.now())
            response=getDiskStatus(self.environment,
                                   self.hosts_list,
                                   self.user,
                                   self.name,
                                   private_key=self.ssh_private_key_filename,
                                   debug=self.debug_boolean)
            self.checked=True
            self.return_code=response["return_code"]
            self.available=response["value"]
            self.message=response["message"]
        else:
            log.debug("Invalid Application Type")
