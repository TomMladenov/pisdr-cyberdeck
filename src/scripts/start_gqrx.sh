#!/bin/sh

ps -e | grep " gqrx"
if [ $? -ne 0 ]
then
		export DISPLAY=:0
		nohup gqrx -s windows -c /home/pi/git/pisdr-cyberdeck/src/config/$2_index$1.conf > /dev/null &
		echo "Waiting for GQRX start..."
		sleep 7
		$(xdotool windowsize $(xdotool search --name 'Gqrx' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gqrx' | head -4 | tail -1) -8 -22)
		#sleep 1
		#$(xdotool key --window $(xdotool search --name 'Gqrx'| head -4 | tail -1) ctrl+d)
		echo "GQRX started"
else
		$(xdotool windowraise $(xdotool search --name 'Gqrx' | head -4 | tail -1))
		$(xdotool windowsize $(xdotool search --name 'Gqrx' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gqrx' | head -4 | tail -1) -8 -22)
fi
exit 0
