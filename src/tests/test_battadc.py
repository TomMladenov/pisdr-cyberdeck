#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import os
import sys
import time
import datetime
import subprocess
import board

import Adafruit_ADS1x15


if __name__ == '__main__':

	adc = Adafruit_ADS1x15.ADS1115(address=0x48)

	GAIN = 1

	while True:
		try:
			capacity1_raw = adc.read_adc(0, gain=GAIN)
			capacity2_raw = adc.read_adc(1, gain=GAIN)
			capacity3_raw = adc.read_adc(2, gain=GAIN)
			capacity4_raw = adc.read_adc(3, gain=GAIN)

			print('{CH1}  {CH2}  {CH3}  {CH4}'.format(CH1=capacity1_raw, CH2=capacity2_raw, CH3=capacity3_raw, CH4=capacity4_raw))

		except Exception as e:
			print(e)

		time.sleep(1)
