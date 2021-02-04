#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import json
import time
import alsaaudio
import subprocess
import os
import telnetlib
import socket
import gpsd
import mgrs
import zmq
from threading import Thread
import logging
import re
from enum import Enum
import pickle
import datetime
from configparser import ConfigParser
import multiprocessing
import pyais
from influxdb import InfluxDBClient

from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219, Mode, Gain
import board
import RPi.GPIO as GPIO
from rpi_backlight import Backlight
import netifaces
import Adafruit_ADS1x15
from rtlsdr import RtlSdr
from aprspy import APRS, PositionPacket, GenericPacket
from aprspy.packets.position import CompressionFix, CompressionSource, CompressionOrigin
from packet import Packet


class Process():

	#This class should be used for any programs that require a data source from a device as an input (either RF or audio, or another device)

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		self.commands = []

		self._init_status()

	def _init_status(self):

		self.status = 	{
							"running" : 0
						}

	def _run_executable(self):
		#Populate this in the subclassing
		pass

	def start_process(self):
		device = self.config["s_device"]
		if 	device == self.parent.rf.config["s_rf1_serial"] or \
			device == self.parent.rf.config["s_rf2_serial"]:
			if self.parent.rf.status["{}_power".format(device)]:
				try:
					index = self.parent.rf.status["{}_index".format(device)]
					sdr = RtlSdr(index)
					sdr.close()

					if not self.status["running"]:
						return self._run_executable()
					else:
						return {"success": False, "message": "process already running!"}


				except Exception as e:
					#Will trow Exception if the RTL SDR cannot be accessed (used by other softw)
					return {"success": False, "message": str(e)}
			else:
				return {"success": False, "message": "Specified input device is not connected"}
		elif device == self.parent.obc.config["s_soundcard"]:

			if not self.status["running"]:
				return self._run_executable()
			else:
				return {"success": False, "message": "process already running!"}

		else:
			return {"success": False, "message": "Specified input device {} is not supported".format(device)}


	def stop_process(self):

		#kill all subcommands (SIGTERM)
		for command in self.commands:
			subprocess.run(['pkill -f \'{}\''.format(command)], shell=True)

		#If for some reason a sigterm did not work, perform an additional SIGKILL (last resort)
		for command in self.commands:
			subprocess.run(['pkill -s 9 -f \'{}\''.format(command)], shell=True)

		self.status["running"] = 0

		return {"success": True, "status": self.status}


	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def set_config(self, key, value):
		if key == "s_id":
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}

class Application():

	#This class should be used for any standalone applications that do not direclty require a data input device

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		self._init_status()

	def _init_status(self):

		self.status = 	{
							"running" : 0
						}

		subprocess.run(["../scripts/stop_{}.sh &".format(self.config["s_id"])], shell=True)

	#This class starts apps via scripts so that additional more complex gui configuration can happen downstream
	def start_process(self):
		subprocess.run(["../scripts/start_{}.sh &".format(self.config["s_id"])], shell=True)
		self.status["running"] = 1
		return {"success": True, "status": self.status}

	def stop_process(self):
		subprocess.run(["../scripts/stop_{}.sh &".format(self.config["s_id"])], shell=True)
		self.status["running"] = 0
		return {"success": True, "status": self.status}

	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def get_configstatus(self):
		configstatus = {"config": self.config, "status": self.status}
		return {"success": True, "config": configstatus}


	def set_config(self, key, value):
		if key in ["s_id", "s_name", "s_type"]:
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}


class Proxy(Application, Thread):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self._init_status()

	def _init_status(self):

		self.status = 	{
							"running" : 1
						}

	def run(self):
		self.proxy()

	def proxy(self):
		try:
			self.context = zmq.Context()

			# Creating subX interface
			self.subX = self.context.socket(zmq.SUB)
			self.subX.bind("tcp://127.0.0.1:{}".format(self.config["i_subx_port"]))

			self.subX.setsockopt_string(zmq.SUBSCRIBE, "")

			# Creating the pubX interface
			self.pubX = self.context.socket(zmq.PUB)
			self.pubX.bind("tcp://0.0.0.0:{}".format(self.config["i_pubx_port"]))
			zmq.device(zmq.FORWARDER, self.subX, self.pubX)
		except Exception as e:
			print("Proxy exited with exception: {}".format(e))


	#This class starts apps via scripts so that additional more complex gui configuration can happen downstream
	def start_process(self):
		return {"success": False, "message": "function not supported for this subsystem"}

	def stop_process(self):
		return {"success": False, "message": "function not supported for this subsystem"}

	def _shutdown_thread(self):
		self.subX.close()
		self.pubX.close()
		self.context.destroy()
		self.stop_process()


