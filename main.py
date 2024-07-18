"""Locally Significant Certificate (LSC) expiration monitoring and automatic renewal using the CUCM AXL API.

Copyright (c) 2024 Cisco and/or its affiliates.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import requests, os, datetime, time, sys
from bs4 import BeautifulSoup
from requests import Session
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from lxml import etree
from zeep import Client, Settings, Plugin
from zeep.transports import Transport
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin

load_dotenv()

DEBUG = os.getenv("DEBUG") == "True"

class MyLoggingPlugin(Plugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        if not DEBUG:
            return

        # Format the request body as pretty printed XML
        xml = etree.tostring(envelope, pretty_print=True, encoding="unicode")

        print(f"\nRequest\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}")

    def ingress(self, envelope, http_headers, operation):
        if not DEBUG:
            return

        # Format the response body as pretty printed XML
        xml = etree.tostring(envelope, pretty_print=True, encoding="unicode")

        print(f"\nResponse\n-------\nHeaders:\n{http_headers}\n\nBody:\n{xml}")

def run():
    print(f'Connecting to CUCM ({os.getenv("CUCM_PUBLISHER")})...', end ="")

    session = Session()

    session.verify = False
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )

    session.auth = HTTPBasicAuth(os.getenv("AXL_USERNAME"), os.getenv("AXL_PASSWORD"))
    transport = Transport(session=session, timeout=10)
    settings = Settings(strict=False, xml_huge_tree=True)

    history = HistoryPlugin()
    plugin = [MyLoggingPlugin(), history] if DEBUG else [history]

    WDSL_file = f'AXLAPI{os.getenv("AXL_VER")}.wsdl'
    client = Client(f'{WDSL_file}', settings=settings, transport=transport, plugins=plugin)

    service = client.create_service(
        '{http://www.cisco.com/AXLAPIService/}AXLAPIBinding',
        f'https://{ os.getenv("CUCM_PUBLISHER") }:8443/axl/')

    sql = 'select name, lscvaliduntil, pkid from device where lscvaliduntil > 0'

    try:
        resp = service.executeSQLQuery(sql)
        print('SUCCESS')
    except Fault as err:
        print(f'AXL error: executeSQLQuery:{err}')
    else:
        response_xml = etree.tostring(history.last_received["envelope"], encoding="unicode", pretty_print=True)

    soup = BeautifulSoup(response_xml, 'lxml')
    #print(soup.prettify())

    d = {}
    for entry in soup.find_all('row'):
        name = entry.find('name').text
        lsc_expire = int(entry.find('lscvaliduntil').text)
        pkid = entry.find('pkid').text
        d[name] = {'lsc_expire':lsc_expire,'pkid':pkid}

    now = int(time.time())
    renew_before_seconds = int(os.getenv("LSC_RENEW_BEFORE_DAYS")) * 24*60*60
    end_date = datetime.datetime.fromtimestamp(now + renew_before_seconds).strftime('%m-%d-%Y')

    nothing_found = True
    print(f'Checking for LSCs expiring on or before {end_date}')
    phone_to_update_lsc = {}
    for key,value in d.items():
        if (d[key]['lsc_expire'] - renew_before_seconds) <= now:
            #renew cert
            print(f"{key} ({d[key]['pkid']}) expires on {datetime.datetime.fromtimestamp(d[key]['lsc_expire']).strftime('%m-%d-%Y')}")
            phone_to_update_lsc[key] = d[key]['pkid']
            nothing_found = False

    if nothing_found:
        print(f'No phone LSCs expiring on or before {end_date}, nothing to do')

    for phone,pkid in phone_to_update_lsc.items():
        ### applyPhone (apply config) after setting to install/upgrade
        FinishBy = datetime.datetime.fromtimestamp(now + renew_before_seconds).strftime('%Y:%m:%d:%H:00')  #2024:08:22:12:00
        sql_update = f"update device set tkcertificatestatus=2, tkCertificateOperation=2, UpgradeFinishTime='{FinishBy}' where pkid='{pkid}'"
        ### uses the CAPF authentication mode of the device security profile applied to the phone

        try:
            resp = service.executeSQLUpdate(sql_update)
        except Fault as err:
            print(f'AXL error: executeSQLQuery:{err}')
        else:
            try:
                resp = service.applyPhone(name=phone)
            except Fault as err:
                print(f'AXL error: executeSQLQuery:{err}')
            else:
                response_xml = etree.tostring(history.last_received["envelope"], encoding="unicode", pretty_print=True)
                print(f"Certificate (LSC) update sent to {phone}")

def help():
    return 'Usage: python main.py\n'\
           'Update the .env file to change parameters:\n'\
           '- CUCM_PUBLISHER\n- AXL_VER\n- AXL_USERNAME\n- AXL_PASSWORD\n'\
           '- LSC_RENEW_BEFORE_DAYS\n- DEBUG'


if __name__ == '__main__':
    try:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print(help())
        else:
            run()
    except IndexError:
        run()