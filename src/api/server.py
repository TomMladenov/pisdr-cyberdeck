#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import systems
import RPi.GPIO as GPIO
import board
from threading import Thread
from configparser import ConfigParser
import json
import os
from influxdb import InfluxDBClient
import datetime


class Server(object):

	def __init__(self, parent=None):
		super(Server, self).__init__()

		self.configurator = ConfigParser()
		self.configurator.read("/home/pi/git/pisdr-cyberdeck/src/api/config.ini")

		server_config = dict(self.load_config(self.configurator.items("server")))

		self.host = server_config["s_server_host"]
		self.port = server_config["i_server_port"]
		self.s_header_description = server_config["s_header_description"]

		GPIO.setmode(GPIO.BCM)
		self.I2C_BUS = board.I2C()

		#devices
		self.obc = systems.OBC(			self, dict(self.load_config(self.configurator.items("obc"))))
		self.display = systems.Display(	self, dict(self.load_config(self.configurator.items("display"))))
		self.battery = systems.Battery(	self, dict(self.load_config(self.configurator.items("battery"))))
		self.dcdc = systems.DCDC(		self, dict(self.load_config(self.configurator.items("dcdc"))))
		self.audio = systems.Audio(		self, dict(self.load_config(self.configurator.items("audio"))))
		self.usb = systems.USB(			self, dict(self.load_config(self.configurator.items("usb"))))
		self.lan = systems.LAN(			self, dict(self.load_config(self.configurator.items("lan"))))
		self.network = systems.Network(	self, dict(self.load_config(self.configurator.items("network"))))
		self.gps = systems.GPS(			self, dict(self.load_config(self.configurator.items("gps"))))
		self.rigctl = systems.RigCtl(	self, dict(self.load_config(self.configurator.items("rigctl"))))
		self.rf = systems.RF(			self, dict(self.load_config(self.configurator.items("rf"))))
		self.indicator = systems.Indicator(self, dict(self.load_config(self.configurator.items("indicator"))))
		self.publisher = systems.Publisher(self, dict(self.load_config(self.configurator.items("publisher"))))
		self.clock = systems.Clock(self, dict(self.load_config(self.configurator.items("clock"))))
		self.database = systems.Database(self, dict(self.load_config(self.configurator.items("database"))))

		#Processes
		self.aprs = systems.APRS(self, 		dict(self.load_config(self.configurator.items("aprs"))))
		self.ais = systems.AIS(self, 		dict(self.load_config(self.configurator.items("ais"))))
		self.rtltcp1 = systems.RTLTCP(self, dict(self.load_config(self.configurator.items("rtltcp1"))))
		self.rtltcp2 = systems.RTLTCP(self, dict(self.load_config(self.configurator.items("rtltcp2"))))
		self.rs1 = systems.RS(self, 		dict(self.load_config(self.configurator.items("rs1"))))
		self.rs2 = systems.RS(self, 		dict(self.load_config(self.configurator.items("rs2"))))
		self.acars = systems.ACARS(self, 	dict(self.load_config(self.configurator.items("acars"))))
		self.vdl = systems.VDL(self, 		dict(self.load_config(self.configurator.items("vdl"))))
		self.ism = systems.ISM(self, 		dict(self.load_config(self.configurator.items("ism"))))
		self.gqrx = systems.GQRX(self, 		dict(self.load_config(self.configurator.items("gqrx"))))
		self.proxy = systems.Proxy(self, 		dict(self.load_config(self.configurator.items("proxy"))))
		self.subscriber = systems.Subscriber(self, 		dict(self.load_config(self.configurator.items("subscriber"))))

		#Applications
		self.opencpn = 		systems.Application(self, dict(self.load_config(self.configurator.items("opencpn"))))
		self.fldigi = 		systems.Application(self, dict(self.load_config(self.configurator.items("fldigi"))))
		self.keyboard = 	systems.Application(self, dict(self.load_config(self.configurator.items("keyboard"))))
		self.navigation = 	systems.Application(self, dict(self.load_config(self.configurator.items("navigation"))))
		self.gpredict = 	systems.Application(self, dict(self.load_config(self.configurator.items("gpredict"))))
		self.vnc1 = 	systems.Application(self, dict(self.load_config(self.configurator.items("vnc1"))))
		self.vnc2 = 	systems.Application(self, dict(self.load_config(self.configurator.items("vnc2"))))

		self.systems = []
		self.systems.append(self.obc)
		self.systems.append(self.display)
		self.systems.append(self.battery)
		self.systems.append(self.dcdc)
		self.systems.append(self.audio)
		self.systems.append(self.usb)
		self.systems.append(self.lan)
		self.systems.append(self.network)
		self.systems.append(self.gps)
		self.systems.append(self.rigctl)
		self.systems.append(self.rf)
		self.systems.append(self.indicator)

		self.systems.append(self.publisher)
		self.systems.append(self.clock)
		self.systems.append(self.aprs)
		self.systems.append(self.ais)
		self.systems.append(self.vdl)
		self.systems.append(self.acars)
		self.systems.append(self.ism)
		self.systems.append(self.rs1)
		self.systems.append(self.rs2)
		self.systems.append(self.rtltcp1)
		self.systems.append(self.rtltcp2)
		self.systems.append(self.gqrx)
		self.systems.append(self.proxy)
		self.systems.append(self.subscriber)

		#self.systems.append(self.gqrx)
		self.systems.append(self.opencpn)
		self.systems.append(self.fldigi)
		self.systems.append(self.keyboard)
		self.systems.append(self.navigation)
		self.systems.append(self.gpredict)
		self.systems.append(self.vnc1)
		self.systems.append(self.vnc2)

		#Start threads
		status = [system.start() for system in self.systems if isinstance(system, Thread)]


	def str2bool(self, v):
	  return v.lower() in ("yes", "true", "t", "1")

	def load_config(self, items):
		result = []
		for (key, value) in items:
			type_tag = key[:2]
			if type_tag == "s_":
				result.append((key, value))
			elif type_tag == "f_":
				result.append((key, float(value)))
			elif type_tag == "b_":
				result.append((key, self.str2bool(value)))
			elif type_tag == "i_":
				result.append((key, int(value)))
			elif type_tag == "l_":
				result.append((key, json.loads(value)))
			else:
				raise ValueError('Invalid type tag {T} found in ini file at key {K}, value {V}'.format(T=type_tag, K=key, V=value))

		return result

	def get_systems(self):
		return {"success": True, "systems": [s.config["s_id"] for s in self.systems]}

	def get_status(self):
		status = []
		indexes = range(len(self.systems))
		keys = [s.config["s_id"] for s in self.systems]
		statuses = [s.status for s in self.systems]
		for i in indexes:
			status.append({"id": keys[i], "status": statuses[i]})
		return {"success": True, "status": status}

	def get_config(self):
		config = []
		indexes = range(len(self.systems))
		keys = [s.config["s_id"] for s in self.systems]
		configs = [s.config for s in self.systems]
		for i in indexes:
			config.append({"id": keys[i], "config": configs[i]})
		return {"success": True, "config": config}

	def get_configstatus(self):
		configstatus = []
		indexes = range(len(self.systems))
		keys = [s.config["s_id"] for s in self.systems]
		configs = [s.config for s in self.systems]
		statuses = [s.status for s in self.systems]
		for i in indexes:
			 configstatus.append({"id": keys[i], "config": configs[i], "status": statuses[i]})
		return {"success": True, "configstatus": configstatus}

	def save_config(self):
		current_config = self.get_config()["config"]
		self.configurator.read_dict(current_config)
		with open('config.ini', 'w') as f:
			self.configurator.write(f)
		return {"success": True}

	def stop_threads(self):
		status = [system._shutdown_thread() for system in self.systems if isinstance(system, Thread)]

	def shutdown(self):
		self.stop_threads()
		subprocess.run(["sudo shutdown now"], shell=True)

	def reboot(self):
		self.stop_threads()
		subprocess.run(["sudo reboot now"], shell=True)
