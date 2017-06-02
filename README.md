## HealthCheck Agent

#### Reports:
* SAS Web application Authentication status
* sas.servers status
* Unix Directory (e.g. /sasconfig) status

#### Requirements

* If installing dependent modules from soucre, the following modules are required.
	* yum install python-devel.x86_64
	* yum install gcc
* Required Distributions
	* ecdsa-0.13
	* pycrypto-2.6.1
	* paramiko-1.18.2 (paramiko >= 2.0 not supported)
	* Fabric-1.13.2
	* jinj2
	* markupsafe (Required by Jinja2)
