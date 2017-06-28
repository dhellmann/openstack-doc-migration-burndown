#!/bin/bash

BASE=/opt/devel/repos

for repo in $(cat repos.txt)
do
    doc_path=$BASE/$repo/doc/source
    if [[ -d $doc_path ]]
    then
        echo $repo >> expected_repos.txt
    fi
done
