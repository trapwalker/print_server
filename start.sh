#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin
p=/home/orangepi/print_server
log=$p/srv.log
cd $p
echo "START! $(date) ----------------" > $log
git pull >> $log 2>&1
pip3 install -r requirements.txt >> $log 2>&1
python3 -m print_server >> $log 2>&1
