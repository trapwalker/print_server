#!/usr/bin/env bash

KEY_NAME_SERVER=id_rsa
KEY_NAME_CLIENT=id_rsa2
CLIENT_ROOT=~/test1

cd $CLIENT_ROOT
mkdir .ssh
wget http://admin.vestnik.press:8010/static/_keys/$KEY_NAME_SERVER.enc -O .ssh/$KEY_NAME_CLIENT.enc
echo "Введите пароль:"
read -s PASSWORD
openssl aes-256-cbc -d -iter 100 -salt -in .ssh/$KEY_NAME_CLIENT.enc -out .ssh/$KEY_NAME_CLIENT -k $PASSWORD
ssh-keygen -y -f $KEY_NAME_CLIENT > $KEY_NAME_CLIENT.pub

sudo apt update -y
sudo apt upgrade -y
sudo apt install cups python3-pip git openssl -y
git clone git@github.com:trapwalker/print_server.git
cd print_server
git checkout release
pip3 install -r requirements.txt
python3 -m
