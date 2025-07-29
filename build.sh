#!/usr/bin/env bash

set -o errexit

apt-get update && apt-get install -y libjpeg-dev zlib1g-dev
pip install -r requirements.txt
python manage.py collectstatic
python manage.py migrate


chmod +x build.sh