#!/bin/sh

ps -e | grep "kronometer"
if [ $? -ne 0 ]
then
		nohup kronometer > /dev/null &
else
		exit 0
fi
exit 0
