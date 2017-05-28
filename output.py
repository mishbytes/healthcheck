import os
import logging
from jinja2 import Environment, FileSystemLoader

from config import healthcheckLogging

PATH = os.path.dirname(os.path.abspath(__file__))

DEFAUTL_CONSOLE_LOG_FILENAME='console.log'
def consoleLogging(filename=None):
    if filename:
        healthcheckLogging(filename=DEFAUTL_CONSOLE_LOG_FILENAME,default_level=DEFAUTL_LOGGING_LEVEL)
    else:
        healthcheckLogging(default_level=logging.DEBUG)

consoleLogging()

def render_template(context,template_dir='/tmp',template_filename='status.html.template'):
    TEMPLATE_ENVIRONMENT = Environment(
        autoescape=False,
        loader=FileSystemLoader(PATH),
        trim_blocks=False)
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


def create_status_html(path='/tmp',host='',time='',total_services=0,total_services_unavailable=0,services_status={}):
    log = logging.getLogger('output.create_status_html()')
    fname = path + '/' + "status.html"

    context = {
        'service_status_dicts': services_status,
        'total_services':total_services,
        'total_services_unavailable':total_services_unavailable,
        'report_title':'Health Check Report Executed from %s at %s' % (host,time)
    }
    log.debug("jinja2 context %s" % context)
    #
    with open(fname, 'w') as f:
        #html = render_template(context,template_dir=path,template_filename='status.html.template')
        html = render_template(context,template_dir=path,template_filename='status.html.template')
        #log.debug(html)
        log.debug("Written bad service report to %s" % fname)
        f.write(html)


def main():
    create_status_html(path=os.path.dirname(os.path.abspath(__file__)))


########################################

if __name__ == "__main__":
    main()
