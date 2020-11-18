#!/usr/bin/env python3

import sys
import os
from aprspy import APRS, PositionPacket, GenericPacket
import json
import zmq
import signal
import socket
from aprspy.packets.position import CompressionFix, CompressionSource, CompressionOrigin

class Forwarder(object):

	def __init__(self, ip, port):

		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PUB)
		self.host = 'tcp://' + ip + ':' + str(port)
		self.socket.bind(self.host)

	def publish(self, message):
		self.socket.send_string(message)

def handler_stop_signals(signum, frame):
	global run
	run = False



if __name__ == '__main__':

	run = True

	signal.signal(signal.SIGINT, handler_stop_signals)
	signal.signal(signal.SIGTERM, handler_stop_signals)

	fwdr = Forwarder('127.0.0.1', 11380)
	opened_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	try:
		while run:
			line = sys.stdin.readline().rstrip()
			if '{' in line: #if received line is in json format
				line_json = json.loads(line)
				print(line_json)


				base_packet = PositionPacket(	compressed = True, source=line_json["type"], destination='BASE', \
												compression_fix = CompressionFix.CURRENT, compression_source = CompressionSource.GLL, compression_origin = CompressionOrigin.COMPRESSED, \
												latitude=line_json["lat"], longitude=line_json["lon"], altitude=int(line_json["alt"]*3.28084), course=int(line_json["heading"]), \
												ambiguity=0, symbol_table='/', symbol_id='O', path='WIDE2-2')
				encoded_packet = base_packet.generate()
				xastir_packet = '{CALL},{PASSCODE}\n{MESSAGE}\n'.format(CALL='BASE', PASSCODE=25318, MESSAGE=encoded_packet)

				#Send to xastir
				opened_socket.sendto(xastir_packet.encode('utf-8'), ("127.0.0.1", 2023))

				#Send to ZMQ PROXY
				fwdr.publish(line)


	except KeyboardInterrupt:
		print("Press Ctrl-C to terminate while statement")
		pass

	'''
	[ 5049] (K1930308) Do 2014-07-17 12:32:15.999  lat: 45.66936  lon: 15.87939  alt: 28541.13   vH: 10.6  D: 270.8  vV: 8.7  # [00000]
	--json 2>/dev/null
	/home/pi/git/radiosonde_auto_rx/demod/mod/rs41mod
	'''
	'''
	{ "type": "RS41", "frame": 5056, "id": "K1930308", "datetime": "2014-07-17T12:32:22.999Z", "vel_h": 14.35572, "heading": 254.20834, "vel_v": 8.27610, "sats": 8, "bt": 65535, "batt": 2.70, "subtype": "RS41" }
	'''
