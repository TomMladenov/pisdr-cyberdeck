"""
A simple Python script to send messages to a sever over Bluetooth using
Python sockets (with Python 3.3 or above).
"""

import socket

serverMACAddress = '00:07:61:45:9A:43'
port = 1


try:
	s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
	s.connect((serverMACAddress,port))
	while 1:
		text = input()
		if text == "quit":
			break
		s.send(bytes(text, 'UTF-8'))
	s.close()
except (Exception, KeyboardInterrupt) as e:
	print('Exception: {E}'.format(E=e))
	s.close()
