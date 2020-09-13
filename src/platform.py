#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import os
import struct
import sys
import time
from threading import Thread, Lock
from PyQt5.QtCore import (QCoreApplication, QObject, QRunnable, QThread, pyqtSignal, QEvent, Qt, QVariant, QTimer, QAbstractTableModel)
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QListWidgetItem, QFileDialog, QTableWidgetItem, qApp
from PyQt5.uic import loadUi
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QImage, QIcon, QPixmap, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QBrush
import numpy as np
import argparse
import datetime
import collections
import logging
import subprocess
from rpi_backlight import Backlight
import RPi.GPIO as GPIO
import re
import board
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219, Mode
from enum import Enum



class Platform():

	backlight = Backlight()

	gps = None

	current_volume = 0
	muted = False

	usb_lan_enabled = False
	ip_address = None

	dev = 0

	def __init__(self, parent):
		self.parent = parent
		self.logger = logging.getLogger('main_logger')
		self.logger.info('[PLATFORM] __init__() called')
		self.ip_address = self.getIpAddress()

		self.scriptpath = '/home/pi/git/pisdr-cyberdeck/src/scripts'

		self.backlight.fade_duration = 0.2
		self.current_volume, self.muted = self.getCurrentVolume()


		GPIO.setmode(GPIO.BCM)  # set board mode to Broadcom -> this means use GPIO numbers, NOT header pin numbers
		GPIO.setup(self.parent.datapool.AUDIO_PWR_PIN, GPIO.OUT)
		GPIO.setup(self.parent.datapool.GPS_PWR_PIN, GPIO.OUT)
		GPIO.setup(self.parent.datapool.IMU_PWR_PIN, GPIO.OUT)
		GPIO.setup(self.parent.datapool.ALARM_LED_PIN, GPIO.OUT)

		self.I2C_BUS = board.I2C()
		FNULL = open(os.devnull, 'w')


		try:
			self.gps = GPS(self, 'localhost', 2947)
			self.gps.start()
		except Exception as e:
			pass

		if self.parent.datapool.AUTOSTART_NAV:
			self.stopApplications()
			self.startNav()

		if self.parent.datapool.DISABLE_AUDIO_UPON_START:
			self.disableAudio()

		if self.parent.datapool.DISABLE_USB_UPON_START:
			self.disableUSB()

	def stopApplications(self):
		subprocess.run(["{PATH}/stop_all_applications.sh".format(PATH=self.scriptpath)], shell=True)

	def reboot(self):
		self.logger.info('[PLATFORM] reboot() called, proceeding to "sudo reboot now"...'.format(PATH=self.scriptpath))
		subprocess.run(["sudo reboot now"], shell=True)

	def shutdown(self):
		subprocess.run(["{PATH}/stop_all_applications.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] shutdown() called, ran script {PATH}/stop_all_applications.sh, proceeding to "sudo shutdown now"...'.format(PATH=self.scriptpath))
		subprocess.run(["sudo shutdown now"], shell=True)

	def takeScreenshot(self):
		subprocess.run(["scrot -e 'mv $f /home/pi/Pictures/screenshots/'"], shell=True)
		self.logger.info('[PLATFORM] takeScreenshot() called, moved to /home/pi/Pictures/screenshots/')
		return True

	def startAcars(self, serno):
		if serno == self.parent.datapool.RF1_SER:
			if self.parent.datapool.e_RF1_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_acars.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF1_SER, PPM=self.parent.datapool.RF1_PPM)], shell=True)
				self.logger.info('[PLATFORM] startAcars() called, run script {PATH}/start_acars.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startAcars() called, but RF1 unit does not have CONNECTED state')
		elif serno == self.parent.datapool.RF2_SER:
			if self.parent.datapool.e_RF2_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_acars.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF2_SER, PPM=self.parent.datapool.RF2_PPM)], shell=True)
				self.logger.info('[PLATFORM] startAcars() called, run script {PATH}/start_vdl.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startAcars() called, but RF2 unit does not have CONNECTED state')
		else:
			self.logger.error('[PLATFORM] startAcars() called, but supplied serial number invalid')

	def stopAcars(self):
		subprocess.run(["{PATH}/stop_acars.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopAcars() called, run script {PATH}/stop_acars.sh'.format(PATH=self.scriptpath))
		self.RTLsleep()
		return True

	def startVdl2(self, serno):
		if serno == self.parent.datapool.RF1_SER:
			if self.parent.datapool.e_RF1_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_vdl.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF1_SER, PPM=self.parent.datapool.RF1_PPM)], shell=True)
				self.logger.info('[PLATFORM] startVdl2() called, run script {PATH}/start_vdl.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startVdl2() called, but RF1 unit does not have CONNECTED state')
		elif serno == self.parent.datapool.RF2_SER:
			if self.parent.datapool.e_RF2_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_vdl.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF2_SER, PPM=self.parent.datapool.RF2_PPM)], shell=True)
				self.logger.info('[PLATFORM] startVdl2() called, run script {PATH}/start_vdl.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startVdl2() called, but RF2 unit does not have CONNECTED state')
		else:
			self.logger.error('[PLATFORM] startVdl2() called, but supplied serial number invalid')

	def stopVdl2(self):
		subprocess.run(["{PATH}/stop_vdl.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopVdl2() called, run script {PATH}/stop_vdl.sh'.format(PATH=self.scriptpath))
		self.RTLsleep()
		return True

	def startAIS(self, serno):
		if serno == RF1_SER:
			if self.parent.datapool.e_RF1_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_ais.sh {INDEX} {PPM}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF1_index, PPM=self.parent.datapool.RF1_PPM)], shell=True)
				self.logger.info('[PLATFORM] startAIS() called, run script {PATH}/start_ais.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startAIS() called, but RF1 unit does not have CONNECTED state')
		elif serno == RF2_SER:
			if self.parent.datapool.e_RF2_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_ais.sh {INDEX} {PPM}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF2_index, PPM=self.parent.datapool.RF2_PPM)], shell=True)
				self.logger.info('[PLATFORM] startAIS() called, run script {PATH}/start_ais.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startAIS() called, but RF2 unit does not have CONNECTED state')
		else:
			self.logger.error('[PLATFORM] startAIS() called, but supplied serial number invalid')

	def stopAIS(self):
		subprocess.run(["{PATH}/stop_ais.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopAIS() called, run script {PATH}/stop_ais.sh'.format(PATH=self.scriptpath))
		return True

	def startADSB(self, serno):
		if serno == self.parent.datapool.RF1_SER:
			if self.parent.datapool.e_RF1_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_adsb.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF1_SER, PPM=self.parent.datapool.RF1_PPM)], shell=True)
				self.logger.info('[PLATFORM] startADSB() called, run script {PATH}/start_adsb.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startADSB() called, but RF1 unit does not have CONNECTED state')
		elif serno == self.parent.datapool.RF2_SER:
			if self.parent.datapool.e_RF2_status == State.CONNECTED:
				subprocess.run(["{PATH}/start_adsb.sh {SERNO} {PPM}".format(PATH=self.scriptpath, SERNO=self.parent.datapool.RF2_SER, PPM=self.parent.datapool.RF2_PPM)], shell=True)
				self.logger.info('[PLATFORM] startADSB() called, run script {PATH}/start_adsb.sh'.format(PATH=self.scriptpath))
			else:
				self.logger.warning('[PLATFORM] startADSB() called, but RF2 unit does not have CONNECTED state')
		else:
			self.logger.error('[PLATFORM] startADSB() called, but supplied serial number invalid')

	def stopADSB(self):
		subprocess.run(["{PATH}/stop_adsb.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopADSB() called, run script {PATH}/stop_adsb.sh'.format(PATH=self.scriptpath))
		return True

	def startGQRX(self, serno, mode):
		if serno == self.parent.datapool.RF1_SER:
			if self.parent.datapool.e_RF1_status == State.CONNECTED:
				if mode == 'vhf':
					subprocess.run(["{PATH}/start_gqrx.sh {INDEX} {MODE}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF1_index, MODE='vhf')], shell=True)
					self.logger.info('[PLATFORM] startGQRX() called, run script {PATH}/start_gqrx.sh'.format(PATH=self.scriptpath))
				elif mode == 'hf':
					subprocess.run(["{PATH}/start_gqrx.sh {INDEX} {MODE}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF1_index, MODE='hf')], shell=True)
					self.logger.info('[PLATFORM] startGQRX() called, run script {PATH}/start_gqrx.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startGQRX() called, but passed mode invalid')
			else:
				self.logger.warning('[PLATFORM] startGQRX() called, but RF1 unit does not have CONNECTED state')
		elif serno == self.parent.datapool.RF2_SER:
			if self.parent.datapool.e_RF2_status == State.CONNECTED:
				if mode == 'vhf':
					subprocess.run(["{PATH}/start_gqrx.sh {INDEX} {MODE}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF2_index, MODE='vhf')], shell=True)
					self.logger.info('[PLATFORM] startGQRX() called, run script {PATH}/start_gqrx.sh'.format(PATH=self.scriptpath))
				elif mode == 'hf':
					subprocess.run(["{PATH}/start_gqrx.sh {INDEX} {MODE}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF2_index, MODE='hf')], shell=True)
					self.logger.info('[PLATFORM] startGQRX() called, run script {PATH}/start_gqrx.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startGQRX() called, but passed mode invalid')
			else:
				self.logger.warning('[PLATFORM] startGQRX() called, but RF2 unit does not have CONNECTED state')
		else:
			self.logger.error('[PLATFORM] startGQRX() called, but supplied serial number invalid')

	def stopGQRX(self):
		subprocess.run(["{PATH}/stop_gqrx.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopGQRX() called, run script {PATH}/stop_gqrx.sh'.format(PATH=self.scriptpath))
		return True

	def startGQRX_noconfig(self):
		subprocess.run(["{PATH}/start_gqrx_noconfig.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startGQRX_noconfig() called, run script {PATH}/start_gqrx_noconfig.sh'.format(PATH=self.scriptpath))
		return True

	def getCurrentVolume(self):
		output = subprocess.check_output(['amixer', 'get', 'Master'])
		lines_full = output.decode('utf-8')
		if '[on]' in lines_full:
			muted = False
		elif '[off]' in lines_full:
			muted = True
		lines = output.decode('utf-8').split('\n')
		line = lines[4]
		ints = re.findall(r'\d+', line)
		master = ints[1]
		return master, muted

	def getCurrentBacklight(self):
		current_brightness = self.backlight.brightness
		return current_brightness

	def stopNav(self):
		subprocess.run(["{PATH}/stop_xastir.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopNav() called, run script {PATH}/stop_xastir.sh'.format(PATH=self.scriptpath))

	def startNav(self):
		subprocess.run(["{PATH}/start_xastir.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startNav() called, run script {PATH}/start_xastir.sh'.format(PATH=self.scriptpath))

	def startDigi(self):
		subprocess.run(["{PATH}/start_fldigi.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startDigi() called, run script {PATH}/start_fldigi.sh'.format(PATH=self.scriptpath))

	def stopDigi(self):
		subprocess.run(["{PATH}/stop_fldigi.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopDigi() called, run script {PATH}/stop_fldigi.sh'.format(PATH=self.scriptpath))

	def startKeyboard(self):
		subprocess.run(["{PATH}/start_keyboard.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startKeyboard() called, run script {PATH}/start_keyboard.sh'.format(PATH=self.scriptpath))

	def startKrono(self):
		subprocess.run(["{PATH}/start_chrono.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startKrono() called, run script {PATH}/start_chrono.sh'.format(PATH=self.scriptpath))

	def mute(self):
		subprocess.run(["amixer set Master mute"], shell=True)
		self.current_volume, self.muted = self.getCurrentVolume()
		self.logger.info('[PLATFORM] mute() called, current volume: {CURRENT_VOLUME}, muted: {CURRENT_MUTE}'.format(CURRENT_VOLUME=self.current_volume, CURRENT_MUTE=self.muted))

	def unMute(self):
		subprocess.run(["amixer set Master unmute"], shell=True)
		self.current_volume, self.muted = self.getCurrentVolume()
		self.logger.info('[PLATFORM] unMute() called, current volume: {CURRENT_VOLUME}, muted: {CURRENT_MUTE}'.format(CURRENT_VOLUME=self.current_volume, CURRENT_MUTE=self.muted))

	def toggleMute(self):
		if self.muted:
			self.unMute()
			return False
		else:
			self.mute()
			return True

	def getIpAddress(self):
		try:
			output = subprocess.check_output(['ip', '-4', 'addr', 'show', 'eth0'])
			lines = output.decode('utf-8').split('\n')
			line = lines[1]
			final = line.split('brd')
			line = final[0]
			return line.replace(' ', '').replace('inet', '')
		except Exception as e:
			return 'no IP'

	def incrementVolume(self):
		subprocess.run(["amixer set Master 5%+ &"], shell=True)
		self.current_volume, self.muted = self.getCurrentVolume()
		self.logger.info('[PLATFORM] incrementVolume() called, current volume: {CURRENT_VOLUME}, muted: {CURRENT_MUTE}'.format(CURRENT_VOLUME=self.current_volume, CURRENT_MUTE=self.muted))
		return self.current_volume, self.muted

	def decrementVolume(self):
		subprocess.run(["amixer set Master 5%- &"], shell=True)
		self.current_volume, self.muted = self.getCurrentVolume()
		self.logger.info('[PLATFORM] decrementVolume() called, current volume: {CURRENT_VOLUME}, muted: {CURRENT_MUTE}'.format(CURRENT_VOLUME=self.current_volume, CURRENT_MUTE=self.muted))
		return self.current_volume, self.muted

	def incrementBacklight(self):
		try:
			current_brightness = self.backlight.brightness
			self.backlight.brightness = current_brightness + 5
		except Exception as e:
			pass
		current_brightness = self.backlight.brightness
		self.logger.info('[PLATFORM] incrementBacklight() called, current brightness: {CURRENT_VOLUME}/255'.format(CURRENT_VOLUME=current_brightness))
		return current_brightness

	def decrementBacklight(self):
		try:
			current_brightness = self.backlight.brightness
			if current_brightness <= 5:
				pass
			else:
				self.backlight.brightness = current_brightness - 5
		except Exception as e:
			pass
		current_brightness = self.backlight.brightness
		self.logger.info('[PLATFORM] decrementBacklight() called, current brightness: {CURRENT_VOLUME}/255'.format(CURRENT_VOLUME=current_brightness))
		return current_brightness

	def toggleDisplayPower(self):
		if self.backlight.power:
			self.backlight.power = False
		else:
			self.backlight.power = True

	def startGpsMon(self):
		subprocess.run(["lxterminal -e gpsmon"], shell=True)
		self.logger.info('[PLATFORM] startGpsMon() called, run command lxterminal -e gpsmon')

	def startKernelLog(self):
		subprocess.run(["lxterminal -e 'dmesg -w'"], shell=True)
		self.logger.info("[PLATFORM] startKernelLog() called, run command lxterminal -e 'dmesg -w'")

	def startSysLog(self):
		subprocess.run(["lxterminal -e 'tail -f {PATH}/main.log'".format(PATH=self.parent.datapool.MAIN_LOG_PATH)], shell=True)
		self.logger.info("[PLATFORM] startSysLog() called, run command lxterminal -e 'tail -f /home/pi/log/cyberbox.log'")

	def startOpenCPN(self):
		subprocess.run(["{PATH}/start_opencpn.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] startOpenCPN() called, run script {PATH}/start_opencpn.sh'.format(PATH=self.scriptpath))

	def stopOpenCPN(self):
		subprocess.run(["{PATH}/stop_opencpn.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopOpenCPN() called, run script {PATH}/stop_opencpn.sh'.format(PATH=self.scriptpath))

	def enableUSB(self):
		subprocess.run(["sudo uhubctl -l 1-1 -p 2 -a 1"], shell=True)
		self.parent.datapool.b_usb_enabled = True
		time.sleep(1)
		self.RTLsleep() #Doing this after a USB power cycle seems to reduce RTL sdr drawn current from 0.110A to 0.01A
		self.logger.info('[PLATFORM] enableUSB() called')

	def RTLsleep(self):
		subprocess.run(["sudo rtl_eeprom -d 0 -r /tmp/rtl_config"], shell=True)
		subprocess.run(["sudo rtl_eeprom -d 1 -r /tmp/rtl_config"], shell=True)

	def disableUSB(self):
		subprocess.run(["sudo uhubctl -l 1-1 -p 2 -a 0"], shell=True)
		self.parent.datapool.b_usb_enabled = False
		self.logger.info('[PLATFORM] disableUSB() called')

	def enableWlan(self):
		subprocess.run(["sudo iwconfig wlan0 txpower auto; sudo iwconfig wlan0 txpower auto"], shell=True)
		self.logger.info('[PLATFORM] enableWlan() called')

	def disableWlan(self):
		subprocess.run(["sudo iwconfig wlan0 txpower off"], shell=True)
		self.logger.info('[PLATFORM] disableWlan() called')

	def startFileManager(self):
		subprocess.run(["pcmanfm"], shell=True)
		self.logger.info('[PLATFORM] startFileManager() called')

	def testAudio(self):
		self.parent.alarm.enable()
		subprocess.run(["aplay /home/pi/git/uwave-eas/eas-attn-8s-n40db.wav"], shell=True)
		self.parent.alarm.disable()
		self.logger.info('[PLATFORM] testAudio() called')

	def enableAudio(self):
		GPIO.setup(self.parent.datapool.AUDIO_PWR_PIN, GPIO.OUT)
		GPIO.output(self.parent.datapool.AUDIO_PWR_PIN, True)
		self.parent.datapool.b_audio_enabled = True
		self.logger.info('[PLATFORM] enableAudio() called')

	def disableAudio(self):
		GPIO.setup(self.parent.datapool.AUDIO_PWR_PIN, GPIO.OUT)
		GPIO.output(self.parent.datapool.AUDIO_PWR_PIN, False)
		self.parent.datapool.b_audio_enabled = False
		self.logger.info('[PLATFORM] disableAudio() called')

	def enableGPS(self):
		GPIO.output(self.parent.datapool.GPS_PWR_PIN, True)
		self.logger.info('[PLATFORM] enableGPS() called')

	def disableGPS(self):
		GPIO.output(self.parent.datapool.GPS_PWR_PIN, False)
		self.logger.info('[PLATFORM] disableGPS() called')

	def enableIMU(self):
		GPIO.output(self.parent.datapool.IMU_PWR_PIN, True)
		self.logger.info('[PLATFORM] enableIMU() called')

	def disableIMU(self):
		GPIO.output(self.parent.datapool.IMU_PWR_PIN, False)
		self.logger.info('[PLATFORM] disableIMU() called')

	def stopRtlTcp(self):
		subprocess.run(["{PATH}/stop_rtltcp.sh".format(PATH=self.scriptpath)], shell=True)
		self.logger.info('[PLATFORM] stopRtlTcp() called, run script {PATH}/stop_rtltcp.sh'.format(PATH=self.scriptpath))

	def startTcpServer(self, serno, lantype):
		if lantype == 'LAN' and self.parent.datapool.b_eth0_status == State.CONNECTED:
			ip = self.parent.datapool.s_eth0_ip
			if serno == self.parent.datapool.RF1_SER:
				if self.parent.datapool.e_RF1_status == State.CONNECTED:
					subprocess.run(["{PATH}/start_tcpserver.sh {INDEX} {PPM} {IP} {PORT}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF1_index, PPM=self.parent.datapool.RF1_PPM, IP=ip, PORT=self.parent.datapool.RF1_TCP_PORT)], shell=True)
					self.logger.info('[PLATFORM] startTcpServer() called, run script {PATH}/start_tcpserver.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startTcpServer() called, but RF1 unit does not have CONNECTED state')
			elif serno == self.parent.datapool.RF2_SER:
				if self.parent.datapool.e_RF2_status == State.CONNECTED:
					subprocess.run(["{PATH}/start_tcpserver.sh {INDEX} {PPM} {IP} {PORT}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF2_index, PPM=self.parent.datapool.RF2_PPM , IP=ip, PORT=self.parent.datapool.RF2_TCP_PORT)], shell=True)
					self.logger.info('[PLATFORM] startTcpServer() called, run script {PATH}/start_tcpserver.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startTcpServer() called, but RF2 unit does not have CONNECTED state')
			else:
				self.logger.error('[PLATFORM] startTcpServer() called, but supplied serial number invalid')
		elif lantype == 'WLAN' and self.parent.datapool.b_wlan0_status == State.CONNECTED:
			ip = self.parent.datapool.s_wlan0_ip
			if serno == self.parent.datapool.RF1_SER:
				if self.parent.datapool.e_RF1_status == State.CONNECTED:
					subprocess.run(["{PATH}/start_tcpserver.sh {INDEX} {PPM} {IP} {PORT}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF1_index, PPM=self.parent.datapool.RF1_PPM, IP=self.parent.datapool.s_wlan0_ip, PORT=38211)], shell=True)
					self.logger.info('[PLATFORM] startTcpServer() called, run script {PATH}/start_tcpserver.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startTcpServer() called, but RF1 unit does not have CONNECTED state')
			elif serno == self.parent.datapool.RF2_SER:
				if self.parent.datapool.e_RF2_status == State.CONNECTED:
					subprocess.run(["{PATH}/start_tcpserver.sh {INDEX} {PPM} {IP} {PORT}".format(PATH=self.scriptpath, INDEX=self.parent.datapool.i_RF2_index, PPM=self.parent.datapool.RF2_PPM , IP=self.parent.datapool.s_wlan0_ip, PORT=38212)], shell=True)
					self.logger.info('[PLATFORM] startTcpServer() called, run script {PATH}/start_tcpserver.sh'.format(PATH=self.scriptpath))
				else:
					self.logger.warning('[PLATFORM] startTcpServer() called, but RF2 unit does not have CONNECTED state')
			else:
				self.logger.error('[PLATFORM] startTcpServer() called, but supplied serial number invalid')
		else:
			self.logger.error('[PLATFORM] startTcpServer() called, but supplied interface is not up or is wrong')

	def setBiasTeeUnit(self, unit, enabled):
		if enabled:
			biast_enabled = 1
		else:
			biast_enabled = 0
		subprocess.run(["/home/pi/git/rtl-sdr-blog/build/src/rtl_biast -d {UNIT} -b {ENABLED}".format(UNIT=unit, ENABLED=biast_enabled)], shell=True)
		self.logger.info('[PLATFORM] setBiasTeeUnit({UNIT}, {ENABLED}) called'.format(UNIT=unit, ENABLED=biast_enabled))
