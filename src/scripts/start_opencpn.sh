#!/bin/sh

ps -e | grep " opencpn"
if [ $? -ne 0 ]
then
		nohup opencpn > /dev/null &
		sleep 10
    window=$(xdotool search --onlyvisible --name opencpn )
		$(xdotool windowsize $window 729 445)
		$(xdotool windowmove $window 0 -25)
else
    window=$(xdotool search --onlyvisible --name opencpn )
		$(xdotool windowraise $window)
fi
exit 0
