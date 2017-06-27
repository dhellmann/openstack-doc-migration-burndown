#!/bin/bash

set -e

cd $(dirname $0)
./gen-burndown.py
git add data.csv
git commit -m "Updated csv"