class Subscriber(Application, Thread):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config
		self.alive = True

		self.xastir_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.SUB)
		host = 'tcp://127.0.0.1:{}'.format(self.parent.proxy.config["i_pubx_port"])
		self.socket.connect(host)
		self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
		self.socket.setsockopt(zmq.RCVTIMEO, 5000)

		self._init_status()


	def _init_status(self):

		self.status = 	{
							"running" : 0
						}

		if self.config["b_autostart"]:
			self.start_process()

	def send_to_xastir(self, source, latitude, longitude, altitude, course, symbol_table, symbol_id, path):

		aprs_packet = PositionPacket(	compressed = True, source=source, destination=self.parent.navigation.config["s_xastir_call"], \
										compression_fix = CompressionFix.CURRENT, compression_source = CompressionSource.GLL, compression_origin = CompressionOrigin.COMPRESSED, \
										latitude=latitude, longitude=longitude, altitude=int(altitude*3.28084), course=int(course), \
										ambiguity=0, symbol_table=symbol_table, symbol_id=symbol_id, path=path)

		self.send_UDP_xastir(aprs_packet.generate())


	def send_UDP_xastir(self, aprs_string):
		xastir_string = '{CALL},{PASSCODE}\n{MESSAGE}\n'.format(CALL=self.parent.navigation.config["s_xastir_call"], PASSCODE=self.parent.navigation.config["i_xastir_passcode"], MESSAGE=aprs_string)
		self.xastir_socket.sendto(xastir_string.encode('utf-8'), (self.parent.navigation.config["s_xastir_ip"], self.parent.navigation.config["i_xastir_port"]))

	def updatePacketCount(self, tag):
		id = "{s_id}_packets".format(s_id=tag)
		if id not in self.status:
			  self.status[id] = 0
		self.status[id] += 1

	def run(self):
		while self.alive:
			while self.status["running"]:
				try:
					packet = pickle.loads(self.socket.recv())

					print("[{}] Received packet with tag [{}] and payload [{}]".format(packet.utc, packet.tag, packet.payload))

					if packet.tag == "aprs":
						self.send_UDP_xastir(aprs_string=packet.payload[6:])
						self.updatePacketCount(packet.tag)

					elif packet.tag == "rs1" or packet.tag == "rs2":

						if '{' in packet.payload and '}' in packet.payload: #if received line is in json format
							line_json = json.loads(packet.payload)

							self.send_to_xastir(source=line_json["type"], \
												latitude=line_json["lat"], \
												longitude=line_json["lon"], \
												altitude=line_json["alt"], \
												course=line_json["heading"], \
												symbol_table='/', \
												symbol_id='O', \
												path='WIDE2-2')

							self.updatePacketCount(packet.tag)


					elif packet.tag == "ais":

						#message = "!AIVDM,1,1,,A,15RTgt0PAso;90TKcjM8h6g208CQ,0*4A"
						message = packet.payload
						aisMessage = json.loads(pyais.AISMessage(pyais.NMEAMessage.from_string(message)).to_json())

						self.send_to_xastir(source=aisMessage["decoded"]["mmsi"], \
											latitude=aisMessage["decoded"]["lat"], \
											longitude=aisMessage["decoded"]["lon"], \
											altitude=1, \
											course=aisMessage["decoded"]["heading"], \
											symbol_table='/', \
											symbol_id='Y', \
											path='WIDE2-2')

						self.updatePacketCount(packet.tag)

						"""
						{
							"nmea": {
								"ais_id": 1,
								"raw": "!AIVDM,1,1,,A,15RTgt0PAso;90TKcjM8h6g208CQ,0*4A",
								"talker": "AI",
								"msg_type": "VDM",
								"count": 1,
								"index": 1,
								"seq_id": "",
								"channel": "A",
								"data": "15RTgt0PAso;90TKcjM8h6g208CQ",
								"checksum": 74,
								"bit_array": "000001000101100010100100101111111100000000100000010001111011110111001011001001000000100100011011101011110010011101001000110000000110101111000010000000001000010011100001"
							},
							"decoded": {
								"type": 1,
								"repeat": 0,
								"mmsi": "371798000",
								"status": 0,
								"turn": -127,
								"speed": 12.3,
								"accuracy": true,
								"lon": -123.39538333333333,
								"lat": 48.38163333333333,
								"course": 224.0,
								"heading": 215,
								"second": 33,
								"maneuver": 0,
								"raim": false,
								"radio": 34017
							}
						}
						"""
					self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
				except Exception as e:
					pass

			time.sleep(1)

	def start_process(self):
		if not self.status["running"]:
			self.status["running"] = 1
			return {"success": True, "status": self.status}
		else:
			return {"success": False, "message": "Process is already running"}

	def stop_process(self):
		if self.status["running"]:
			self.status["running"] = 0
			return {"success": True, "status": self.status}
		else:
			return {"success": False, "message": "Process is already stopped"}

	def _shutdown_thread(self):
		self.stop_process()
		self.alive = False

