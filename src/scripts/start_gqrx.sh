#!/bin/sh

ps -e | grep " gqrx"
if [ $? -ne 0 ]
then
		nohup gqrx -s windows -c /home/pi/git/pisdr-cyberdeck/src/config/generic.conf > /dev/null &
		sleep 11
		$(xdotool windowsize $(xdotool search --name 'Gqrx' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gqrx' | head -4 | tail -1) -8 -22)
else
		$(xdotool windowraise $(xdotool search --name 'Gqrx' | head -4 | tail -1))
		$(xdotool windowsize $(xdotool search --name 'Gqrx' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gqrx' | head -4 | tail -1) -8 -22)
fi
exit 0
