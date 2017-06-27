import logging
import time
import threading
from datetime import datetime

#project
from check_sasweblogon import sasLogon
from check_sasserver import getsasserverstatus
from check_disk import getDiskStatus

log = logging.getLogger('Service')

class Service(object):
    def __init__(self,
                 environment_name,
                 environment_level,
                 group,
                 service,
                 type,
                 hosts,
                 port,
                 protocol,
                 user,
                 password,
                 debug=False,
                 ssh_private_key_filename='~/.ssh/id_rsa'):
        self.type=type
        self.environment_name=environment_name
        self.environment_level=environment_level,
        self.group=group
        self.service=service
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
        self.status={}
        self.message=''
        self.last_checked=None
        self.command_timeoutseconds=30
        self.running=False

        #Extract host from dictionary key
        if len(self.hosts) > 1:
            for hosts in  self.hosts:
                self.hosts_list.append(str(hosts))
        else:
            self.hosts_str=str(hosts.keys()[0])
            self.hosts_list.append(str(hosts.keys()[0]))

    def isAvailable(self):
        return self.available

    def __str__(self):
        return str(dict(self))

    def __iter__(self):
        # first start by grabbing the Class items
        #iters = dict((x,y) for x,y in Message.__dict__.items() if x[:2] != '__')
        iters={}

        combined_services={}
        service_desc={"type":self.type,
                      "group":self.group,
                      "port":self.port}
        for host in self.hosts_list:
            if host in combined_services:
                if not self.service in combined_services[host]:
                    combined_services[host][self.service]={}
            else:
                combined_services[host]={}
                combined_services[host][self.service]={}
            combined_services[host][self.service]=service_desc

        # then update the class items with the instance items
        iters.update(combined_services)

        # now 'yield' through the items
        for x,y in iters.items():
            yield x,y

    def getStatus(self):
        log = logging.getLogger('service.getStatus()')
        log.debug("Is debug enabled for service %s? %s" % (self.service,self.debug_boolean))
        hosts_list=[]
        hosts_str=''


        if self.type.upper() == 'WEBAPP':
            #response={"value":True|False,"return_code":return_code,"message":message}
            #log.debug("Checking WebApp: %s://%s:%s/%s" % (self.protocol,self.hosts,self.port,self.name))
            self.last_checked=str(datetime.now())
            log.debug("Get status for service %s" % self.service)
            self.status=sasLogon(self.environment_name,
                                 self.group,
                                 self.protocol,
                                 self.hosts_str,
                                 self.port,
                                 self.service,
                                 self.user,
                                 self.password,
                                 debug=self.debug_boolean)
            log.debug("Response from service %s type %s is %s " % (self.service,self.type.upper(),self.status))
            self.checked=True
        elif self.type.upper() == 'DISK':
            log.debug("Checking Disk")
            self.last_checked=str(datetime.now())
            self.status=getDiskStatus(self.environment_name,
                                      self.group,
                                      self.hosts_list,
                                      self.user,
                                      self.service,
                                      private_key=self.ssh_private_key_filename,
                                      debug=self.debug_boolean)
            log.debug("Response from service %s type %s is %s " % (self.service,self.type.upper(),self.status))
            self.checked=True
        elif self.type.upper() == 'SAS.SERVERS':
            log.debug("Checking SAS.SERVERS")
            self.last_checked=str(datetime.now())
            self.status=getsasserverstatus(self.environment_name,
                                           self.group,
                                           self.hosts_list,
                                           self.user,
                                           self.service,
                                           private_key=self.ssh_private_key_filename,
                                           debug=self.debug_boolean)
            log.debug("Response from service %s type %s is %s " % (self.service,self.type.upper(),self.status))
            self.checked=True
        else:
            log.debug("Invalid Application Type")