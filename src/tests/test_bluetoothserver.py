#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import sys
sys.path.append("..")
import time
import socket
from threading import Thread
import os
import subprocess


class BluetoothServer(Thread):

	def __init__(self, port):
		Thread.__init__(self)

		self.port = port

		#self.parent = parent
		self.running = False
		self.alive = True

		self.commandCount = 0

		self.bt_mac = "00:07:61:45:9A:43"
		self.socket = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
		#self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		#self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		backlog = 1
		self.size = 1024

		self.socket.bind((self.bt_mac, 1))
		self.socket.listen(backlog)



	def startServer(self):
		if not self.running:
			try:
				subprocess.run(["sudo rfkill unblock bluetooth"], shell=True)
				cmd = "hciconfig"
				device_id = "hci0"
				self.running = True
				#return CODES.SUCCESS
				print("Server successfully started")
				print("Listening for incoming connections...")

			except Exception as e:
				print("Could not start the server, error: {ERR}".format(ERR=e))
				exc_type, exc_obj, exc_tb = sys.exc_info()
				fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
				print(exc_type, fname, exc_tb.tb_lineno)
				#return CODES.ERROR

		else:
			print("Could not start the server, server is already running!")
			#return CODES.ERROR


	def stopServer(self):
		if self.running:
			try:
				self.alive = True
				self.running = False
				subprocess.run(["sudo rfkill block bluetooth"], shell=True)
				#return CODES.SUCCESS
				print("Server successfully stopped")

			except Exception as e:
				print("Could not stop the server, error: {ERR}".format(ERR=e))
				#return CODES.ERROR
		else:
			print("Could not stop the server, server is already stopped!")
			#return CODES.ERROR



	def terminate(self):
		self.running = False
		self.alive = False

		self.socket.shutdown(1)

		print("Server successfully terminated")


	def run(self):
		while self.alive:
			while self.running:
				try:

					client, address = self.socket.accept()
					print("Incoming connection from {CLI}".format(CLI=address))
					while True:
						data = client.recv(self.size).decode('utf-8')
						if data:
							print("Received data: " + data)

							self.commandCount += 1
							'''
							if self.debug:
								logging.debug('Received JSON-formatted command: {CMD}'.format(CMD=data))

							json_command = json.loads(data)
							success = self.parent.runCommand(json_command)
							response = {}
							response['success'] = success
							json_response = json.dumps(response)
							client.send(json_response.encode('utf-8'))
							'''

				except Exception as e:
					print("Client disconnected with error:{ERR}".format(ERR=e))
					client.close()
					time.sleep(1)
			time.sleep(1) #Idle at 1 Hz if not active




if __name__ == '__main__':

	server = BluetoothServer(port=1)
	server.start()
	server.startServer()
	time.sleep(1000)
	server.stopServer()
	server.terminate()
