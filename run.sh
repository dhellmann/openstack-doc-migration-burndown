#!/bin/bash -x

set -e

date

cd $(dirname $0)
if [[ ! -d .venv ]]
then
    virtualenv --python=python3.5 .venv
    .venv/bin/pip install -r requirements.txt
fi
source .venv/bin/activate

./gen-burndown.py
sed -i "s/Last updated:.*/Last updated: $(date -u)/" index.html
git add data.* missing_urls.json notstarted.json index.html
git commit -m "Updated csv"
scp -i ~/.ssh/id_rsa-backups data.* notstarted.json index.html doughellmann.com:~/doughellmann.com/doc-migration/
