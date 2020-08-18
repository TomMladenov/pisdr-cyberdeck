#!/bin/sh

RF_SER=$1
PPM=$2

ps -e | grep "acarsdec"
if [ $? -ne 0 ]
then
    nohup $(acarsdec -p $PPM -r $RF_SER  131.450 131.475 131.525 131.725 131.825 -D -l /home/pi/log/acars/ACARS_LOG.log) > /dev/null &
    exit 0
else
	 exit -1
fi
