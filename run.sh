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

#exit $?

sed -i "s/Last updated:.*/Last updated: $(date -u)/" index.html
git add data.* *.json index.html
git commit -m "Updated csv"
scp -i ~/.ssh/id_rsa-backups data.* *.json index.html doughellmann.com:~/doughellmann.com/doc-migration/
