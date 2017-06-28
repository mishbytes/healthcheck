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

def full_status_html(template_path,
                      summary_status,
                      all_messages,
                      environment="Default"):

    summary_html=""
    log = logging.getLogger('output.full_status_html()')
    jinja2_context={'environment':environment,
                    'summary':summary_status,
                    'all_messages':all_messages}
    log.debug("jinja2 context %s" % json.dumps(jinja2_context,indent=4))
    try:
        summary_html = render_template(jinja2_context,
                                       template_dir=template_path,
                                       template_filename='summary.html.template')
    except Exception as e:
        log.error("Error occurred while generating HTML")
        log.exception(e)
        return None

    log.debug("HTML Output: \n %s"  % summary_html)

    return summary_html

def alert_html(template_path,
                      summary_status,
                      all_messages,
                      environment="Default"):

    summary_html=""
    log = logging.getLogger('output.full_status_html()')
    jinja2_context={'environment':environment,
                    'summary':summary_status,
                    'all_messages':all_messages}
    log.debug("jinja2 context %s" % json.dumps(jinja2_context,indent=4))
    try:
        summary_html = render_template(jinja2_context,
                                       template_dir=template_path,
                                       template_filename='alert.html.template')
    except Exception as e:
        log.error("Error occurred while generating HTML")
        log.exception(e)
        return None

    log.debug("HTML Output: \n %s"  % summary_html)

    return summary_html


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    messages_raw_json={"testserver": {
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

                            }
              }
    messages_summary_json= {u'Storage':{'bad': 6, 'good': 0},
                       u'SAS Web Applications':{'bad': 2, 'good': 0},
                       u'SAS Metadata Services': {'bad': 1, 'good': 0}
                       }

    try:
        from config import gethtmltemplatedir
        full_status_html(gethtmltemplatedir(),messages_summary_json,messages_raw_json)
    except Exception as e:
        print e
