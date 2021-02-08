#!/bin/sh

ps -e | grep " match"
if [ $? -ne 0 ]
then
		nohup matchbox-keyboard > /dev/null &
		sleep 0.5
		$(xdotool windowmove $(xdotool search --name Keyboard) 0 290)
else
		$(xdotool windowraise $(xdotool search --name 'Keyboard'))
fi
exit 0
