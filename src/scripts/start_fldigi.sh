#!/bin/sh

ps -e | grep " fldigi"
if [ $? -ne 0 ]
then
		nohup fldigi -g 729x445+0+28 > /dev/null &
else
		$(xdotool windowactivate $(xdotool search --name 'fldigi'))
		$(xdotool windowsize $(xdotool search --name 'fldigi') 729 445)
		$(xdotool windowmove $(xdotool search --name 'fldigi') 0 28)
fi
exit 0
