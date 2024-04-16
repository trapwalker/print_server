#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

cd /home/orangepi/print_server
# kill here
git pull
pip3 install -r requirements.txt
python3 -m print_server
