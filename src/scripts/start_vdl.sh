#!/bin/sh

RF_SER=$1
PPM=$2

ps -e | grep "dumpvdl2"
if [ $? -ne 0 ]
then
    nohup $(dumpvdl2 --rtlsdr $RF_SER --correction $PPM 136725000 136775000 136825000 136875000 136975000 --utc --daily --output-file /home/pi/log/vdl/VDL_LOG.log) > /dev/null &
    exit 0
else
	 exit -1
fi
