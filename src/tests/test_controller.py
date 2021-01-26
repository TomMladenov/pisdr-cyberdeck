#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import os
import sys
import time
import datetime
import subprocess
import RPi.GPIO as GPIO
import board
import crc8

from adafruit_bus_device.i2c_device import I2CDevice

CMD_ID = 0x33
PARAM_ID = 0x54

if __name__ == '__main__':

	controller_device = I2CDevice(board.I2C(), 0x04)
	#hash = crc8.crc8()


	while True:
		try:
			if PARAM_ID == 0x53:
				command = '{command_id};{param_id};{gps_lat};{gps_lon}'.format(command_id=CMD_ID, param_id=PARAM_ID, gps_lat=50.02, gps_lon=8.4013)
				rList = command.encode('utf-8')
			elif PARAM_ID == 0x54:
				now = datetime.datetime.utcnow()
				command = [CMD_ID, PARAM_ID, int(now.hour), int(now.minute), int(now.second), int(now.year)-2000, int(now.month), int(now.day)]
				rList = command

			arr = bytearray(rList)
			payload = arr #+ bytearray.fromhex(str(crc))
			controller_device.write(payload)
			print(str(payload))

		except Exception as e:
			print(e)

		time.sleep(1)
