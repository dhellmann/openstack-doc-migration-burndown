#!/usr/bin/env python

# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import ConfigParser
import json

import requests
from requests.auth import HTTPDigestAuth

PROJECT_SITE = "https://review.openstack.org/changes/"
QUERY = "q=project:openstack/nova+file:api-ref+NOT+age:10d"
ATTRS = ("&o=CURRENT_REVISION&o=ALL_COMMITS&o=ALL_FILES&o=LABELS"
         "&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS")
URL = "%s?%s%s" % (PROJECT_SITE, QUERY, ATTRS)


def parse_args():
    parser = argparse.ArgumentParser(description='Get review stats for sprint')
    parser.add_argument('-s', '--show-stats', action='store_true',
                        dest="show_stats",
                        help='show stats of merged patches',
                        default=True)
    parser.add_argument('-d', '--debug', action='store_true',
                        dest="debug",
                        default=False)
    parser.add_argument('-r', '--show-reviews', action='store_true',
                        dest="show_reviews",
                        help='show open reviews',
                        default=False)
    return parser.parse_args()


def fetch_data(debug=False):
    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    user = config.get('default', 'user')
    password = config.get('default', 'password')
    auth = HTTPDigestAuth(user, password)
    resp = requests.get(URL, auth=auth)
    # slice out the "safety characters"
    content = resp.content[5:]
    if debug:
        print("Response from Gerrit:\n")
        print(content)
    return json.loads(content)


def merged(data):
    """Collect all the merged changes"""
    changes = {}

    for change in data:
        if change.get('status') == "MERGED":
            name = change['owner']['name']
            if name in changes:
                changes[name] += 1
            else:
                changes[name] = 1
    return changes


def proposed_changes(data):
    """Collect all the proposed changes"""
    changes = {}

    for change in data:
        if change.get('status') != "ABANDONED":
            name = change['owner']['name']
            if name in changes:
                changes[name] += 1
            else:
                changes[name] = 1
    return changes


def open_reviews_with_files(data):
    """Collect all the files that exist for open reviews"""
    changes = {}
    for change in data:
        if change.get('status') == "NEW":
            number = change['_number']
            files = []
            for k, v in change['revisions'].items():
                files = sorted(v['files'].keys())
            changes[number] = files
    return changes


def reviewers(data):
    """Collect all the reviewers on any relevant patches.

    NOTE: this only counts reviewers on the final version of the
    patch, it's a limitation, but because we're only getting names and
    not really doing stats, it's probably coming out in the wash."""
    changes = {}
    for change in data:
        if change['labels'].get('Code-Review'):
            if 'all' not in change['labels'].get('Code-Review', []):
                continue
            reviewers = change['labels']['Code-Review']['all']
            for rev in reviewers:
                # we only count people that scored a review, 0 doesn't
                # count.
                if rev["value"] != 0:
                    name = rev["name"]
                    if name in changes:
                        changes[name] += 1
                    else:
                        changes[name] = 1
    return changes


def main():
    args = parse_args()
    data = fetch_data(args.debug)

    if args.show_stats:
        print("\nHas proposed changes: %s" %
              len(proposed_changes(data).keys()))
        for name in sorted(proposed_changes(data).keys()):
            print(" - " + name)

        print("\nHas had changes merged: %s" % len(merged(data).keys()))
        for name in sorted(merged(data).keys()):
            print(" - " + name)

        print("\nHas reviewed changes: %s" % len(reviewers(data).keys()))
        for name in sorted(reviewers(data).keys()):
            print(" - " + name)

    if args.show_reviews:
        reviews_with_files = open_reviews_with_files(data)
        print("\nOpen reviews changing files: %s" % len(reviews_with_files))
        for name in sorted(reviews_with_files.keys()):
            print(" - https://review.openstack.org/%s - %s" % (
                name, ", ".join(reviews_with_files[name])))


if __name__ == "__main__":
    main()
