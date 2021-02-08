#!/bin/sh

ps -e | grep " gpredict"
if [ $? -ne 0 ]
then
		nohup gpredict > /dev/null &
		sleep 3
		$(xdotool windowsize $(xdotool search --name 'Gpredict' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gpredict' | head -4 | tail -1) -8 -40)
else
		$(xdotool windowraise $(xdotool search --name 'Gpredict' | head -4 | tail -1))
		$(xdotool windowsize $(xdotool search --name 'Gpredict' | head -4 | tail -1) 729 437)
		$(xdotool windowmove $(xdotool search --name 'Gpredict' | head -4 | tail -1) -8 -40)
fi
exit 0
