#!/bin/sh

ps -e | grep " xastir"
if [ $? -ne 0 ]
then
	#clear pid file
	echo "" > /home/pi/tmp/xastir.pid
	nohup xastir & > /dev/null && echo $! > /home/pi/tmp/xastir.pid
	sleep 3
	$(xdotool windowsize $(xdotool search --name xastir | head -2 | tail -1) 729 441)
	$(xdotool windowmove $(xdotool search --name xastir | head -2 | tail -1) 0 -21)
	$(xdotool windowsize $(xdotool search --name xastir | head -1) 729 450)
	$(xdotool windowmove $(xdotool search --name xastir | head -1) 0 -30)
else
	$(xdotool windowraise $(xdotool search --name xastir | head -2 | tail -1))
	$(xdotool windowraise $(xdotool search --name xastir | head -1))
	$(xdotool windowsize $(xdotool search --name xastir | head -2 | tail -1) 729 441)
	$(xdotool windowmove $(xdotool search --name xastir | head -2 | tail -1) 0 -21)
	$(xdotool windowsize $(xdotool search --name xastir | head -1) 729 450)
	$(xdotool windowmove $(xdotool search --name xastir | head -1) 0 -30)
fi
exit 0
