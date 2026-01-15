#!/bin/bash
set -e

cd /app

pytest  > /app/logs/tests_output.log
python3 /app/src/main.py > /app/logs/main_output.log
python3 /app/src/map.py > /app/logs/map_output.log