class APRS(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"i_freq" : self.config["i_freq"],
							"i_baud" : self.config["i_baud"],
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_fm"], shell=True)
		subprocess.run(["killall direwolf"], shell=True)


	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		freq = self.config["i_freq"]
		gain = self.config["i_gain"]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		samprate = self.config["i_samprate"]
		baud = self.config["i_baud"]

		command1 = "rtl_fm -M fm -d {} -f {} -g {} -p {} -s {} -".format(index, freq, gain, ppm, samprate)
		command2 = "direwolf -q dh -t 0 -r {} -D 1 -B {} -".format(samprate, baud)
		command3 = "python3 forwarder.py -t {}".format(self.config["s_id"])

		self.commands.append(command1)
		self.commands.append(command2)
		self.commands.append(command3)
		self.process = subprocess.Popen("{} | {} | {} > /home/pi/aprsdebug 2>&1 &".format(command1, command2, command3), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		self.status["running"] = 1

		return {"success": True, "status": self.status}



class AIS(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"i_freq_l" : self.config["i_freq_l"],
							"i_freq_r" : self.config["i_freq_r"],
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_ais"], shell=True)


	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		gain = self.config["i_gain"]
		freq_left = self.config["i_freq_l"]
		freq_right = self.config["i_freq_r"]

		#command1 = "rtl_ais -d {} -p {} -g {} -l {} -r {} -n".format(index, ppm, gain, freq_left, freq_right)
		command1 = "for i in 1 2 3 4 5; do cat /home/pi/ais; done"
		command2 = "python3 forwarder.py -t {}".format(self.config["s_id"])

		self.commands.append(command1)
		self.commands.append(command2)
		self.process = subprocess.Popen("{} | {} &".format(command1, command2), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class RTLTCP(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"s_host" : self.config["s_host"],
							"i_port" : self.config["i_port"],
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_tcp"], shell=True)

	def _run_executable(self):
		host = self.config["s_host"]
		port = self.config["i_port"]
		freq = self.config["i_freq"]
		gain = self.config["i_gain"]
		rate = self.config["i_samprate"]
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]

		command1 = "rtl_tcp -a {} -p {} -f {} -g {} -s {} -d {} -P {}".format(host, port, freq, gain, rate, index, ppm)

		self.commands.append(command1)
		self.process = subprocess.Popen("{} &".format(command1), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class RS(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"s_sonde" : self.config["s_sonde"],
							"i_freq" : self.config["i_freq"],
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_fm"], shell=True)
		subprocess.run(["killall rs41mod"], shell=True)
		subprocess.run(["killall dfm09mod"], shell=True)

	def _run_executable(self):
		if 	self.config["s_device"] == self.parent.rf.config["s_rf1_serial"] or self.config["s_device"] == self.parent.rf.config["s_rf2_serial"]:
			freq = self.config["i_freq"]
			gain = self.config["i_gain"]
			index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
			ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
			command1 = "rtl_fm -M fm -d {} -f {} -g {} -p {} -F9 -s 15k".format(index, freq, gain, ppm)
			command2 = "sox -t raw -r 15k -e s -b 16 -c 1 - -r 48000 -b 8 -t wav - lowpass {}".format(self.config["i_lowpass"])

		elif self.config["s_device"] == self.parent.obc.config["s_soundcard"]:
			command1 = "rec -q -t wav --comment {} -r 48000 -".format(self.config["s_id"])
			command2 = "sox - -t wav - lowpass {}".format(self.config["i_lowpass"])

		if self.config["s_sonde"] == "rs41":
			if self.config["b_inverted"]:
				command3 = "rs41mod --ecc --crc -i --json"
			else:
				command3 = "rs41mod --ecc --crc --json"

		elif self.config["s_sonde"] == "dfm":
			command3 = "dfm09mod --ecc --json --dist --auto"

		#command4 = "/home/pi/git/pisdr-cyberdeck/src/scripts/sonde_to_xastir.py --sourceid {}".format(self.config["s_id"])
		command4 = "python3 forwarder.py -t {}".format(self.config["s_id"])


		self.commands.append(command1)
		#self.commands.append(command2)
		#self.commands.append(command3)
		self.commands.append(command4)
		self.process = subprocess.Popen("{} | {} | {} | {} &".format(command1, command2, command3, command4), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class ACARS(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall acarsdec"], shell=True)

	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		gain = self.config["i_gain"]
		freqs = json.loads(self.config["l_freqs"])
		freqs_unpacked = ""
		for f in freqs:
			freqs_unpacked += str(f) + " "

		command1 = "acarsdec -d {} -p {} -g {} {}".format(index, ppm, gain, freqs_unpacked)

		self.commands.append(command1)
		self.process = subprocess.Popen("{} &".format(command1), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class VDL(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall dumpvdl2"], shell=True)

	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		gain = self.config["i_gain"]
		id = self.config["s_id"]
		freqs = json.loads(self.config["l_freqs"])
		freqs_unpacked = ""
		for f in freqs:
			freqs_unpacked += str(f) + " "

		command1 = "dumpvdl2 --rtlsdr {} --correction {} --gain {} --station-id {} --output decoded:json:file:path=- {}".format(index, ppm, gain, id, freqs_unpacked)
		command2 = "/home/pi/git/pisdr-cyberdeck/src/scripts/sonde_to_xastir.py"

		self.commands.append(command1)
		self.commands.append(command2)
		self.process = subprocess.Popen("{} | {} &".format(command1, command2), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class ISM(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"i_freq" : self.config["i_freq"],
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_433"], shell=True)

	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		gain = self.config["i_gain"]
		id = self.config["s_id"]
		freq = self.config["i_freq"]
		samprate = self.config["i_samprate"]

		command1 = "rtl_433 -d {} -p {} -g {} -f {} -s {} -F json -C si".format(index, ppm, gain, freq, samprate)
		#command2 = "/home/pi/git/pisdr-cyberdeck/src/scripts/sonde_to_xastir.py"
		#rtl_433 -d 0 -p 0 -f 433920000 -s 1400000 -F json

		self.commands.append(command1)
		#self.commands.append(command2)
		self.process = subprocess.Popen("{} &".format(command1), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class ADSB(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"s_device" : self.config["s_device"]
						}

		subprocess.run(["killall rtl_433"], shell=True)

	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]
		ppm = self.parent.rf.config["i_{}_ppm".format(self.config["s_device"])]
		gain = self.config["i_gain"]
		id = self.config["s_id"]
		freq = self.config["i_freq"]
		samprate = self.config["i_samprate"]

		command1 = "rtl_433 -d {} -p {} -g {} -f {} -s {} -F json".format(index, ppm, gain, freq, samprate)
		#command2 = "/home/pi/git/pisdr-cyberdeck/src/scripts/sonde_to_xastir.py"

		self.commands.append(command1)
		#self.commands.append(command2)
		self.process = subprocess.Popen("{} &".format(command1, command2), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.status["running"] = 1

		return {"success": True, "status": self.status}


class GQRX(Process):

	def _init_status(self):

		self.status = 	{
							"running" : 0,
							"i_samprate" : self.config["i_samprate"],
							"b_directsamp" : self.config["b_directsamp"],
							"b_bias" : self.config["b_bias"],
							"s_device" : self.config["s_device"]
						}

		self.stop_process()

	def _run_executable(self):
		index = self.parent.rf.status["{}_index".format(self.config["s_device"])]

		config = ConfigParser()
		config.read(self.config["s_generic_config"])
		config["General"]["crashed"] = "false"
		config["input"]["decimation"] = str(self.config["i_decimation"])
		config["input"]["frequency"] = str(self.config["i_freq"])
		config["input"]["sample_rate"] = str(self.config["i_samprate"])

		if self.config["b_directsamp"]:
			config["input"]["device"] = '\"rtl={},direct_samp=3\"'.format(index)
		else:
			config["input"]["device"] = '\"rtl={}\"'.format(index)


		with open(self.config["s_generic_config"], 'w') as configfile:
			config.write(configfile)

		subprocess.run(["/home/pi/git/pisdr-cyberdeck/src/scripts/start_{}.sh &".format(self.config["s_id"])], shell=True)
		self.status["running"] = 1

		return {"success": True, "status": self.status}

	def start_process(self):
		if not self.status["running"]:
			device = self.config["s_device"]
			if 	device == self.parent.rf.config["s_rf1_serial"] or \
				device == self.parent.rf.config["s_rf2_serial"]:
				if self.parent.rf.status["{}_power".format(device)]:
					try:
						index = self.parent.rf.status["{}_index".format(device)]
						sdr = RtlSdr(index)
						sdr.close()

						if not self.status["running"]:
							return self._run_executable()
						else:
							return {"success": False, "message": "process already running!"}


					except Exception as e:
						#Will trow Exception if the RTL SDR cannot be accessed (used by other softw)
						return {"success": False, "message": str(e)}
				else:
					return {"success": False, "message": "Specified input device is not connected"}
			elif device == self.parent.obc.config["s_soundcard"]:

				if not self.status["running"]:
					return self._run_executable()
				else:
					return {"success": False, "message": "process already running!"}

			else:
				return {"success": False, "message": "Specified input device {} is not supported".format(device)}
		else:
			subprocess.run(["/home/pi/git/pisdr-cyberdeck/src/scripts/start_{}.sh &".format(self.config["s_id"])], shell=True)
			return {"success": True, "status": self.status}


	def stop_process(self):
		subprocess.run(["/home/pi/git/pisdr-cyberdeck/src/scripts/stop_{}.sh &".format(self.config["s_id"])], shell=True)
		self.status["running"] = 0

		return {"success": True, "status": self.status}





class GenericSystem(Thread):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = {}
		self.running = True

	def _getTemperatureDS18B20(self, ID):
		try:
			output = subprocess.check_output(['cat', '/sys/bus/w1/devices/{TEMP_ID}/temperature'.format(TEMP_ID=ID)])
			return int(output.decode('utf-8'))/1000.0, True
		except Exception as e:
			return 0.0, False

	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def _shutdown_thread(self):
		self.running = False

	def run(self):
		while self.running:
			time.sleep(1)

	def set_config(self, key, value):
		if key in ["s_id", "s_name", "s_type", "i_sense_pin", "i_control_pin", "s_rf1_serial", "s_rf2_serial"]:
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}



class RigCtl(Application):
	"""Basic rigctl client implementation. https://github.com/marmelo/gqrx-remote/blob/master/gqrx-remote.py """

	def start_process(self):
		self.status["running"] = 1
		return {"success": True, "status": self.status}

	def stop_process(self):
		self.status["running"] = 0
		return {"success": True, "status": self.status}

	def _request(self, request):
		try:
			con = telnetlib.Telnet(self.config["s_hostname"], self.config["i_port"])
			con.write(('%s\n' % request).encode('ascii'))
			response = con.read_some().decode('ascii').strip()
			con.write('c\n'.encode('ascii'))
			return {"success": True, "response" : response}
			#return {"success": True}
		except Exception as e:
			return {"success": False, "message": str(e)}

	def set_frequency(self, frequency):
		return self._request('F %s' % frequency)

	def get_frequency(self):
		return self._request('f')

	def set_mode(self, mode):
		return self._request('M %s' % mode)

	def get_mode(self):
		return self._request('m')

	def get_level(self):
		return self._request('l')


class Publisher(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = {}

		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PUB)
		self.host = 'tcp://{}:{}'.format(self.config["s_host"], self.config["i_port"])
		self.socket.bind(self.host)

		self.running = True

	def run(self):
		while self.running:
			status = self.parent.get_configstatus()
			to_send = pickle.dumps(status)

			self.socket.send(to_send)
			time.sleep(self.config["i_period"])


class Battery(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = 	{
							"charge_state" : "",
							"level": 0,
							"temp1": 0,
							"temp2" : 0,
							"t_left" : 0
						}


		self.battadc = Adafruit_ADS1x15.ADS1115(address=int(self.config["s_level_i2c_addr"], 16))

		self.last_sample_time_temp 		= datetime.datetime.utcnow()
		self.last_sample_time_level		= datetime.datetime.utcnow()
		self.last_sample_time_charge	= datetime.datetime.utcnow()

		self.running = True

	def run(self):
		while self.running:
			current_time = datetime.datetime.utcnow()
			if (current_time - self.last_sample_time_temp).seconds >= self.config["i_temp_polling_period"]:
				self.last_sample_time_temp = current_time

				temp1, valid = self._getTemperatureDS18B20(self.config["s_temp1_sensor"])
				if valid:
					self.status["temp1"] = temp1

				temp2, valid = self._getTemperatureDS18B20(self.config["s_temp2_sensor"])
				if valid:
					self.status["temp2"] = temp2


			if (current_time - self.last_sample_time_level).seconds >= self.config["i_level_polling_period"]:
				self.last_sample_time_level = current_time

				raw_readings = [0] * 4
				raw_readings[0] = self.battadc.read_adc(0, gain=1)
				raw_readings[1] = self.battadc.read_adc(1, gain=1)
				raw_readings[2] = self.battadc.read_adc(2, gain=1)
				raw_readings[3] = self.battadc.read_adc(3, gain=1)

				readings = [25 if r >= self.config["i_pd_threshold"] else 0 for r in raw_readings]
				level = sum(readings)

				self.status["level"] = level

				if self.status["level"] == 0:
					self.status["charge_state"] = "IDLE"
				else:
					self.status["charge_state"] = "(DIS)CHARGING"

			total_p = self.parent.obc.status["consumption"] + self.parent.display.status["consumption"]
			self.status["t_left"] = ((float(self.status["level"])/100.0)*self.config["i_capacity_wh"]) / total_p

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)

			time.sleep(1)


class DCDC(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		GPIO.setup(self.config["i_j1a_sense_pin"], GPIO.IN)
		GPIO.setup(self.config["i_j1b_sense_pin"], GPIO.IN)


		self.status = 	{
								"power" : 0,
								"temp": 0,
								"j1a_power" : 0,
								"j1b_power" : 0
							}

		self.last_sample_time_temp		= datetime.datetime.utcnow()
		self.last_sample_time_sense		= datetime.datetime.utcnow()

		self.running = True

	def run(self):
		while self.running:
			current_time = datetime.datetime.utcnow()
			if (current_time - self.last_sample_time_temp).seconds >= self.config["i_temp_polling_period"]:
				self.last_sample_time_temp = current_time
				temp, valid = self._getTemperatureDS18B20(self.config["s_temp_sensor"])
				if valid:
					self.status["temp"] = temp

			if (current_time - self.last_sample_time_sense).seconds >= self.config["i_sense_polling_period"]:
				self.last_sample_time_sense = current_time

				self.status["j1a_power"] = int(GPIO.input(self.config["i_j1a_sense_pin"]))
				self.status["j1b_power"] = int(GPIO.input(self.config["i_j1b_sense_pin"]))

				if self.status["j1b_power"]:
					self.status["power"] = 1
				else:
					self.status["power"] = 0

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
			time.sleep(1)

class CustomINA219(INA219):

	"""
	Custom INA219 calibration due to use of 50mohm shunt resistor (standard is 100mohm)
	"""

	def set_custom_calibration_16V_3A(self):  # pylint: disable=invalid-name

		# VBUS_MAX = 16V
		# VSHUNT_MAX = 0.16          (Assumes Gain 3, 160mV)
		# RSHUNT = 0.05              (Resistor value in ohms)

		# 1. Determine max possible current
		# MaxPossible_I = VSHUNT_MAX / RSHUNT
		# MaxPossible_I = 3.2A

		# 2. Determine max expected current
		# MaxExpected_I = 3.0A

		# 3. Calculate possible range of LSBs (Min = 15-bit, Max = 12-bit)
		# MinimumLSB = MaxExpected_I/32767
		# MinimumLSB = 0.000091556              (uA per bit)
		# MaximumLSB = MaxExpected_I/4096
		# MaximumLSB = 0.0007324              (uA per bit)

		# 4. Choose an LSB between the min and max values
		#    (Preferrably a roundish number close to MinLSB)
		# CurrentLSB = 0.00016 (uA per bit)
		self._current_lsb = 0.0916  # in milliamps

		# 5. Compute the calibration register
		# Cal = trunc (0.04096 / (Current_LSB * RSHUNT))
		# Cal = 13434 (0x347a)

		self._cal_value = 8943

		# 6. Calculate the power LSB
		# PowerLSB = 20 * CurrentLSB
		# PowerLSB = 0.003 (3.048mW per bit)
		self._power_lsb = 0.001832

		# 7. Compute the maximum current and shunt voltage values before overflow
		#
		# 8. Compute the Maximum Power
		#

		# Set Calibration register to 'Cal' calcutated above
		self._raw_calibration = self._cal_value

		# Set Config register to take into account the settings above
		self.bus_voltage_range = BusVoltageRange.RANGE_16V
		self.gain = Gain.DIV_4_160MV
		self.bus_adc_resolution = ADCResolution.ADCRES_12BIT_4S
		self.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_4S
		self.mode = Mode.SANDBVOLT_CONTINUOUS


class OBC(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.running = True

		self.I2C_BUS = board.I2C()

		self.status = 	{
							"power": 1,
							"temp1": 0,
							"temp2": 0,
							"voltage" : 0,
							"current" : 0,
							"consumption" : 0
						 }

		self.ina219 = CustomINA219(self.I2C_BUS, addr=int(self.config["s_power_ina219_addr"], 16))
		self.ina219.set_custom_calibration_16V_3A()

	def _getInternalTemperature(self):
		output = subprocess.check_output(['vcgencmd', 'measure_temp'])
		floats = re.findall("\d+\.\d+", output.decode('utf-8'))
		return float(floats[0])

	def reboot(self):
		subprocess.run(["sudo reboot now"], shell=True)
		return {"success": True, "status": self.status}

	def shutdown(self):
		subprocess.run(["sudo shutdown now"], shell=True)
		return {"success": True, "status": self.status}

	def run(self):
		while self.running:
			self.status["temp1"] = self._getInternalTemperature()

			temp2, valid = self._getTemperatureDS18B20(self.config["s_temp_sensor"])
			if valid:
				self.status["temp2"] = temp2


			self.status["voltage"] = self.ina219.bus_voltage  # voltage on V- (load side)
			self.status["current"] = self.ina219.current/1000.0 # current in mA
			self.status["consumption"] = self.status["voltage"] * self.status["current"]

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
			time.sleep(self.config["i_polling_period"])



class Indicator(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = 	{
							"power" : 0
						}

		GPIO.setup(self.config["i_control_pin"], GPIO.OUT)
		GPIO.output(self.config["i_control_pin"], False)

		self.interval_high = self.config["f_interval_high"]
		self.interval_medium = self.config["f_interval_medium"]
		self.interval_low = self.config["f_interval_low"]

		self.interval = self.interval_low
		self._disable()

		self.running = True

	def _shutdown_thread(self):
		self._disable()
		self.running = False

	def _setHighInterval(self):
		self.interval = self.interval_high

	def _setMediumInterval(self):
		self.interval = self.interval_medium

	def _setLowInterval(self):
		self.interval = self.interval_low

	def _enable(self):
		self.alarm_active = True

	def _disable(self):
		self.alarm_active = False

	def set_power(self, power):
		if power:
			self._enable()
			self.status["power"] = 1
			return {"success": True, "status": self.status}
		else:
			self._disable()
			self.status["power"] = 0
			return {"success": True, "status": self.status}

	def run(self):
		while self.running:
			while self.alarm_active:
				GPIO.output(self.config["i_control_pin"], True)
				time.sleep(self.interval)

				GPIO.output(self.config["i_control_pin"], False)
				time.sleep(self.interval)
			time.sleep(0.5)
			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)



class RF(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = 	{
								"rf1_power": 0,
								"rf1_index": 0,
								"rf2_power": 0,
								"rf2_index": 0
							}

		self.running = True

	def run(self):
		while self.running:
			try:
				self.status["rf1_index"] = self._getDeviceIndex(self.config["s_rf1_serial"])
				self.status["rf1_power"] = 1
			except Exception as e:
				self.status["rf1_index"] = 0
				self.status["rf1_power"] = 0

			try:
				self.status["rf2_index"] = self._getDeviceIndex(self.config["s_rf2_serial"])
				self.status["rf2_power"] = 1
			except Exception as e:
				self.status["rf2_index"] = 0
				self.status["rf2_power"] = 0

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
			time.sleep(2)

	def _getDeviceIndex(self, serial):
		return RtlSdr.get_device_index_by_serial(serial)

class LAN():

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		self.status = 	{
							"power" : 0
						}

		if self.config["b_on_startup"]:
			self.set_power(True)
		else:
			self.set_power(False)

	def set_power(self, power):
		try:
			if power:
				subprocess.run(["sudo uhubctl -l 1-1 -p 1 -a 1"], shell=True)
				self.status["power"] = 1
				return {"success": True, "status": self.status}
			else:
				subprocess.run(["sudo ifconfig eth0 down"], shell=True)
				subprocess.run(["sudo uhubctl -l 1-1 -p 1 -a 0"], shell=True)
				self.status["power"] = 0
				return {"success": True, "status": self.status}
			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)

		except Exception as e:
			return {"success": False, "message": str(e)}

	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def toggle_power(self):
		if self.status["power"]:
			return self.set_power(False)
		else:
			return self.set_power(False)

	def set_config(self, key, value):
		if key == "s_id":
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}

class USB():

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		self.status = 	{
							"power" : 0
						}

		if self.config["b_on_startup"]:
			self.set_power(True)
		else:
			self.set_power(False)

	def set_power(self, power):
		try:
			if power:
				subprocess.run(["sudo uhubctl -l 1-1 -p 2 -a 1"], shell=True)
				self.status["power"] = 1
				return {"success": True, "status": self.status}
			else:
				subprocess.run(["sudo uhubctl -l 1-1 -p 2 -a 0"], shell=True)
				self.status["power"] = 0
				return {"success": True, "status": self.status}
			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)

		except Exception as e:
			return {"success": False, "message": str(e)}

	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def toggle_power(self):
		if self.status["power"]:
			return self.set_power(False)
		else:
			return self.set_power(False)

	def set_config(self, key, value):
		if key == "s_id":
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}


class Audio():

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		GPIO.setup(self.config["i_control_pin"], GPIO.OUT)
		self.mixer = alsaaudio.Mixer(self.config["s_mixer_name"])

		self.status = 	{
							"power" : 0,
							"volume": self.mixer.getvolume()[0],
							"mute": int(self.mixer.getmute()[0]),
							"test" : 0

						 }

		if self.config["b_on_startup"]:
			self.set_power(True)
		else:
			self.set_power(False)

		self.running = True

	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}

	def _shutdown_thread(self):
		self.set_power(False)
		self.running = False

	def set_volume(self, volume):
		try:
			self.mixer.setvolume(volume)
			self.status["volume"] = volume
			return {"success": True, "status": self.status}
		except Exception as e:
			return {"success": False, "message": str(e)}

	def increment_volume(self):
		try:
			self.mixer.setvolume(self.status["volume"] + 5)
			self.status["volume"] += 5
			return {"success": True, "status": self.status}
		except Exception as e:
			return {"success": False, "message": str(e)}

	def decrement_volume(self):
		try:
			self.mixer.setvolume(self.status["volume"] - 5)
			self.status["volume"] -= 5
			return {"success": True, "status": self.status}
		except Exception as e:
			return {"success": False, "message": str(e)}

	def set_mute(self, mute):
		try:
			self.mixer.setmute(mute)
			self.status["mute"] = int(mute)
			return {"success": True, "status": self.status}
		except Exception as e:
			return {"success": False, "message": str(e)}

	def toggle_mute(self):
		if self.status["mute"]:
			self.set_mute(False)
			return {"success": True, "status": self.status}
		else:
			self.set_mute(True)
			return {"success": True, "status": self.status}

	def set_test(self, test):
		if test:
			subprocess.run(["aplay {} &".format(self.config["s_test_wav"])], shell=True)
			return {"success": True, "test": 1}
		else:
			subprocess.run(["pkill -f {}".format(self.config["s_test_wav"])], shell=True)
			return {"success": True, "test": 0}
		self.status["test"] = int(test)

	def set_power(self, power):
		if power:
			GPIO.output(self.config["i_control_pin"], True)
			self.status["power"] = 1
			return {"success": True, "status": self.status}
		else:
			GPIO.output(self.config["i_control_pin"], False)
			self.status["power"] = 0
			return {"success": True, "status": self.status}

	def set_config(self, key, value):
		if key == "s_id":
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}

class Network(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = 		{
								"eth0" : "",
								"wlan0" : "",
								"wlan1" : ""
							}

		self.running = True

	def run(self):
		while self.running:
			try:
				eth0_if = netifaces.ifaddresses("eth0")
				if 2 in eth0_if:
					self.status["eth0"] = eth0_if[2][0]["addr"]
				else:
					self.status["eth0"] = "NO LINK"
			except Exception as e:
				print(str(e))
				self.status["eth0"] = "NOT AVLBL"

			try:
				wlan0_if = netifaces.ifaddresses("wlan0")
				if 2 in wlan0_if:
					self.status["wlan0"] = wlan0_if[2][0]["addr"]
				else:
					self.status["wlan0"] = "NO LINK"
			except Exception as e:
				self.status["wlan0"] = "NOT AVLBL"

			try:
				wlan1_if = netifaces.ifaddresses("wlan1")
				if 2 in wlan1_if:
					self.status["wlan1"] = wlan1_if[2][0]["addr"]
				else:
					self.status["wlan1"] = "NO LINK"
			except Exception as e:
				self.status["wlan1"] = "NOT AVLBL"

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
			time.sleep(self.config["i_polling_period"])


class Clock(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = 	{
							"time_utc": ""
						 }

		self.running = True

	def run(self):
		while self.running:
			self.status["time_utc"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
			time.sleep(1)


class Display(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.I2C_BUS = board.I2C()

		self.display_connected = os.path.isfile('/sys/class/backlight/rpi_backlight/max_brightness')

		if self.display_connected:
			self.backlight = Backlight()
			self.backlight.fade_duration = self.config["f_fade_duration"]
			self.status = {
								"power": int(self.backlight.power),
								"brightness": self.backlight.brightness,
								"voltage" : 0,
								"current" : 0,
								"consumption" : 0
							 }
		else:
			self.status = {
								"power": 0,
								"brightness": 0,
								"voltage" : 0,
								"current" : 0,
								"consumption" : 0
							 }


		if self.config["b_power_polling_enabled"]:
			self.ina219 = CustomINA219(self.I2C_BUS, addr=int(self.config["s_power_ina219_addr"], 16))
			self.ina219.set_custom_calibration_16V_3A()


		self.set_power(True)
		self.set_brightness(self.config["i_backlight_startup"])

		self.running = True

	def set_brightness(self, brightness):
		if self.display_connected:
			try:
				self.backlight.brightness = brightness
				self.status["brightness"] = brightness
				return {"success": True, "status": self.status}
			except Exception as e:
				return {"success": False, "message": str(e)}
		else:
			return {"success": False, "message": "No display connected"}

	def increment_brightness(self):
		if self.display_connected:
			try:
				self.backlight.brightness = self.status["brightness"] + 5
				self.status["brightness"] += 5
				return {"success": True, "status": self.status}
			except Exception as e:
				return {"success": False, "message": str(e)}
		else:
			return {"success": False, "message": "No display connected"}

	def decrement_brightness(self):
		if self.display_connected:
			try:
				self.backlight.brightness = self.status["brightness"] - 5
				self.status["brightness"] -= 5
				return {"success": True, "status": self.status}
			except Exception as e:
				return {"success": False, "message": str(e)}
		else:
			return {"success": False, "message": "No display connected"}

	def set_power(self, power):
		if self.display_connected:
			try:
				self.backlight.power = power
				self.status["power"] = int(power)
				return {"success": True, "status": self.status}
			except Exception as e:
				return {"success": False, "message": str(e)}
		else:
			return {"success": False, "message": "No display connected"}

	def toggle_power(self):
		if self.display_connected:
			try:
				self.backlight.power = not self.status["power"]
				self.status["power"] = int(self.backlight.power)
				return {"success": True, "status": self.status}
			except Exception as e:
				return {"success": False, "message": str(e)}
		else:
			return {"success": False, "message": "No display connected"}


	def screenshot(self):
		command = "export DISPLAY=:0; scrot -e 'mv $f /home/pi/Pictures/screenshots/; echo $f'"
		process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
		file = process.communicate()[0].strip()

		return {"success": True, "file": file}


	def run(self):
		while self.running:
			if self.config["b_power_polling_enabled"]:
				self.status["voltage"] = self.ina219.bus_voltage  # voltage on V- (load side)
				self.status["current"] = self.ina219.current/1000.0 # current in mA
				self.status["consumption"] = self.status["voltage"] * self.status["current"]

			self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
			time.sleep(self.config["i_polling_period"])




class GPS(GenericSystem):

	def __init__(self, parent, config):
		Thread.__init__(self)
		self.parent = parent
		self.config = config

		self.status = {
							"power" : 0,
							"mode" : 0,
							"sats_visible" : 0,
							"sats_used" : 0,
							"lat" : 0.0,
							"lon" : 0.0,
							"track" : 0.0,
							"hspeed" : 0.0,
							"time_utc" : "",
							#"error" : 0,
							"mgrs" : "",
							"grid" : "",
							"alt" : 0.0,
							"climb" : 0.0

						 }

		self.m = mgrs.MGRS()

		self.running = True
		self.connected = False

		self.set_power(True)
		self.set_power(False)

		if self.config["b_on_startup"]:
			self.set_power(True)

	def set_power(self, bool):
		if bool:
			subprocess.run(["../scripts/enable_gps.sh"], shell=True) #Enable GPSD and wake GPS
			time.sleep(0.5)
			try:
				gpsd.connect()
				self.connected = True
				self.status["power"] = int(self.connected)
				return {"success": True, "status": self.status}
			except Exception as e:
				print(str(e))
				return {"success": False, "message": str(e)}
		else:
			if self.status["power"]:
				self.connected = False
				subprocess.run(["../scripts/disable_gps.sh"], shell=True) #Enable GPSD and wake GPS
				self.status["power"] = int(self.connected)
				self.status["mode"] = 0
				self.status["sats_visible"] = 0
				self.status["sats_used"] = 0
				self.status["lat"] = 0.0
				self.status["lon"] = 0.0
				self.status["track"] = 0.0
				self.status["hspeed"] = 0.0
				self.status["time_utc"] = ""

				self.status["error_c"] = 0.0
				self.status["error_s"] = 0.0
				self.status["error_t"] = 0.0
				self.status["error_v"] = 0.0
				self.status["error_x"] = 0.0
				self.status["error_y"] = 0.0

				self.status["mgrs"] = ""
				self.status["grid"] = ""
				self.status["alt"] = 0.0
				self.status["climb"] = 0.0
				self.status["power"] = int(self.connected)
				return {"success": True, "status": self.status}
			else:
				return {"success": False, "message": "GPS is already disabled"}


	def to_grid(self, dec_lat, dec_lon):

		upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
		lower = 'abcdefghijklmnopqrstuvwx'
		adj_lat = dec_lat + 90.0
		adj_lon = dec_lon + 180.0
		grid_lat_sq = upper[int(adj_lat/10)];
		grid_lon_sq = upper[int(adj_lon/20)];
		grid_lat_field = str(int(adj_lat%10))
		grid_lon_field = str(int((adj_lon/2)%10))
		adj_lat_remainder = (adj_lat - int(adj_lat)) * 60
		adj_lon_remainder = ((adj_lon) - int(adj_lon/2)*2) * 60
		grid_lat_subsq = lower[int(adj_lat_remainder/2.5)]
		grid_lon_subsq = lower[int(adj_lon_remainder/5)]

		return grid_lon_sq + grid_lat_sq + grid_lon_field + grid_lat_field + grid_lon_subsq + grid_lat_subsq

	def _shutdown_thread(self):
		self.running = False
		self.connected = False


	def run(self):
		while self.running:
			while self.connected:

				self.packet = gpsd.get_current() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
				self.status["mode"] = self.packet.mode
				self.status["sats_visible"] = self.packet.sats
				self.status["sats_used"] = self.packet.sats_valid

				if self.status["mode"] == 0:

					self.status["lat"] = 0.0
					self.status["lon"] = 0.0
					self.status["track"] = 0.0
					self.status["hspeed"] = 0.0
					self.status["time_utc"] = ""

					self.status["error_c"] = 0.0
					self.status["error_s"] = 0.0
					self.status["error_t"] = 0.0
					self.status["error_v"] = 0.0
					self.status["error_x"] = 0.0
					self.status["error_y"] = 0.0

					self.status["mgrs"] = ""
					self.status["grid"] = ""
					self.status["alt"] = 0.0
					self.status["climb"] = 	0.0

				elif self.status["mode"] == 1:

					self.status["lat"] = 0.0
					self.status["lon"] = 0.0
					self.status["track"] = 0.0
					self.status["hspeed"] = 0.0
					self.status["time_utc"] = ""
					self.status["error_c"] = 0.0
					self.status["error_s"] = 0.0
					self.status["error_t"] = 0.0
					self.status["error_v"] = 0.0
					self.status["error_x"] = 0.0
					self.status["error_y"] = 0.0
					self.status["mgrs"] = ""
					self.status["grid"] = ""
					self.status["alt"] = 0.0
					self.status["climb"] = 	0.0

				elif self.status["mode"] == 2:

					self.status["lat"] = self.packet.lat
					self.status["lon"] = self.packet.lon
					self.status["track"] = self.packet.track
					self.status["hspeed"] = self.packet.track
					self.status["time_utc"] = str(self.packet.time)

					self.status["error_c"] = 0.0
					self.status["error_s"] = 0.0
					self.status["error_t"] = 0.0
					self.status["error_v"] = 0.0
					self.status["error_x"] = 0.0
					self.status["error_y"] = 0.0

					self.status["mgrs"] = self.m.toMGRS(self.packet.lat, self.packet.lon).decode('utf-8')
					self.status["grid"] = self.to_grid(self.packet.lat, self.packet.lon)
					self.status["alt"] = 0.0
					self.status["climb"] = 0.0

				elif self.status["mode"] == 3:

					self.status["lat"] = self.packet.lat
					self.status["lon"] = self.packet.lon
					self.status["track"] = self.packet.track
					self.status["hspeed"] = self.packet.track
					self.status["time_utc"] = str(self.packet.time)

					self.status["error_c"] = float(self.packet.error["c"])
					self.status["error_s"] = float(self.packet.error["s"])
					self.status["error_t"] = float(self.packet.error["t"])
					self.status["error_v"] = float(self.packet.error["v"])
					self.status["error_x"] = float(self.packet.error["x"])
					self.status["error_y"] = float(self.packet.error["y"])

					self.status["mgrs"] = self.m.toMGRS(self.packet.lat, self.packet.lon).decode('utf-8')
					self.status["grid"] = self.to_grid(self.packet.lat, self.packet.lon)
					self.status["alt"] = self.packet.alt
					self.status["climb"] = self.packet.climb

				self.parent.database.dumpData(id=self.config["s_id"], fields=self.status)
				time.sleep(1)
			time.sleep(0.5)


class Database():

	def __init__(self, parent, config):
		self.parent = parent
		self.config = config

		self.status = 	{
							"active" : 1
						}

		self.dbclient = InfluxDBClient(host=self.config["s_db_host"], port=self.config["i_db_port"], username=self.config["s_db_username"], password=self.config["s_db_password"], database=self.config["s_db_name"])

	def dumpData(self, id, fields):
		json_body = [{
						"measurement": id,
						"time": datetime.datetime.utcnow(),
						"fields": fields
					}]

		self.dbclient.write_points(json_body)


	def get_status(self):
		return {"success": True, "status": self.status}

	def get_config(self):
		return {"success": True, "config": self.config}


	def set_config(self, key, value):
		if key == "s_id":
			return {"success": False, "message": "Modification of s_id is not allowed"}
		else:
			if key in self.config:
				try:
					type_tag = key[:2]
					if type_tag == "s_":
						new_value = value
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "f_":
						new_value = float(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "b_":
						if value.lower() in ["true", "True", "1", "yes", "false", "False", "0", "no"]:
							new_value = self.parent.str2bool(value.lower())
							self.config[key] = new_value
							return {"success": True, "config": self.config}
						else:
							return {"success": False, "message": "Value {} not valid boolean".format(value)}
					elif type_tag == "i_":
						new_value = int(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}
					elif type_tag == "l_":
						new_value = json.loads(value)
						self.config[key] = new_value
						return {"success": True, "config": self.config}

				except Exception as e:
					return {"success": False, "message": "Exception occurred: {}".format(str(e))}

			else:
				return {"success": False, "message": "Key {} not present in target configuration dict".format(key)}
