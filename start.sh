#!/bin/sh

# kill here
cd /home/orangepi/print_server
git pull
pip3 install -r requirements.txt
python3 -m print_server
