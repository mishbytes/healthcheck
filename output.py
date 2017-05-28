import os
from jinja2 import Environment, FileSystemLoader

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(PATH),
    trim_blocks=False)


def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


def create_status_html():
    fname = "status.html"
    service_status_dicts = [{'myhostname.com':[
                                                {
                                                    'service': '/tmp',
                                                    'type':'disk',
                                                    'status': True,
                                                    'last_checked':'01-01-2006 19:34:30',
                                                    'additional_info':'Network Timeout'
                                                    },
                                                {
                                                    'service': '/tmp2',
                                                    'type':'disk',
                                                    'status': True,
                                                    'last_checked':'01-01-2006 19:34:30',
                                                    'additional_info':'Network Timeout'
                                                    },
                                                {
                                                    'service': '/tmp3',
                                                    'type':'disk',
                                                    'status': True,
                                                    'last_checked':'01-01-2006 19:34:30',
                                                    'additional_info':'Network Timeout'
                                                    }
                                            ]
                            },
                            {'myhostname2.com':[
                                                    {
                                                        'service': '/tmp',
                                                        'type':'disk',
                                                        'status': True,
                                                        'last_checked':'01-01-2006 19:34:30',
                                                        'additional_info':'Network Timeout'
                                                        },
                                                    {
                                                        'service': '/tmp2',
                                                        'type':'disk',
                                                        'status': True,
                                                        'last_checked':'01-01-2006 19:34:30',
                                                        'additional_info':'Network Timeout'
                                                        },
                                                    {
                                                        'service': '/tmp3',
                                                        'type':'disk',
                                                        'status': True,
                                                        'last_checked':'01-01-2006 19:34:30',
                                                        'additional_info':'Network Timeout'
                                                        }
                                                ]
                                                    }
                            ]
    context = {
        'service_status_dicts': service_status_dicts,
        'total_services':3,
        'total_service_unavailable':2,
        'report_title':'Health Check Report Executed from Hostname at 01-01-2006 19:34:30'
    }
    #
    with open(fname, 'w') as f:
        html = render_template('status.html.template', context)
        f.write(html)


def main():
    create_status_html()

########################################

if __name__ == "__main__":
    main()
