#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'


import sys
import os
import json
import zmq
import signal
import socket
import argparse
import pickle
import datetime


class Packet(object):

	def __init__(self, tag, payload):

		self.tag = tag
		self.utc = datetime.datetime.utcnow()
		self.payload = payload


class Forwarder(object):

	def __init__(self, ip, port):

		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PUB)
		self.host = 'tcp://' + ip + ':' + str(port)
		self.socket.connect(self.host)

	def publish(self, packet):
		to_send = pickle.dumps(packet)
		self.socket.send(to_send)

def handler_stop_signals(signum, frame):
	sys.exit()


if __name__ == '__main__':

	run = True

	parser = argparse.ArgumentParser(
		description='')

	parser.add_argument(
		'-t', '--tag', type=str, help='unique tag to append to data', required=True)

	args = parser.parse_args()

	tag = args.tag

	try:

		signal.signal(signal.SIGINT, handler_stop_signals)
		signal.signal(signal.SIGTERM, handler_stop_signals)

		fwdr = Forwarder('127.0.0.1', 5005)

		while run:
			line = sys.stdin.readline().rstrip()
			if not line == "":
				#print(line)
				p = Packet(tag, line)
				fwdr.publish(p)

				#print("Sending data {}".format(line))

	except Exception as e:
		#print("Press Ctrl-C to terminate while statement")
		os.system("echo '{}' > /home/pi/forwarder_exception".format(str(e)))
		pass
