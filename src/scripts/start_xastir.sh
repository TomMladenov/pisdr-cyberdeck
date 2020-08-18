#!/bin/sh

export DISPLAY=:0
ps -e | grep " xastir"
if [ $? -ne 0 ]
then
		nohup xastir > /dev/null &
		sleep 3
		$(xdotool windowsize $(xdotool search --name xastir | head -2 | tail -1) 729 441)
		$(xdotool windowmove $(xdotool search --name xastir | head -2 | tail -1) 0 -21)
		$(xdotool windowsize $(xdotool search --name xastir | head -1) 729 450)
		$(xdotool windowmove $(xdotool search --name xastir | head -1) 0 -30)
		echo "xastir started"
else
		$(xdotool windowraise $(xdotool search --name xastir | head -2 | tail -1))
		$(xdotool windowraise $(xdotool search --name xastir | head -1))
fi
exit 0
