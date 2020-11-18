#!/bin/sh

pkill -F /home/pi/tmp/rs41.pid
pkill -F /home/pi/tmp/dfm.pid
pkill -f "comment RS41"
pkill -f "comment DFM"
