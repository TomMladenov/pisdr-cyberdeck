#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'


import requests
import zmq
from threading import Thread
import json
import pickle

class RemoteCyberdeck(Thread):

	def __init__(self, ip, http_port, zmq_port):
		Thread.__init__(self)

		self.ip = ip
		self.http_port = http_port

		self.connected = False

		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.SUB)
		self.host = 'tcp://' + ip + ':' + str(zmq_port)
		self.socket.connect(self.host)
		self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
		self.socket.setsockopt(zmq.RCVTIMEO, 5000)

		self.active = True

	def _put_request(self, path, params=None):
		try:
			r = requests.put('http://{}:{}{}'.format(self.ip, self.http_port, path), params=params)
			if r.status_code == 200:
				return r.json() #Server responded with a success status
			else:
				return {"success": False, "response": r.status_code} #Something went wrong on the server side
		except Exception as e:
			return {"success": False, "response": str(e)} #Something went wrong on the client side


	def _get_request(self, path, params=None):
		try:
			r = requests.get('http://{}:{}{}'.format(self.ip, self.http_port, path), params=params)
			if r.status_code == 200:
				return r.json()
			else:
				return {"success": False, "response": r.status_code}
		except Exception as e:
			return {"success": False, "response": str(e)}


	def _post_request(self, path, params=None):
		try:
			r = requests.post('http://{}:{}{}'.format(self.ip, self.http_port, path), params=params)
			if r.status_code == 200:
				return r.json()
			else:
				return {"success": False, "response": r.status_code}
		except Exception as e:
			return {"success": False, "response": str(e)}


	def handshake(self):
		return self._put_request(path="/ping")

	def get_systems(self):
		return self._get_request(path="/systems")

	def get_config(self, system=None):
		if system:
			return self._get_request(path="/systems/{}/config".format(system))
		else:
			return self._get_request(path="/config")

	def save_config(self):
		return self._post_request(path="/config")


	def get_status(self, system=None):
		if system:
			return self._get_request(path="/systems/{}/status".format(system))
		else:
			return self._get_request(path="/status")

	def get_configstatus(self, system=None):
		if system:
			return self._get_request(path="/systems/{}/configstatus".format(system))
		else:
			return self._get_request(path="/configstatus")

	def set_config(self, system, key, value):
		return self._put_request(path="/systems/{}/config".format(system),  params={"key": key, "value": value})

	def set_power(self, system, power):
		return self._put_request(path="/systems/{}/power".format(system), params={"power": power})

	def toggle_power(self, system):
		return self._put_request(path="/systems/{}/power/toggle".format(system))

	def start_process(self, system):
		return self._put_request(path="/systems/{}/start_process".format(system))

	def stop_process(self, system):
		return self._put_request(path="/systems/{}/stop_process".format(system))

	def reboot(self):
		return self._put_request(path="/systems/obc/reboot")

	def shutdown(self):
		return self._put_request(path="/systems/obc/shutdown")



	def set_volume(self, volume):
		return self._put_request(path="/systems/audio/volume", params={"volume": volume})

	def increment_volume(self):
		return self._put_request(path="/systems/audio/volume/increment")

	def decrement_volume(self):
		return self._put_request(path="/systems/audio/volume/decrement")

	def set_mute(self, mute):
		return self._put_request(path="/systems/audio/mute", params={"mute": mute})

	def toggle_mute(self):
		return self._put_request(path="/systems/audio/mute/toggle")

	def set_test(self, test):
		return self._put_request(path="/systems/audio/test", params={"test": test})


	def set_brightness(self, brightness):
		return self._put_request(path="/systems/display/brightness", params={"brightness": brightness})

	def increment_brightness(self):
		return self._put_request(path="/systems/display/brightness/increment")

	def decrement_brightness(self):
		return self._put_request(path="/systems/display/brightness/decrement")

	def screenshot(self):
		return self._put_request(path="/systems/display/screenshot")


	def get_frequency(self):
		return self._get_request(path="/systems/rigctl/frequency")

	def set_frequency(self, frequency):
		return self._put_request(path="/systems/rigctl/frequency", params={"frequency": frequency})

	def stop(self):
		self.active = False

	def run(self):
		while self.active:
			try:
				self.status = pickle.loads(self.socket.recv())["configstatus"]
				self.connected = True

			except Exception as e:
				print(str(e))
				self.connected = False


"""
if __name__ == '__main__':

	cyberdeck = RemoteCyberdeck("192.168.0.163", 5000, 5001)
	print("Issuing remote handshake...")
	response = cyberdeck.handshake()
	print(reponse)

	if resonse["success"]:
		gps_status = cyberdeck.get_config(system="gps")
		print(gps_pstatus)

	cyberdeck.stop()
	sys.exit("Done!")

"""
