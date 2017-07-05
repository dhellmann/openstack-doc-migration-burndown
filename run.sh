#!/bin/bash -x

set -e

date

cd $(dirname $0)
./gen-burndown.py
sed -i "s/Last updated:.*/Last updated: $(date)/" index.html
git add data.* notstarted.json index.html
git commit -m "Updated csv"
scp -i ~/.ssh/id_rsa-backups data.* notstarted.json index.html doughellmann.com:~/doughellmann.com/doc-migration/
