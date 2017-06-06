#std imports
import logging
import httplib
import urllib
import urllib2
import cookielib
import socket
import hashlib
from datetime import datetime

log = logging.getLogger(__name__)

def sasLogon(environment,protocol,host,port,application,user,password,debug=False):

    log = logging.getLogger('check_sas.sasLogon()')
    log.debug("SAS Logon for WebApp: %s://%s:%s/%s initiated" % (protocol,host,port,application))
    headers = {"Content-Type": "text/plain","Accept": "text/plain","Connection":" keep-alive"}
    cas_endpoint='/SASLogon/v1/tickets/'
    AVAILABLE=False
    return_code=300
    message=""
    #Logon Code
    params_logon = urllib.urlencode({'username': user, 'password': password})
    #log.debug("checking staus of %s" % (application))
    try:

        log.debug("Establishing HTTPS connection : %s://%s:%s " % (protocol,host,port))
        conn = httplib.HTTPSConnection(host,port,timeout=60)
        #Rquest Start time
        conn.request("POST","/SASLogon/v1/tickets/",params_logon,headers)
        response = conn.getresponse()
        log.debug("Establised HTTPS connection : %s://%s:%s " % (protocol,host,port))
        response.read()

        return_code = response.status

        #Get Location
        if return_code == 201:
              location = response.getheader("Location")
              #Extract TGT from location
              lastSlash = location.rfind('/') + 1
              tgt = location[lastSlash:len(location)]
              service_url = "%s://%s:%s/%s/j_spring_cas_security_check" % (protocol,host,port,application)
              log.debug("Service URL: %s" % service_url)
              params = urllib.urlencode({'service': service_url})
              conn.request("POST", "%s%s" % (cas_endpoint, tgt) , params, headers=headers)
              response = conn.getresponse()
              return_code=response.status
              if return_code == 200:
                  service_ticket = response.read()
                  url="%s?ticket=%s" % (service_url, service_ticket)

                  log.debug("Successfully received service ticket for %s" % (application))
                  cj = cookielib.CookieJar()
                  no_proxy_support = urllib2.ProxyHandler({})
                  cookie_handler = urllib2.HTTPCookieProcessor(cj)
                  opener = urllib2.build_opener(no_proxy_support, cookie_handler, urllib2.HTTPHandler(debuglevel=1))
                  urllib2.install_opener(opener)

                  log.debug("Logging on to %s " % (application))
                  response = urllib2.urlopen(url)

                  return_code=response.getcode()
                  if return_code == 200:
                    log.debug("Logging on to %s successful" % (application))
                    AVAILABLE=True
                    message = "Ok"
                  else:
                    log.debug("Logging on to %s failed" % (application))
                    AVAILABLE=False
                  htmlresult = response.read()

                  logoffurl="/SASLogon/v1/tickets/" + tgt
                  conn.request("DELETE", logoffurl , headers=headers)
                  response = conn.getresponse()
                  response.read()

              else:
                  message = "Invalid response code %s for Service Ticket Request" % return_code
                  log.debug(message)
                  logoffurl="/SASLogon/v1/tickets/" + tgt
                  conn.request("DELETE", logoffurl , headers=headers)
                  response = conn.getresponse()
                  response.read()
        else:
              message = "Failed to get TGT return code is %d" % return_code
              location = ""
              tgt = ""
              conn.close()

    except httplib.BadStatusLine as e:
        log.debug("Bad Status Line %s" % e)
    except urllib2.HTTPError as httperr:
        return_code = httperr.code
        message = "HTTP Error %d" % return_code
        message = httperr.reason
        log.exception(httperr)
    except httplib.HTTPException as e:
        log.debug(e)
        return_code = e.errno
        message = "Failed to get TGT return code is %d" % return_code
        log.debug(message)
        #message=e
    except socket.error as socketmsg:
        log.debug("Socket Error Occurred host %s port %s" % (host,port))
        log.debug(socketmsg.errno)
        if socketmsg.errno == 111:
            message="Connection Refused"
        else:
            message=str(socketmsg)
            log.debug(socketmsg)
            #message="Socket error %d" % socketmsg.errno
        log.debug(socketmsg)
    except socket.gaierror as socketgamsg:
        if socketgamsg.errno == 111:
          message="Connection Refused"
        else:
          message="Socket error %d" % socketgamsg.errno
        log.debug(socketmsg)
    finally:
        if conn:
            conn.close()

    last_checked=str(datetime.now())
    service_id=hashlib.md5(host + application).hexdigest()

    output={"available":AVAILABLE,
            "return_code":return_code,
            "message":message,
            "type":"webapp",
            "service_id":service_id,
            "last_checked":last_checked
            }
    _status={host:{application:output}}
    log.debug("Status of %s: %s" % (application,_status))
    return _status
