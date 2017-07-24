#!/usr/bin/env python3

import csv
import collections
import time
import os
import configparser
import json
import sys

import requests
from requests.auth import HTTPDigestAuth
import yaml

PROJECT_SITE = "https://review.openstack.org/changes/"
QUERY = "q=topic:doc-migration"
URL = "%s?%s" % (PROJECT_SITE, QUERY)

INSTALL_TMPL = 'https://docs.openstack.org/{name}/{series}/install/index.html'
ADMIN_TMPL = 'https://docs.openstack.org/{name}/{series}/admin/index.html'
CONFIG_TMPL = 'https://docs.openstack.org/{name}/{series}/configuration/index.html'

ALL_URLS = [
    'https://docs.openstack.org/{name}/{series}/index.html',
]
URLS_BY_TYPE = {
    'service': [
        INSTALL_TMPL,
        ADMIN_TMPL,
        CONFIG_TMPL,
    ],
    'networking': [
        INSTALL_TMPL,
        CONFIG_TMPL,
    ],
}
URLS_BY_TYPE['baremetal'] = URLS_BY_TYPE['service'][:]

NOT_EXPECTED = {
    'vitrage': [ADMIN_TMPL, CONFIG_TMPL],
}


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
    start = None
    more_changes = True
    config = configparser.ConfigParser()
    config.read('config.ini')
    user = config.get('default', 'user')
    password = config.get('default', 'password')
    auth = HTTPDigestAuth(user, password)
    response = []
    to_fetch = url
    while more_changes:
        if start:
            to_fetch = url + '&start={}'.format(start)
        print('fetching {}'.format(to_fetch))
        resp = requests.get(to_fetch, auth=auth)
        content = _parse_content(resp, debug)
        response.extend(content)
        more_changes = content[-1].get('_more_changes', False)
        start = len(content)
        start = (start or 0) + len(content)
    return response

observed_repos = set()
in_progress = set()

relevant = fetch_data(URL)
print('Found {} reviews'.format(len(relevant)))
for review in relevant:
    if review['status'] == 'ABANDONED':
        continue
    observed_repos.add(review['project'])
    if review['status'] == 'MERGED':
        # Do not count this repo as in-progress
        continue
    in_progress.add(review['project'])

with open('expected_repos.txt', 'r', encoding='utf-8') as f:
    expected_repos = set([line.strip() for line in f])

unseen_repos = expected_repos - observed_repos
not_started = len(unseen_repos)

with open('../openstack-manuals/www/project-data/latest.yaml', 'r', encoding='utf-8') as f:
    doc_projects = yaml.safe_load(f.read())


def _check_url(url):
    "Return True if the URL exists, False otherwise."
    # print('Checking {} '.format(url), end='')
    try:
        resp = requests.head(url)
    except requests.exceptions.TooManyRedirects:
        result = False
    result = (resp.status_code // 100) == 2
    # if not result:
    #     print('MISSING')
    # else:
    #     print()
    return result


missing_urls = []
for project in doc_projects:
    to_check = ALL_URLS[:]
    to_check.extend(URLS_BY_TYPE.get(project['type'], []))
    for url_tmpl in to_check:
        if url_tmpl in NOT_EXPECTED.get(project['name'], []):
            continue
        url = url_tmpl.format(
            series='latest',
            name=project['name'],
        )
        if not _check_url(url):
            missing_urls.append(url)
missing_urls.sort()

print('Found {} changes in review'.format(len(in_progress)))
print('Found {} repos not started'.format(not_started))
print('Found {} missing URLs'.format(len(missing_urls)))

if not os.path.exists('data.csv'):
    with open('data.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(('date',
                         'Changes In Review',
                         'Repos Not Started',
                         'Missing URLs'))

with open('data.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow(
        (int(time.time()),
         len(in_progress),
         not_started,
         len(missing_urls),
        ),
    )

with open('data.json', 'w') as f:
    f.write(json.dumps([
        {'Changes In Review': repo}
        for repo in sorted(in_progress)
    ]))

with open('notstarted.json', 'w') as f:
    f.write(json.dumps([
        {'Repos Not Started': repo}
        for repo in sorted(unseen_repos)
    ]))

with open('missing_urls.json', 'w') as f:
    f.write(json.dumps([
        {'Missing URLs': u}
        for u in missing_urls]
    ))
