#!/bin/sh

ps -e | grep "dump1090"
if [ $? -ne 0 ]
then
    ps -e | grep " xastir"
    if [ $? -eq 0 ]
    then
  		nohup $(/home/pi/git/dump1090/dump1090 --ppm -1.4 --gain 49  --net --net-sbs-port 30003 --phase-enhance --oversample --fix --device $1 --ppm $2) > /dev/null &
      sleep 1
      nohup $(/usr/share/xastir/scripts/ads-b.pl BASE 25318) > /dev/null &
  		exit 0
    else
      exit -2
    fi
else
		exit -1
fi
