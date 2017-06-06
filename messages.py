import json
import hashlib
import logging
import time

class Message(object):
    def __init__(self,json_object):
        self.host="unknown"
        self.name="unknown"
        self.service_id="unknown"
        self.available=False
        self.return_code=-1
        self.last_checked="unknown"
        self.message="unknown"
        self.type="unknown"
        #if isJson(message_json):
            #convert json string to json dict
        #json_object = json.loads(message_json)
        if isinstance(json_object, dict):
            for host,service in json_object.iteritems():
                #depth 0 is hosts
                self.host=host
                #depth 1 is service name
                for name,value in service.iteritems():
                    self.name=name
                    self.service_id=hashlib.md5(host + name).hexdigest()
                    for property in value:
                        #depth 2
                        if "AVAILABLE" == property.upper():
                            self.available=value[property]
                        elif "RETURN_CODE" == property.upper():
                            self.return_code=value[property]
                        elif "LAST_CHECKED" == property.upper():
                            self.last_checked=value[property]
                        elif "MESSAGE" == property.upper():
                            self.message=value[property]
                        elif "TYPE" == property.upper():
                            self.type=value[property]

        else:
            raise ValueError('Non-dictionary value not allowed')


    def __add__(self,new):
        combined_dict={}
        print self
        combined_dict.update(str(self))
        #combined_dict.update(str(new))
        return self


    def __str__(self):
        return str(dict(self))

    def __iter__(self):
        # first start by grabbing the Class items
        #iters = dict((x,y) for x,y in Message.__dict__.items() if x[:2] != '__')
        iters={}

        # then update the class items with the instance items
        iters.update({self.host:{self.name:{"service_id":self.service_id,
                                          "available":self.available,
                                          "return_code":self.return_code,
                                          "last_checked":self.last_checked,
                                          "message":self.message,
                                          "type":self.type,

                                          }
                               }
                    })
        # now 'yield' through the items
        for x,y in iters.items():
            yield x,y
    __repr__ = __str__

class Messages(object):
    def __init__(self):
        self.messages=[]
        self.messages_to_alert={}
        self.messages_alert_timer={}

    def add(self,message):
        self.messages.append(Message(message))

    def getMessages(self):
        return self.messages

    def reset(self):
        self.messages=[]
        self.messages_to_alert=[]

    def getUnavailableAsDict(self):
        unavailable_dict={}
        unavailable_count=0
        for message in self.messages:
            if not message.available:
                unavailable_count+=1
                unavailable_dict.update(dict(message))
        return unavailable_count,unavailable_dict

    def getAlertMessagesAsDict(self,alert_lifetime=7200):
        log = logging.getLogger('messages.getAlertMessagesAsDict()')
        alert_messages={}
        alert_count=0
        alert_found=True
        for message in self.messages:
            if not message.available:
                if message.service_id in self.messages_alert_timer:
                    last_alert_time=self.messages_alert_timer[message.service_id]
                    age_of_last_alert=time.time() - last_alert_time
                    if age_of_last_alert > alert_lifetime:
                        log.debug("Age of Alert for service %s exceeded alert life time %s" % (message.name,alert_lifetime))
                        log.debug("Add service to alert list %s" % message.name)
                        alert_count+=1
                        self.messages_alert_timer[message.service_id]=time.time()
                        alert_found=True
                        alert_messages.update(dict(message))
                    else:
                        log.debug("Last Alert for service %s not expired " % message.name)
                else:
                    log.debug("This first alert for service %s since agent start" % message.name)
                    alert_count+=1
                    self.messages_alert_timer[message.service_id]=time.time()
                    alert_found=True
                    alert_messages.update(dict(message))

        log.debug(json.dumps(self.messages_alert_timer,indent=4))
        log.debug("Following services will be alerted")
        log.debug(json.dumps(alert_messages,indent=4))

        return alert_count,alert_messages

    def __len__(self):
        return len(self.messages)

    def __str__(self):
        combined_messages={}
        for message in self.messages:
            combined_messages.update(dict(message))
        return json.dumps(combined_messages,indent=4)

    #convert list of message objects to dictionary
    def __iter__(self):
        # first start by grabbing the Class items
        #iters = dict((x,y) for x,y in Messages.__dict__.items() if x[:2] != '__')

        iters={}

        #combine all message objects as dict
        combined_messages={}
        for message in self.messages:
            combined_messages.update(dict(message))

        # then update the class items with the instance items
        iters.update(combined_messages)
        # now 'yield' through the items
        for x,y in iters.items():
            yield x,y



if __name__ == '__main__':
    myjson={"testserver": {
                               "SASStudio": {
                                               "available": False,
                                               "return_code": 300,
                                               "last_checked": "2017-06-05 11:56:42.181631",
                                               "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                               "message": "[Errno 8] nodename nor servname provided, or not known",
                                               "type": "webapp"
                                             }
                            }
              }
    myjson2={"testserver2": {
                               "SASStudio": {
                                               "available": False,
                                               "return_code": 300,
                                               "last_checked": "2017-06-05 11:56:42.181631",
                                               "service_id": "3e460a2bbbe7f0f29b13c7d910959fd3",
                                               "message": "[Errno 8] nodename nor servname provided, or not known",
                                               "type": "webapp"
                                             }
                            }
              }
    try:
        cls3=Messages()
        cls3.add(myjson)
        cls3.add(myjson2)
    except ValueError as e:
        print "cls1 not created: %s" % e
    else:
        #print "cls1 created"
        #print dict(cls1)
        #print dict(cls2)
        print json.dumps(dict(cls3),indent=6)


    #print json.dumps(cls1)
