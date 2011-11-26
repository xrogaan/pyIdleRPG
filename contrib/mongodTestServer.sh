#!/usr/bin/env bash

[[ ! -x /tmp/xro ]]; mkdir /tmp/xro

mongod --dbpath /tmp/xro --port 27010 --bind_ip 127.0.0.1
