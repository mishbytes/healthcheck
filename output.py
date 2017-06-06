import os
import logging
import json
from jinja2 import Environment, FileSystemLoader


def render_template(context,template_dir='/tmp',template_filename='status.html.template'):
    TEMPLATE_ENVIRONMENT = Environment(
        autoescape=False,
        loader=FileSystemLoader(template_dir),
        trim_blocks=False)
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


def generateStatusHtmlPage(path='/tmp',host='',time='',
                           total_services=0,
                           total_services_unavailable=0,
                           alerts_count_for_email=0,
                           hosts_friendlyname={},
                           services_status={},
                           reporter_responsetime=0):
    log = logging.getLogger('output.generateStatusHtmlPage()')
    fname = path + '/' + "status.html"

    html=None
    context = {
        'service_status_dicts': services_status,
        'total_services':total_services,
        'total_services_unavailable':total_services_unavailable,
        'alerts_count_for_email':alerts_count_for_email,
        'hosts_friendlyname':hosts_friendlyname,
        'report_title':'Health Check Report Executed on %s took %s seconds' % (host,reporter_responsetime)
    }
    log.debug("jinja2 context %s" % json.dumps(context,indent=4))
    #
    #with open(fname, 'w') as f:
        #html = render_template(context,template_dir=path,template_filename='status.html.template')
        #html = render_template(context,template_dir=path,template_filename='status.html.template')
        #log.debug(html)
        #log.debug("Written bad service report to %s" % fname)
        #f.write(html)
    try:
        html = render_template(context,template_dir=path,template_filename='status.html.template')
    except Exception as e:
        log.error("Error occurred while generating HTML")
        log.exception(e)
    return html


#def main():
#    generateStatusHtmlPage(path=os.path.dirname(os.path.abspath(__file__)))


########################################

#if __name__ == "__main__":
#    main()
