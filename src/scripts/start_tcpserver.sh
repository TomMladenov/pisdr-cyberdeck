#!/bin/sh

RF_INDEX=$1
PPM=$2
IP=$3
PORT=$4

nohup $(rtl_tcp -d $RF_INDEX -P $PPM -a $IP -s 960000 -p $4) > /dev/null &
