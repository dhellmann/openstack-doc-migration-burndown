#!/usr/bin/env python

import argparse
import base64
import collections
import time
import glob
import os
import ConfigParser
import json
from multiprocessing import Pool
import re

import requests
from requests.auth import HTTPDigestAuth

TOP = 'nova/api-ref/source'

PROJECT_SITE = "https://review.openstack.org/changes/"
DIFF_QUERY = "%s/revisions/current/patch"
QUERY = "q=project:openstack/nova+file:^api-ref/source/.*.inc+NOT+age:7d"
ATTRS = ("&o=CURRENT_REVISION&o=ALL_COMMITS&o=ALL_FILES&o=LABELS"
         "&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS")
URL = "%s?%s%s" % (PROJECT_SITE, QUERY, ATTRS)
DIFF_URL = PROJECT_SITE + DIFF_QUERY

PHASES = ['needs:method_verification', 'needs:parameter_verification',
          'needs:example_verification', 'needs:body_verification']

counts = collections.OrderedDict()
for phase in PHASES:
    counts[phase] = []
counts['done'] = []

files = []


def _parse_content(resp, debug=False):
    # slice out the "safety characters"
    if resp.content[:4] == ")]}'":
        content = resp.content[5:]
        if debug:
            print("Response from Gerrit:\n")
            print(content)
        return json.loads(content)
    elif ('X-FYI-Content-Encoding' in resp.headers and
          resp.headers['X-FYI-Content-Encoding'] == 'base64'):
        return base64.b64decode(resp.content)
    else:
        print resp
        return resp.content


def fetch_data(url, debug=False):
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    user = config.get('default', 'user')
    password = config.get('default', 'password')
    auth = HTTPDigestAuth(user, password)
    resp = requests.get(url, auth=auth)
    return _parse_content(resp, debug)


def _http_process(change):
    diff = fetch_data(change['url'])
    files = []
    fname = None
    for line in diff.split('\n'):
        m = re.match('--- a/api-ref/source/(.*.inc)$', line)
        if m:
            fname = m.group(1)
        m = re.match('-.. needs:(.*)', line)
        if m:
            tag = {'number': change['number'],
                   'filename': fname,
                   'tag': m.group(1)}
            files.append(tag)
    return files


def gather_reviews():
    data = fetch_data(URL)
    changes = []
    for change in data:
        if change['status'] != 'NEW':
            continue
        newchange = {}
        newchange['number'] = change['_number']
        newchange['url'] = DIFF_URL % change['id']
        changes.append(newchange)

    pool = Pool(processes=10)
    files = pool.map(_http_process, changes)
    relevant = []
    for f in files:
        if f:
            relevant.extend(f)
    return relevant


def update_review_list(files, updated):
    for fdata in files:
        updates = [x for x in updated if x['filename'] == fdata['filename']]
        for update in updates:
            what = "needs:%s" % update['tag']
            fdata[what] = update['number']


for fname in sorted(glob.glob("%s/*.inc" % TOP)):
    with open(fname) as f:
        fdata = {'filename': os.path.basename(fname)}
        content = f.readlines()
        done = True
        for key in PHASES:
            if ".. %s\n" % key in content:
                fdata[key] = "TODO"
                done = False
                counts[key].append(fname)
            else:
                fdata[key] = u"\u2713"
        if done:
            counts['done'].append(fname)
        files.append(fdata)

relevant = gather_reviews()
update_review_list(files, relevant)


with open("data.csv", "a") as f:
    f.write("%d,%d,%d,%d,%d\n" % (
        int(time.time()),
        len(counts['needs:method_verification']),
        len(counts['needs:parameter_verification']),
        len(counts['needs:example_verification']),
        len(counts['needs:body_verification'])))


with open("data.json", "w") as f:
    f.write(json.dumps(files))

with open("data.txt", "w") as f:
    FORMAT = "%-40s %10s %10s %10s %10s\n"
    f.write(FORMAT % ("File Name", "Method", "Param", "Example", "Body"))
    for fdata in files:
        f.write((FORMAT % (fdata['filename'],
                           fdata['needs:method_verification'],
                           fdata['needs:parameter_verification'],
                           fdata['needs:example_verification'],
                           fdata['needs:body_verification'])).encode('utf8'))
