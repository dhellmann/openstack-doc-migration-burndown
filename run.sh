#!/bin/bash

set -e

cd $(dirname $0)
./gen-burndown.py
git add data.csv
git commit -m "Updated csv"
rsync -av --exclude config.ini data.csv index.html doughellmann.com:~/doughellmann.com/doc-migration/
