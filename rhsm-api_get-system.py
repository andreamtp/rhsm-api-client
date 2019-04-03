#!/usr/bin/env python3
#
# rhsm-api_get-systems.py
#
# Copyright (C) 2019 Antonio Romito
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Please refer to the following bugzilla for more info:
# <https://bugzilla.redhat.com/show_bug.cgi?id=1673170>
#
# usage: rhsm-api_get-systems.py [-h] -u USERNAME -p PASSWORD -c CLIENT_ID -s
#                                CLIENT_SECRET -o OUTPUT_CSV
#
# RHSM API implementation
#
# optional arguments:
#   -h, --help            show this help message and exit
#   -u USERNAME, --username USERNAME
#                         Red Hat customer portal username
#   -p PASSWORD, --password PASSWORD
#                         Red Hat customer portal password
#   -c CLIENT_ID, --client_id CLIENT_ID
#                         Red Hat customer portal API Key Client ID
#   -s CLIENT_SECRET, --client_secret CLIENT_SECRET
#                         Red Hat customer portal API Key Client Secret
#   -o OUTPUT_CSV, --output_csv OUTPUT_CSV
#                         Output CSV file
#
import requests
import csv
import argparse
import time
from oauthlib.oauth2 import LegacyApplicationClient
from oauthlib.oauth2 import TokenExpiredError
from requests_oauthlib import OAuth2Session


class Systems:
    def __init__(self, pagination, body):
        self.pagination = pagination
        self.body = body

    def get_body(self):
        return self.body

    def get_count(self):
        return self.pagination['count']

    def get_limit(self):
        return self.pagination['limit']

    def get_offset(self):
        return self.pagination['offset']


class System:
    def __init__(self, entitlement_count, entitlement_status, errata_counts, href, last_checkin, name, stype, uuid):
        self.entitlementCount = entitlement_count
        self.entitlementStatus = entitlement_status
        self.errataCounts = errata_counts
        self.href = href
        self.lastCheckin = last_checkin
        self.name = name
        self.type = stype
        self.uuid = uuid

        self.securityCount = None
        self.bugfixCount = None
        self.enhancementCount = None

        if self.errataCounts is not None:
            self.set_errata_counts()
        else:
            self.securityCount = 0
            self.bugfixCount = 0
            self.enhancementCount = 0


    def set_errata_counts(self):
        self.securityCount = self.errataCounts['securityCount']
        self.bugfixCount = self.errataCounts['bugfixCount']
        self.enhancementCount = self.errataCounts['enhancementCount']

    def print_system_to_csv(self, csv_filename):
        with open(csv_filename, 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter=',')
            csv_writer.writerow([self.name, self.uuid, self.enhancementCount, self.type, "Not Available",
                                 self.entitlementStatus, self.lastCheckin, self.securityCount, self.bugfixCount,
                                 self.enhancementCount])

    def __repr__(self):
        return ('Name: %s UUID: %s Subscriptions Attached: %d Type: %s Cloud Provider: %s Status: %s '
                'Last Check in: %s Security Advisories: %d Bug Fixes: %d Enhancements: %d' %
                (self.name, self.uuid, self.enhancementCount, self.type, "Not Available", self.entitlementStatus,
                 self.lastCheckin, self.securityCount, self.bugfixCount, self.enhancementCount))


class AuthorizationCode:
    TOKEN_URL = 'https://sso.redhat.com/auth/realms/3scale/protocol/openid-connect/token'

    def __init__(self, username, password, client_id, client_secret, token=None):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token

        self.session = OAuth2Session(client=LegacyApplicationClient(client_id=self.client_id))

    def fetch_token(self):
        self.token = self.session.fetch_token(token_url=self.TOKEN_URL, username=self.username, password=self.password,
                                              client_id=self.client_id, client_secret=self.client_secret)
        return self.token

    def refresh_token(self):
        self.token = self.session.refresh_token(token_url=self.TOKEN_URL, client_id=self.client_id,
                                                client_secret=self.client_secret)
        return self.token


class Portal:
    API_URL = 'https://api.access.redhat.com/management/v1/'

    def __init__(self, auth=None):
        self.auth = auth

    def _get(self, *endpoint, params=None):
        endpoint = '/'.join(endpoint)
        print(time.ctime() + ' - Starting request: %s with params: %s ' % (self.API_URL + endpoint, params))
        if self.auth:
            try:
                t1 = time.time()
                response = self.auth.session.get(self.API_URL + endpoint, params=params)
                t2 = time.time()
            except TokenExpiredError:
                print(time.ctime() + ' - Token has expired. Refreshing token...')
                self.auth.refresh_token()
                t1 = time.time()
                response = self.auth.session.get(self.API_URL + endpoint, params=params)
                t2 = time.time()
        else:
            t1 = time.time()
            response = requests.get(self.API_URL + endpoint, params=params)
            t2 = time.time()
        print(time.ctime() + ' - The Round Trip Time for %s is %s' % (response.url, str(t2 - t1)))

        return response.json()

    def systems(self, limit, offset):
        payload = {'limit': limit, 'offset': offset}
        json = self._get('systems', params=payload)
        return json


def main():
    parser = argparse.ArgumentParser(description="RHSM API implementation")
    parser.add_argument("-u", "--username", help="Red Hat customer portal username", required=True)
    parser.add_argument("-p", "--password", help="Red Hat customer portal password", required=True)
    parser.add_argument("-c", "--client_id", help="Red Hat customer portal API Key Client ID", required=True)
    parser.add_argument("-s", "--client_secret", help="Red Hat customer portal API Key Client Secret", required=True)
    parser.add_argument("-o", "--output_csv", help="Output CSV file", required=True)

    args = parser.parse_args()

    total_count = 0
    all_systems = list()

    auth = AuthorizationCode(args.username, args.password, args.client_id, args.client_secret)
    auth.fetch_token()
    portal = Portal(auth)

    limit = 100
    offset = 0

    while True:
        this_systems_json = portal.systems(limit, offset)
        this_systems = Systems(this_systems_json['pagination'], this_systems_json['body'])
        if this_systems.get_count() != 0:
            total_count = total_count + this_systems.get_count()
            current_offset = offset
            offset = offset + limit
            for system in this_systems.get_body():
                if 'errataCounts' not in system:
                    system['errataCounts'] = None
                if 'lastCheckin' not in system:
                    system['lastCheckin'] = None

                this_system = System(system['entitlementCount'], system['entitlementStatus'], system['errataCounts'],
                                     system['href'], system['lastCheckin'], system['name'], system['type'],
                                     system['uuid'])

                this_system.print_system_to_csv(args.output_csv)
                all_systems.append(this_system)
        else:
            break

    print(time.ctime() + " - Total Number of systems in list: %d" % len(all_systems))
    print(time.ctime() + " - Total Number of systems from count: %d" % total_count)


if __name__ == "__main__":
    main()
