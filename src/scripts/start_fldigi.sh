#!/bin/sh

ps -e | grep " fldigi"
if [ $? -ne 0 ]
then
		export DISPLAY=:0
		nohup fldigi > /dev/null &
		#echo "Waiting for FLdigi start..."
		#sleep 10
		#$(xdotool windowsize $(xdotool search --name 'fldigi') 729 450)
		#$(xdotool windowmove $(xdotool search --name 'fldigi') 0 -5)
		#echo "Fldigi started"
else
		$(xdotool windowactivate $(xdotool search --name 'fldigi'))
		#$(xdotool windowmove $(xdotool search --name 'fldigi') 0 -5)
fi
exit 0
