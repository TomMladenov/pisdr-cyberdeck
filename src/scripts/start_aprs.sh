#!/bin/sh

INDEX=$1

export DISPLAY=:0

ps -e | grep " rtl_fm"
if [ $? -ne 0 ]
then
  #clear PID file
  echo "" > /home/pi/tmp/aprs.pid
  rtl_fm -M fm -d $INDEX -f 144.800M -s 24000 - | direwolf -t 0 -r 24000 -D 1 -B 1200 - & > /dev/null && echo $! > /home/pi/tmp/aprs.pid
else
  echo "Already running"
fi
exit 0
