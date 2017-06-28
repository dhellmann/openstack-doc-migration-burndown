#!/bin/bash -x

set -e

date

cd $(dirname $0)
./gen-burndown.py
git add data.* notstarted.json
git commit -m "Updated csv"
#rsync -av --exclude config.ini data.* index.html doughellmann.com:~/doughellmann.com/doc-migration/
scp -i ~/.ssh/id_rsa-backups data.* notstarted.json index.html doughellmann.com:~/doughellmann.com/doc-migration/
