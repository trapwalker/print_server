#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin

cd /home/orangepi/print_server

git pull > /home/orangepi/print_server/srv.log 2>&1
pip3 install -r requirements.txt >> /home/orangepi/print_server/srv.log 2>&1
python3 -m print_server >> /home/orangepi/print_server/srv.log 2>&1
