#!/usr/bin/env python
# encoding: utf-8
'''
Gandi v5 LiveDNS - DynDNS Update via REST API and CURL/requests

@author: cave
License GPLv3
https://www.gnu.org/licenses/gpl-3.0.html

Created on 13 Aug 2017
http://doc.livedns.gandi.net/ 
http://doc.livedns.gandi.net/#api-endpoint -> https://dns.gandi.net/api/v5/
'''

import requests, json
import config
import argparse
import subprocess


def get_dynip(ifconfig_provider):
    ''' find out own IPv4 at home <-- this is the dynamic IP which changes more or less frequently
    similar to curl ifconfig.me/ip, see example.config.py for details to ifconfig providers 
    '''
    result=[]
    r, _ = subprocess.Popen(['curl', '-s', '-4', ifconfig_provider], shell=False, stdout=subprocess.PIPE).communicate()
    print('Checking dynamic IP: ' , r.decode("utf-8").strip('\n'))
    result.append(r.decode("utf-8").strip('\n'))
    r, _ = subprocess.Popen(['curl', '-s', '-6', ifconfig_provider], shell=False, stdout=subprocess.PIPE).communicate()
    print('Checking dynamic IP: ' , r.decode("utf-8").strip('\n'))
    result.append(r.decode("utf-8").strip('\n'))
    return result

def get_uuid():
    ''' 
    find out ZONE UUID from domain
    Info on domain "DOMAIN"
    GET /domains/<DOMAIN>:
        
    '''
    url = config.api_endpoint + '/domains/' + config.domain
    u = requests.get(url, headers={"X-Api-Key":config.api_secret})
    json_object = json.loads(u._content)
    if u.status_code == 200:
        return json_object['zone_uuid']
    else:
        print('Error: HTTP Status Code ', u.status_code, 'when trying to get Zone UUID')
        print(json_object['message'])
        exit()

def get_dnsip(uuid):
    ''' find out IP from first Subdomain DNS-Record
    List all records with name "NAME" and type "TYPE" in the zone UUID
    GET /zones/<UUID>/records/<NAME>/<TYPE>:
    
    The first subdomain from config.subdomain will be used to get   
    the actual DNS Record IP
    '''
    url = config.api_endpoint+ '/zones/' + uuid + '/records/' + config.subdomains[0] + '/'
    result=[]
    for record in ["A", "AAAA"]:
        headers = {"X-Api-Key":config.api_secret}
        u = requests.get(url + record, headers=headers)
        if u.status_code == 200:
            json_object = json.loads(u._content)
            print('Checking IP from DNS Record' , config.subdomains[0], ':', json_object['rrset_values'][0].strip('\n'))
            result.append(json_object['rrset_values'][0].strip('\n'))
        else:
            print('Error: HTTP Status Code ', u.status_code, 'when trying to get IP from subdomain', config.subdomains[0])
            print(json_object['message'])
            result.append(None)
    return result

def update_records(uuid, dynIPs, subdomain):
    ''' update DNS Records for Subdomains 
        Change the "NAME"/"TYPE" record from the zone UUID
        PUT /zones/<UUID>/records/<NAME>/<TYPE>:
        curl -X PUT -H "Content-Type: application/json" \
                    -H 'X-Api-Key: XXX' \
                    -d '{"rrset_ttl": 10800,
                         "rrset_values": ["<VALUE>"]}' \
                    https://dns.gandi.net/api/v5/zones/<UUID>/records/<NAME>/<TYPE>
    '''
    result = 0
    for dynIP in dynIPs:
        if dynIP == None:
            continue
        if ":" in dynIP:
            record = "AAAA"
        else:
            record = "A"
        url = config.api_endpoint+ '/zones/' + uuid + '/records/' + subdomain + '/' + record
        payload = {"rrset_ttl": config.ttl, "rrset_values": [dynIP]}
        headers = {"Content-Type": "application/json", "X-Api-Key":config.api_secret}
        u = requests.put(url, data=json.dumps(payload), headers=headers)
        json_object = json.loads(u._content)

        if u.status_code == 201:
            print('Status Code:', u.status_code, ',', json_object['message'], ', ', record, ' RR updated for', subdomain)
            result = result + 1
        else:
            print('Error: HTTP Status Code ', u.status_code, 'when trying to update IP from subdomain', subdomain)
            print(json_object['message'])
    return result > 0


def main(force_update, verbosity):

    if verbosity:
        print("verbosity turned on - not implemented by now")

        
    #get zone ID from Account
    uuid = get_uuid()
   
    #compare dynIP and DNS IP 
    dynIPs = get_dynip(config.ifconfig)
    dnsIP, dnsIP6 = get_dnsip(uuid)
    
    if force_update:
        print("Going to update/create the DNS Records for the subdomains")
        for sub in config.subdomains:
            update_records(uuid, dynIPs, sub)
    else:
        try:
            dynIPs.remove(dnsIP)
            dynIPs.remove(dnsIP6)
        except ValueError:
            pass
        if dynIPs:
            print("IP Address Mismatch - going to update the DNS Records for the subdomains with new IP", dynIPs)
            for sub in config.subdomains:
                update_records(uuid, dynIPs, sub)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', help="increase output verbosity", action="store_true")
    parser.add_argument('-f', '--force', help="force an update/create", action="store_true")
    args = parser.parse_args()
        
        
    main(args.force, args.verbose)
