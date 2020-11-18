#!/bin/sh

LP=$1
INV=$2

export DISPLAY=:0
ps -e | grep " xastir"
if [ $? -eq 0 ]
then
  ps -e | grep "dfm09mod"
  if [ $? -ne 0 ]
  then
    rec -t wav --comment DFM -r 48000 - 2>/dev/null | \
    sox - -t wav - lowpass $LP | \
    /home/pi/git/radiosonde_auto_rx/demod/mod/dfm09mod --ecc $INV --json 2>/dev/null | \
    /home/pi/git/pisdr-cyberdeck/src/scripts/sonde_to_xastir.py & > /dev/null && echo $! > /home/pi/tmp/dfm.pid
    exit 0
  else
    exit 0
  fi
else
		exit 0
fi
