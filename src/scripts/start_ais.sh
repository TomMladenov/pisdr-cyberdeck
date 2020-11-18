#!/bin/sh

RF_INDEX=$1
PPM=$2

ps -e | grep "rtl_ais"
if [ $? -ne 0 ]
then
    nohup $(rtl_ais -d $RF_INDEX -p $PPM) > /dev/null &
    exit 0
else
    exit 0
fi
