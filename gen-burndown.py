#!/usr/bin/env python3

import csv
import collections
import time
import os
import configparser
import json

import requests
from requests.auth import HTTPDigestAuth

TOP = 'nova/api-ref/source'

PROJECT_SITE = "https://review.openstack.org/changes/"
QUERY = "q=topic:doc-migration"
URL = "%s?%s" % (PROJECT_SITE, QUERY)


def _parse_content(resp, debug=False):
    # slice out the "safety characters"
    if resp.content[:4] == b")]}'":
        content = resp.content[5:]
        if debug:
            print("Response from Gerrit:\n")
            print(content)
        return json.loads(content.decode('utf-8'))
    else:
        print('could not parse response')
        return resp.content


def fetch_data(url, debug=False):
    print('fetching {}'.format(url))
    config = configparser.ConfigParser()
    config.read('config.ini')
    user = config.get('default', 'user')
    password = config.get('default', 'password')
    auth = HTTPDigestAuth(user, password)
    resp = requests.get(url, auth=auth)
    return _parse_content(resp, debug)
    # return json.loads(_parse_content(resp, debug).decode('utf-8'))

observed_repos = set()
in_progress = 0

relevant = fetch_data(URL)
for review in relevant:
    if review['status'] == 'ABANDONED':
        continue
    observed_repos.add(review['project'])
    if review['status'] == 'MERGED':
        # Do not count this repo as in-progress
        continue
    in_progress += 1

with open('expected_repos.txt', 'r', encoding='utf-8') as f:
    expected_repos = set([line.strip() for line in f])

unseen_repos = expected_repos - observed_repos
not_started = len(unseen_repos)

print('Found {} changes in review'.format(in_progress))
print('Found {} repos not started'.format(not_started))

if not os.path.exists('data.csv'):
    with open('data.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(('date',
                         'Changes In Review',
                         'Repos Not Started', ))

with open('data.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow(
        (int(time.time()),
         in_progress,
         not_started,
        ),
    )

with open('data.json', 'w') as f:
    f.write(json.dumps([
        {'Changes In Review': repo}
        for repo in sorted(observed_repos)
    ]))
