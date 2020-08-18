#!/bin/sh

export DISPLAY=:0
ps -e | grep " opencpn"
if [ $? -ne 0 ]
then
		nohup opencpn > /dev/null &
		sleep 4
    window=$(xdotool search --onlyvisible --name opencpn )
		$(xdotool windowsize $window 729 445)
		$(xdotool windowmove $window 0 -25)
		echo "opencpn started"
else
    window=$(xdotool search --onlyvisible --name opencpn )
		$(xdotool windowraise $window)
fi
exit 0
