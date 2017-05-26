class ServiceStatus(object):
    def __init__(self,hosts,application,application_type,type,value,timestamp,message):
        self.application=application
        self.application_type=application_type
        self.type=type
        self.value=value
        self.message=message
        self.timestamp=timestamp
        self.hosts=hosts

    def asDict(self):
        _dict_status={}
        _dict_status["hosts"]=self.hosts
        _dict_status["application_type"]=self.application_type
        _dict_status["application"]=self.application
        _dict_status["type"]=self.type
        _dict_status["value"]=self.value
        _dict_status["message"]=self.message
        _dict_status["timestamp"]=self.timestamp
        return _dict_status
