#!/bin/bash

set -e

cd $(dirname $0)
./gen-burndown.py
git ci -m "Updated csv" > /dev/null
