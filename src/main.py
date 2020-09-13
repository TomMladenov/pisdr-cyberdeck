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
import gpsd
import mgrs
import re
from enum import Enum

import board
from rpi_backlight import Backlight
import RPi.GPIO as GPIO
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219, Mode

from datapool import Datapool
from platform import Platform
from configuration import *


upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
lower = 'abcdefghijklmnopqrstuvwx'

def to_grid(dec_lat, dec_lon):

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

def is_time_between(begin_time, end_time, check_time=None):
	# If check time is not given, default to current UTC time
	check_time = check_time or datetime.datetime.utcnow().time()
	if begin_time < end_time:
		return check_time >= begin_time and check_time <= end_time
	else: # crosses midnight
		return check_time >= begin_time or check_time <= end_time


GPIO.setmode(GPIO.BCM)  # set board mode to Broadcom -> this means use GPIO numbers, NOT header pin numbers
GPIO.setup(AUDIO_PWR_PIN, GPIO.OUT)
GPIO.setup(GPS_PWR_PIN, GPIO.OUT)
GPIO.setup(IMU_PWR_PIN, GPIO.OUT)
GPIO.setup(ALARM_LED_PIN, GPIO.OUT)

I2C_BUS = board.I2C()
FNULL = open(os.devnull, 'w')

class State(Enum):
	CONNECTED = 1
	DISCONNECTED = 2
	NO_LINK = 3

class Statusbar(QDialog):

	def __init__(self, parent=None):
		super(Statusbar, self).__init__(parent)
		gui = path + '/gui/statusbar.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.move(0, 452)
		self.show()


class Barmenu(QWidget):

	def __init__(self, parent=None):
		super(Barmenu, self).__init__(parent)
		gui = path + '/gui/barmenu.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.move(500, 320)
		self.show()

	def popup(self):
		self.show()
		self.activateWindow()


class MenuWindow(QWidget):

	def __init__(self, parent=None):
		super(MenuWindow, self).__init__(parent)
		gui = path + '/gui/menu_2.ui'
		loadUi(gui, self)
		self.move(0, 0)

		header = self.data_view.horizontalHeader()
		header.setSectionResizeMode(3)

		self.model = TableModel([])
		self.model.setHeader(['Source', 'Frequency', 'UTC Start time', 'ID', 'Message'])


		self.data_view.setModel(self.model)
		self.data_view.show()

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.show()

	def popup(self):
		self.show()
		self.activateWindow()


class TableModel(QAbstractTableModel):

	def __init__(self, data):
		QAbstractTableModel.__init__(self)
		self._data = data

	def setHeader(self, header):
		self._header = header

	def rowCount(self, parent):
		return len(self._data)

	def columnCount(self, parent):
		return len(self._header)

	def data(self, index, role):
		if role != Qt.DisplayRole:
			return QVariant()
		elif role == Qt.DecorationRole:
			if not self._data[index.row()][8] == True:
				return QtGui.QColor(0,255,0)
			else:
				return QtGui.QColor(255,0,0)
		else:
			if index.column() == 0:
				return str(self._data[index.row()][index.column()])
			elif index.column() == 1:
				return self._data[index.row()][index.column()]
			elif index.column() == 2:
				return str(self._data[index.row()][index.column()])
			elif index.column() == 3:
				return str(round(self._data[index.row()][index.column()], 1))
			elif index.column() == 4:
				return str(round(self._data[index.row()][index.column()], 1))
			elif index.column() == 5:
				return str(self._data[index.row()][7])
			elif index.column() == 6:
				return str(round(self._data[index.row()][8], 1))
			elif index.column() == 7:
				return str(round(self._data[index.row()][9], 1))
			elif index.column() == 8:
				return str(round(self._data[index.row()][6], 1))
			elif index.column() == 9:
				return str(not self._data[index.row()][10])

		self.model.setHeader(['Source', 'Frequency', 'UTC Start time', 'ID', 'Message'])

	def headerData(self, section, orientation, role):
		if role != Qt.DisplayRole or orientation != Qt.Horizontal:
			return QVariant()
		return self._header[section]



class MessageWindow(QWidget):

	def __init__(self, parent=None):
		super(MessageWindow, self).__init__(parent)
		gui = path + '/gui/message_window.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.move(180, 180)
		self.hide()

	def popup(self):
		self.show()
		self.activateWindow()


class Main(QMainWindow):

	buttonStyleIdle = 		"border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186);"
	buttonStyleClicked = 	"border: 1px solid black; border-radius: 25px; background-color: rgb(0, 255, 0);"
	buttonStyleClickedRed = "border: 1px solid black; border-radius: 25px; background-color: rgb(255, 0, 0);"

	boxStyleNight = 		"background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
	boxStyleNormal = 		""

	buttonStyleIdleNight = 		"border: 1px solid red; border-radius: 25px; background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
	buttonStyleClickedNight = 	"border: 1px solid red; border-radius: 25px; background-color: rgb(255, 0, 0); color: rgb(0, 0, 0);"

	nightModeBackground = 	"background-color: rgb(0, 0, 0);"
	normalBackground = 		'background-color: rgb(186, 186, 186);'

	GREEN = 				'background-color: rgb(0, 255, 0);'
	RED = 					'background-color: rgb(255, 0, 0);'
	ORANGE =				'background-color: rgb(255, 165, 0);'

	blackTextRedBackground = "background-color: rgb(255, 0, 0); color: rgb(0, 0, 0);"

	nightModeEnabled = False

	def __init__(self, parent=None):
		super(Main, self).__init__(parent)
		gui = path + '/gui/toolbar.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.statusBar().hide()
		self.move(732, 0)

		#---------DATAPOOL----------
		self.datapool = Datapool()
		#---------------------------

		#---------WINDOWS-----------
		self.statusbar = Statusbar()
		self.messagewindow = MessageWindow()
		self.menuwindow = MenuWindow()
		self.menuwindow.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.barmenu = Barmenu()
		#---------------------------


		self.menuwindow.adsb_combo.addItem(RF1_SER)
		self.menuwindow.adsb_combo.addItem(RF2_SER)
		self.menuwindow.acars_combo.addItem(RF1_SER)
		self.menuwindow.acars_combo.addItem(RF2_SER)
		self.menuwindow.vdl2_combo.addItem(RF1_SER)
		self.menuwindow.vdl2_combo.addItem(RF2_SER)
		self.menuwindow.ais_combo.addItem(RF1_SER)
		self.menuwindow.ais_combo.addItem(RF2_SER)
		self.menuwindow.aprs_combo.addItem(RF1_SER)
		self.menuwindow.aprs_combo.addItem(RF2_SER)

		self.menuwindow.tcprf1_combo_box.addItem('LAN')
		self.menuwindow.tcprf1_combo_box.addItem('WLAN')

		self.menuwindow.tcprf2_combo_box.addItem('LAN')
		self.menuwindow.tcprf2_combo_box.addItem('WLAN')

		self.menuwindow.gqrx_mode_combo.addItem('hf')
		self.menuwindow.gqrx_mode_combo.addItem('vhf')
		self.menuwindow.gqrx_dev_combo.addItem(RF1_SER)
		self.menuwindow.gqrx_dev_combo.addItem(RF2_SER)

		self.menuwindow.rf1_tcp_port_label.setText(str(RF1_TCP_PORT))
		self.menuwindow.rf2_tcp_port_label.setText(str(RF2_TCP_PORT))

		self.platform = Platform(self)
		vol, muted = self.platform.getCurrentVolume()
		self.statusbar.vol_label.setText('Vol: ' + str(vol) + '%')

		bl = self.platform.getCurrentBacklight()
		self.statusbar.bl_label.setText('BL: ' + str(bl) + '%')

		#----VOLUME-----
		self.volup_button.pressed.connect(self.incrementVolume)
		self.voldown_button.pressed.connect(self.decrementVolume)
		self.mute_button.pressed.connect(self.toggleMute)
		#---------------------------


		#----BACKLIGHT----
		self.toolbar_backlight_up_button.pressed.connect(self.incrementBacklight)
		self.toolbar_backlight_down_button.pressed.connect(self.decrementBacklight)
		#---------------------------


		#----MAIN BUTTONS----
		self.toolbar_nav_button.pressed.connect(self.platform.startNav)
		self.toolbar_key_button.pressed.connect(self.platform.startKeyboard)
		self.toolbar_gqrx_button.pressed.connect(self.platform.startGQRX_noconfig)
		self.menu_button.pressed.connect(self.menuwindow.popup)
		self.menuwindow.exit_button.pressed.connect(self.exitApplication)
		self.menuwindow.reboot_button.pressed.connect(self.reboot)
		self.menuwindow.shutdown_button.pressed.connect(self.shutdown)
		self.menuwindow.nightmode_button.pressed.connect(self.toggleNightMode)

		self.screenshot_button.pressed.connect(self.takeScreenshot)


		#Tab switcher
		self.menuwindow.obc_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(0))
		self.menuwindow.nav_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(1))
		self.menuwindow.env_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(2))
		self.menuwindow.data_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(3))
		self.menuwindow.apps_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(4))
		self.menuwindow.mon_button.pressed.connect(lambda: self.menuwindow.stackedWidget.setCurrentIndex(5))

		self.menuwindow.enable_usb_button.pressed.connect(self.platform.enableUSB)
		self.menuwindow.disable_usb_button.pressed.connect(self.platform.disableUSB)

		self.menuwindow.enable_audio_button.pressed.connect(self.platform.enableAudio)
		self.menuwindow.disable_audio_button.pressed.connect(self.platform.disableAudio)

		self.menuwindow.enable_gps_button.pressed.connect(self.platform.enableGPS)
		self.menuwindow.disable_gps_button.pressed.connect(self.platform.disableGPS)

		self.menuwindow.enable_imu_button.pressed.connect(self.platform.enableIMU)
		self.menuwindow.disable_imu_button.pressed.connect(self.platform.disableIMU)

		self.menuwindow.enable_wlan_button.pressed.connect(self.platform.enableWlan)
		self.menuwindow.disable_wlan_button.pressed.connect(self.platform.disableWlan)

		self.menuwindow.chrono_button.pressed.connect(self.platform.startKrono)
		self.menuwindow.test_speaker_button.pressed.connect(self.platform.testAudio)
		self.menuwindow.file_manager_button.pressed.connect(self.platform.startFileManager)

		self.messagewindow.ok_button.pressed.connect(self.messagewindow.hide)
		self.messagewindow.cancel_button.pressed.connect(self.messagewindow.hide)


		self.menuwindow.start_adsb_button.pressed.connect(self.startADSB)
		self.menuwindow.stop_adsb_button.pressed.connect(self.stopADSB)
		self.menuwindow.start_ais_button.pressed.connect(self.startAIS)
		self.menuwindow.stop_ais_button.pressed.connect(self.stopAIS)
		self.menuwindow.start_acars_button.pressed.connect(self.startAcars)
		self.menuwindow.stop_acars_button.pressed.connect(self.stopAcars)
		self.menuwindow.start_vdl2_button.pressed.connect(self.startVdl2)
		self.menuwindow.stop_vdl2_button.pressed.connect(self.stopVdl2)
		self.menuwindow.start_gqrx_button.pressed.connect(self.startGQRX)
		self.menuwindow.stop_gqrx_button.pressed.connect(self.stopGQRX)
		self.menuwindow.start_opencpn_button.pressed.connect(self.platform.startOpenCPN)
		self.menuwindow.stop_opencpn_button.pressed.connect(self.platform.stopOpenCPN)
		self.menuwindow.start_gpsmon_button.pressed.connect(self.platform.startGpsMon)
		self.menuwindow.start_xastir_button.pressed.connect(self.platform.startNav)
		self.menuwindow.stop_xastir_button.pressed.connect(self.platform.stopNav)

		self.menuwindow.start_fldigi_button.pressed.connect(self.platform.startDigi)
		self.menuwindow.stop_fldigi_button.pressed.connect(self.platform.stopDigi)

		self.toolbar_screen_onoff_button.clicked.connect(self.platform.toggleDisplayPower)

		self.menuwindow.start_dmesg_button.pressed.connect(self.platform.startKernelLog)
		self.menuwindow.start_syslog_button.pressed.connect(self.platform.startSysLog)

		self.menuwindow.start_tcprf1_button.pressed.connect(self.startTcpRF1)
		self.menuwindow.start_tcprf2_button.pressed.connect(self.startTcpRF2)

		self.menuwindow.stop_rtltcp_button.pressed.connect(self.platform.stopRtlTcp)

		self.alarm = AlarmIndicator(self)
		self.alarm.alarmHighSignal.connect(self.flashOBCbutton)
		self.poller = Poller(parent=self)
		self.powerpoller = TempPowerPoller(parent=self)

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.tickTock)
		self.timer.timeout.connect(self.updateGui)

		self.timer.start(500)
		self.alarm.start()
		self.poller.start()
		self.powerpoller.start()

		if is_time_between(datetime.time(6,00), datetime.time(20,0)):
			self.disableNightMode()
		else:
			self.enableNightMode()

	def startTcpRF1(self):
		lantype = self.menuwindow.tcprf1_combo_box.currentText()
		self.platform.startTcpServer(RF1_SER, lantype)

	def startTcpRF2(self):
		lantype = self.menuwindow.tcprf2_combo_box.currentText()
		self.platform.startTcpServer(RF2_SER, lantype)

	def toggleMute(self):
		status = self.platform.toggleMute()
		if self.nightModeEnabled:
			if status:
				self.mute_button.setStyleSheet(self.buttonStyleClickedNight)
			else:
				self.mute_button.setStyleSheet(self.buttonStyleIdleNight)
		else:
			if status:
				self.mute_button.setStyleSheet(self.buttonStyleClickedRed)
			else:
				self.mute_button.setStyleSheet(self.buttonStyleIdle)

	def flashOBCbutton(self, bool):
		if self.nightModeEnabled:
			if bool:
				self.menuwindow.obc_button.setStyleSheet(self.buttonStyleClickedNight)
			else:
				self.menuwindow.obc_button.setStyleSheet(self.buttonStyleIdleNight)
		else:
			if bool:
				self.menuwindow.obc_button.setStyleSheet(self.buttonStyleClickedRed)
			else:
				self.menuwindow.obc_button.setStyleSheet(self.buttonStyleIdle)

	def setWarning(self, widget, warn, err):
		if self.nightModeEnabled:
			if err or warn:
				widget.setStyleSheet(self.blackTextRedBackground)
			else:
				widget.setStyleSheet(self.boxStyleNight)
		else:
			if err:
				widget.setStyleSheet(self.RED)
			elif warn:
				widget.setStyleSheet(self.ORANGE)
			else:
				widget.setStyleSheet(self.normalBackground)

	def updateGui(self):
		if self.datapool.b_status_nav:
			self.highlight_button(self.toolbar_nav_button)
			self.menuwindow.xastir_status_label.setStyleSheet(self.GREEN)
			self.menuwindow.adsb_xastir_status.setStyleSheet(self.GREEN)
		else:
			self.reset_button(self.toolbar_nav_button)
			self.menuwindow.xastir_status_label.setStyleSheet(self.RED)
			self.menuwindow.adsb_xastir_status.setStyleSheet(self.RED)

		if self.datapool.b_status_gqrx:
			self.highlight_button(self.toolbar_gqrx_button)
			self.menuwindow.gqrx_status.setStyleSheet(self.GREEN)
		else:
			self.reset_button(self.toolbar_gqrx_button)
			self.menuwindow.gqrx_status.setStyleSheet(self.RED)

		if self.datapool.b_status_key:
			self.highlight_button(self.toolbar_key_button)
		else:
			self.reset_button(self.toolbar_key_button)

		if self.datapool.b_status_speakertest:
			self.highlight_button(self.menuwindow.test_speaker_button)
		else:
			self.reset_button(self.menuwindow.test_speaker_button)

		if self.datapool.b_status_fldigi:
			self.menuwindow.fldigi_status_label.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.fldigi_status_label.setStyleSheet(self.RED)

		if self.datapool.b_status_dump1090:
			self.menuwindow.adsb_dump1090_status.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.adsb_dump1090_status.setStyleSheet(self.RED)

		if self.datapool.b_status_adsb:
			self.menuwindow.adsb_client_status.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.adsb_client_status.setStyleSheet(self.RED)

		if self.datapool.b_status_ais:
			self.menuwindow.rtl_ais_status.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.rtl_ais_status.setStyleSheet(self.RED)

		if self.datapool.b_status_acars:
			self.menuwindow.acarsdec_status.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.acarsdec_status.setStyleSheet(self.RED)

		if self.datapool.b_status_vdl2:
			self.menuwindow.vdl2_status.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.vdl2_status.setStyleSheet(self.RED)

		if self.datapool.b_status_tcpserver_RF1:
			self.menuwindow.tcprf1_status_label_2.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.tcprf1_status_label_2.setStyleSheet(self.RED)

		if self.datapool.b_status_tcpserver_RF2:
			self.menuwindow.tcprf2_status_label.setStyleSheet(self.GREEN)
		else:
			self.menuwindow.tcprf2_status_label.setStyleSheet(self.RED)

		self.menuwindow.wlan_ip_label.setText('WLAN: {IP}'.format(IP=self.datapool.s_wlan0_ip))
		self.menuwindow.lan_ip_label.setText('LAN: {IP}'.format(IP=self.datapool.s_eth0_ip))

		if self.datapool.e_RF1_status == State.CONNECTED:
			self.statusbar.rf1_status.setStyleSheet(self.GREEN)
			self.menuwindow.rf1_status.setStyleSheet(self.GREEN)
		elif self.datapool.e_RF1_status == State.DISCONNECTED:
			self.statusbar.rf1_status.setStyleSheet(self.RED)
			self.menuwindow.rf1_status.setStyleSheet(self.RED)

		if self.datapool.e_RF2_status == State.CONNECTED:
			self.statusbar.rf2_status.setStyleSheet(self.GREEN)
			self.menuwindow.rf2_status.setStyleSheet(self.GREEN)
		elif self.datapool.e_RF2_status == State.DISCONNECTED:
			self.statusbar.rf2_status.setStyleSheet(self.RED)
			self.menuwindow.rf2_status.setStyleSheet(self.RED)

		if self.datapool.b_eth0_status == State.CONNECTED:
			self.statusbar.gen_net_eth0_link.setStyleSheet(self.GREEN)
			self.menuwindow.lan_ip_label.setStyleSheet(self.GREEN)
		elif self.datapool.b_eth0_status == State.NO_LINK:
			self.statusbar.gen_net_eth0_link.setStyleSheet(self.ORANGE)
			self.menuwindow.lan_ip_label.setStyleSheet(self.ORANGE)
		elif self.datapool.b_eth0_status == State.DISCONNECTED:
			self.statusbar.gen_net_eth0_link.setStyleSheet(self.RED)
			self.menuwindow.lan_ip_label.setStyleSheet(self.RED)

		if self.datapool.b_wlan0_status == State.CONNECTED:
			self.statusbar.gen_net_wlan0_link.setStyleSheet(self.GREEN)
			self.menuwindow.wlan_ip_label.setStyleSheet(self.GREEN)
			self.menuwindow.wlan_status.setStyleSheet(self.GREEN)
		elif self.datapool.b_wlan0_status == State.NO_LINK:
			self.statusbar.gen_net_wlan0_link.setStyleSheet(self.ORANGE)
			self.menuwindow.wlan_ip_label.setStyleSheet(self.ORANGE)
			self.menuwindow.wlan_status.setStyleSheet(self.ORANGE)
		elif self.datapool.b_wlan0_status == State.DISCONNECTED:
			self.statusbar.gen_net_wlan0_link.setStyleSheet(self.RED)
			self.menuwindow.wlan_ip_label.setStyleSheet(self.RED)
			self.menuwindow.wlan_status.setStyleSheet(self.RED)

		self.menuwindow.uptime_label.setText(self.datapool.s_obc_uptime)



		#---------------TEMPERATURES----------------
		self.menuwindow.temp_dcdc.setText('DCDC = {T} °C'.format(T=round(self.datapool.f_temp_dcdc, 2)))
		self.setWarning(self.menuwindow.temp_dcdc, self.datapool.b_temp_dcdc_warn, self.datapool.b_temp_dcdc_err)

		self.menuwindow.temp_obc.setText('OBC = {T} °C'.format(T=round(self.datapool.f_temp_obc, 2)))
		self.setWarning(self.menuwindow.temp_obc, self.datapool.b_temp_obc_warn, self.datapool.b_temp_obc_err)

		self.menuwindow.temp_obc_core.setText('OBC core = {T} °C'.format(T=round(self.datapool.f_temp_obc_core, 2)))
		self.statusbar.gen_obc_temp_label.setText('{T}°C'.format(T=round(self.datapool.f_temp_obc_core, 2)))
		self.setWarning(self.menuwindow.temp_obc_core, self.datapool.b_temp_obc_core_warn, self.datapool.b_temp_obc_core_err)
		self.setWarning(self.statusbar.gen_obc_temp_label, self.datapool.b_temp_obc_core_warn, self.datapool.b_temp_obc_core_err)

		self.menuwindow.temp_batt.setText('BATT = {T} °C'.format(T=round(self.datapool.f_temp_batt, 2)))
		self.setWarning(self.menuwindow.temp_batt, self.datapool.b_temp_batt_warn, self.datapool.b_temp_batt_err)

		#-------------------POWER-------------------
		self.menuwindow.obc_power.setText('OBC = {P} W ({V} V/{I} A)'.format(P=round(self.datapool.f_power_obc, 2), V=round(self.datapool.f_voltage_obc, 2), I=round(self.datapool.f_current_obc, 2)))
		self.menuwindow.mon_power.setText('MON = {P} W ({V} V/{I} A)'.format(P=round(self.datapool.f_power_mon, 2), V=round(self.datapool.f_voltage_mon, 2), I=round(self.datapool.f_current_mon, 2)))
		self.menuwindow.tot_power.setText('TOT = {P} W'.format(P=round(self.datapool.f_power_tot, 2)))
		self.statusbar.tot_power.setText('{P} W'.format(P=round(self.datapool.f_power_tot, 2)))

		#----------------STATUS---------------------
		self.setIndicator(self.statusbar.gps_status, self.datapool.b_gps_enabled)
		self.setIndicator(self.menuwindow.gps_status, self.datapool.b_gps_enabled)
		self.setIndicator(self.menuwindow.gps_power_status, self.datapool.b_gps_enabled)
		self.setIndicator(self.menuwindow.gpsd_status_label, self.datapool.b_status_gpsd)
		self.setIndicator(self.menuwindow.opencpn_status_label, self.datapool.b_status_opencpn)

		self.setIndicator(self.statusbar.audio_status, self.datapool.b_audio_enabled)
		self.setIndicator(self.menuwindow.audio_status, self.datapool.b_audio_enabled)

		self.setIndicator(self.statusbar.imu_status, self.datapool.b_imu_enabled)
		self.setIndicator(self.menuwindow.imu_status, self.datapool.b_imu_enabled)

		self.setIndicator(self.statusbar.usb_label, self.datapool.b_usb_enabled)
		self.setIndicator(self.menuwindow.obc_usb_label, self.datapool.b_usb_enabled)


		self.menuwindow.gps_time_label.setText('UTC: {0}'.format(self.datapool.s_gps_time))
		self.menuwindow.gps_lat_label.setText('Lat: N{0} °'.format(round(self.datapool.f_gps_lat, 5)))
		self.menuwindow.gps_lon_label.setText('Lon: E{0} °'.format(round(self.datapool.f_gps_lon, 5)))
		self.menuwindow.gps_alt_label.setText('Alt: {0} m'.format(self.datapool.f_gps_alt))
		self.menuwindow.gps_sats_label.setText('Satellites: {0} '.format(self.datapool.i_gps_numsats))
		self.menuwindow.gps_mgrs_label.setText('MGRS: {0} '.format(str(self.datapool.s_gps_mgrs)))
		self.menuwindow.gps_locator_label.setText('Locator: {0} '.format(self.datapool.s_gps_locator))

		self.menuwindow.gps_path_label.setText('Device: {0}'.format(self.datapool.s_gps_path))
		self.menuwindow.gps_speed_label.setText('Speed: {0} Bd'.format(self.datapool.s_gps_speed))
		self.menuwindow.gps_driver_label.setText('Device: {0}'.format(self.datapool.s_gps_driver))


		if self.datapool.i_gps_mode == 3:
			self.menuwindow.gps_mode_label.setText('3D FIX')
			self.menuwindow.gps_mode_label.setStyleSheet("background-color: rgb(0, 255, 0);")
		elif self.datapool.i_gps_mode == 2:
			self.menuwindow.gps_mode_label.setText('2D FIX')
			self.menuwindow.gps_mode_label.setStyleSheet("background-color: rgb(255, 128, 0);")
		else:
			self.menuwindow.gps_mode_label.setText('NO FIX')
			self.menuwindow.gps_mode_label.setStyleSheet("background-color: rgb(255, 0, 0);")



	def setIndicator(self, widget, bool):
		if self.nightModeEnabled:
			if bool:
				widget.setStyleSheet(self.blackTextRedBackground)
			else:
				widget.setStyleSheet(self.buttonStyleIdleNight)
		else:
			if bool:
				widget.setStyleSheet(self.GREEN)
			else:
				widget.setStyleSheet(self.RED)

	def enableNightMode(self):
		self.nightModeEnabled = True
		self.setStyleSheet(self.nightModeBackground)
		self.volup_button.setStyleSheet(self.buttonStyleIdleNight)
		self.voldown_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_backlight_up_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_backlight_down_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_nav_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_gqrx_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_screen_onoff_button.setStyleSheet(self.buttonStyleIdleNight)
		self.mute_button.setStyleSheet(self.buttonStyleIdleNight)
		self.toolbar_key_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menu_button.setStyleSheet(self.buttonStyleIdleNight)
		self.screenshot_button.setStyleSheet(self.buttonStyleIdleNight)

		self.menuwindow.setStyleSheet(self.nightModeBackground)
		self.menuwindow.stackedWidget.setStyleSheet('border:0px solid black; ' + self.nightModeBackground)
		self.menuwindow.obc_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.nav_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.env_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.data_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.apps_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.mon_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.nightmode_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.time_button_2.setStyleSheet(self.buttonStyleIdleNight)

		self.menuwindow.enable_gps_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.disable_gps_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.enable_imu_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.disable_imu_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.enable_audio_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.disable_audio_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.enable_usb_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.disable_usb_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.enable_wlan_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.disable_wlan_button.setStyleSheet(self.buttonStyleIdleNight)
		self.menuwindow.test_speaker_button.setStyleSheet(self.buttonStyleIdleNight)

		self.menuwindow.exit_button.setStyleSheet(self.buttonStyleIdleNight)


		self.menuwindow.obc_thermal_groupbox.setStyleSheet(self.boxStyleNight)
		self.menuwindow.obc_power_groupbox.setStyleSheet(self.boxStyleNight)
		self.menuwindow.obc_comms_groupbox.setStyleSheet(self.boxStyleNight)

		self.menuwindow.uptime_label.setStyleSheet(self.boxStyleNight)

		self.barmenu.setStyleSheet(self.nightModeBackground)

		self.statusbar.setStyleSheet(self.nightModeBackground)
		self.statusbar.main_time_label.setStyleSheet('color: rgb(255, 0, 0);')
		self.statusbar.gen_obc_temp_label.setStyleSheet('color: rgb(255, 0, 0);')
		self.statusbar.vol_label.setStyleSheet('color: rgb(255, 0, 0);')
		self.statusbar.bl_label.setStyleSheet('color: rgb(255, 0, 0);')
		self.statusbar.tot_power.setStyleSheet('color: rgb(255, 0, 0);')
		self.statusbar.total_power_label_2.setStyleSheet('color: rgb(255, 0, 0);')

		self.messagewindow.setStyleSheet(self.boxStyleNight)
		self.messagewindow.cancel_button.setStyleSheet(self.buttonStyleIdleNight)
		self.messagewindow.ok_button.setStyleSheet(self.buttonStyleIdleNight)

	def disableNightMode(self):
		self.nightModeEnabled = False
		self.setStyleSheet(self.normalBackground)
		self.volup_button.setStyleSheet(self.buttonStyleIdle)
		self.voldown_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_backlight_up_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_backlight_down_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_nav_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_gqrx_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_screen_onoff_button.setStyleSheet(self.buttonStyleIdle)
		self.mute_button.setStyleSheet(self.buttonStyleIdle)
		self.toolbar_key_button.setStyleSheet(self.buttonStyleIdle)
		self.menu_button.setStyleSheet(self.buttonStyleIdle)
		self.screenshot_button.setStyleSheet(self.buttonStyleIdle)

		self.menuwindow.setStyleSheet(self.normalBackground)
		self.menuwindow.stackedWidget.setStyleSheet('border:0px solid black; ' + self.normalBackground)
		self.menuwindow.obc_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.nav_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.env_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.data_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.apps_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.mon_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.nightmode_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.time_button_2.setStyleSheet(self.buttonStyleIdle)

		self.menuwindow.enable_gps_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.disable_gps_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.enable_imu_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.disable_imu_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.enable_audio_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.disable_audio_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.enable_usb_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.disable_usb_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.enable_wlan_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.disable_wlan_button.setStyleSheet(self.buttonStyleIdle)
		self.menuwindow.test_speaker_button.setStyleSheet(self.buttonStyleIdle)

		self.menuwindow.exit_button.setStyleSheet(self.buttonStyleIdle)

		self.menuwindow.obc_thermal_groupbox.setStyleSheet(self.boxStyleNormal)
		self.menuwindow.obc_power_groupbox.setStyleSheet(self.boxStyleNormal)
		self.menuwindow.obc_comms_groupbox.setStyleSheet(self.boxStyleNormal)

		self.menuwindow.uptime_label.setStyleSheet(self.boxStyleNormal)

		self.barmenu.setStyleSheet(self.normalBackground)

		self.statusbar.setStyleSheet(self.normalBackground)
		self.statusbar.main_time_label.setStyleSheet('')
		self.statusbar.gen_obc_temp_label.setStyleSheet('')
		self.statusbar.vol_label.setStyleSheet('')
		self.statusbar.bl_label.setStyleSheet('')
		self.statusbar.tot_power.setStyleSheet('')
		self.statusbar.total_power_label_2.setStyleSheet('')

		self.messagewindow.setStyleSheet(self.normalBackground)
		self.messagewindow.cancel_button.setStyleSheet(self.buttonStyleIdle)
		self.messagewindow.ok_button.setStyleSheet(self.buttonStyleIdle)

	def toggleNightMode(self):
		if not self.nightModeEnabled:
			self.enableNightMode()
		else:
			self.disableNightMode()

	def startADSB(self):
		config = self.menuwindow.adsb_combo.currentText()
		self.platform.startADSB(config)

	def stopADSB(self):
		self.platform.stopADSB()

	def startAcars(self):
		config = self.menuwindow.acars_combo.currentText()
		self.platform.startAcars(config)

	def stopAcars(self):
		self.platform.stopAcars()

	def startVdl2(self):
		config = self.menuwindow.vdl2_combo.currentText()
		self.platform.startVdl2(config)

	def stopVdl2(self):
		self.platform.stopVdl2()

	def startAIS(self):
		config = self.menuwindow.ais_combo.currentText()
		self.platform.startAIS(config)

	def stopAIS(self):
		self.platform.stopAIS()

	def startGQRX(self):
		config = self.menuwindow.gqrx_dev_combo.currentText()
		mode = self.menuwindow.gqrx_mode_combo.currentText()
		self.platform.startGQRX(config, mode)

	def stopGQRX(self):
		self.platform.stopGQRX()

	def takeScreenshot(self):
		self.platform.takeScreenshot()
		self.messagewindow.popup()

	def reboot(self):
		self.platform.stopApplications()
		self.statusbar.close()
		self.menuwindow.close()
		self.barmenu.close()
		self.platform.reboot()

	def incrementVolume(self):
		vol, muted = self.platform.incrementVolume()
		self.statusbar.vol_label.setText('Vol: ' + str(vol) + '%')
		self.barmenu.popup()
		self.barmenu.volume_bar.setValue(int(vol))

	def decrementVolume(self):
		vol, muted = self.platform.decrementVolume()
		self.statusbar.vol_label.setText('Vol: ' + str(vol) + '%')
		self.barmenu.popup()
		self.barmenu.volume_bar.setValue(int(vol))

	def incrementBacklight(self):
		bl = self.platform.incrementBacklight()
		self.statusbar.bl_label.setText('BL: ' + str(bl) + '%')
		self.barmenu.popup()
		self.barmenu.backlight_bar.setValue(bl)

	def decrementBacklight(self):
		bl = self.platform.decrementBacklight()
		self.statusbar.bl_label.setText('BL: ' + str(bl) + '%')
		self.barmenu.popup()
		self.barmenu.backlight_bar.setValue(bl)

	def exitApplication(self):
		self.platform.stopApplications()
		self.statusbar.close()
		self.menuwindow.close()
		self.barmenu.close()
		self.close()

	def shutdown(self):
		self.platform.stopApplications()
		self.statusbar.close()
		self.menuwindow.close()
		self.platform.shutdown()

	def tickTock(self):
		self.statusbar.main_time_label.setText(datetime.datetime.utcnow().strftime("%H:%M:%S UTC %b %d-%m-%Y"))

	def updateTemperature(self, temp):
		self.statusbar.gen_obc_temp_label.setText('{TEMP} °C'.format(TEMP=temp))
		if temp < 54.0:
			self.statusbar.gen_obc_temp_label.setStyleSheet('')
		elif temp >= 54.0 and temp <= 65:
			self.statusbar.gen_obc_temp_label.setStyleSheet('background-color: rgb(255, 255, 0);')
		elif temp > 65:
			self.statusbar.gen_obc_temp_label.setStyleSheet('background-color: rgb(255, 0, 0);')

		self.barmenu.hide()

	def keyPressEvent(self, event):
		print(event.key())

	def	highlight_button(self, button):
		if self.nightModeEnabled:
			button.setStyleSheet(self.buttonStyleClickedNight)
		else:
			button.setStyleSheet(self.buttonStyleClicked)

	def reset_button(self, button):
		if self.nightModeEnabled:
			button.setStyleSheet(self.buttonStyleIdleNight)
		else:
			button.setStyleSheet(self.buttonStyleIdle)


class AlarmIndicator(QThread):

	alarm_active = False
	alarmHighSignal = pyqtSignal(bool)

	def __init__(self, parent=None):
		QThread.__init__(self)

		self.logger = logging.getLogger('main_logger')
		self.logger.info('[ALARM] __init__() called')
		GPIO.output(ALARM_LED_PIN, False)

	def enable(self):
		self.alarm_active = True
		self.logger.info('[ALARM] enable() called')

	def disable(self):
		self.alarm_active = False
		if GPIO.input(ALARM_LED_PIN):
			GPIO.output(ALARM_LED_PIN, False)
			self.alarmHighSignal.emit(False)
		self.logger.info('[ALARM] disable() called')

	def run(self):
		while True:
			time.sleep(0.5)
			if self.alarm_active:
				GPIO.output(ALARM_LED_PIN, True)
				self.alarmHighSignal.emit(True)
			time.sleep(0.5)
			if self.alarm_active:
				GPIO.output(ALARM_LED_PIN, False)
				self.alarmHighSignal.emit(False)


class KernelPoller(QThread):

	dmesg_output = pyqtSignal(str)

	def __init__(self, parent=None):
		QThread.__init__(self)
		self.proc = subprocess.Popen(['dmesg', '-w'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	def run(self):
		while True:
			out = self.proc.stdout.read(1).decode('utf-8')
			if out == '' and self.proc.poll() != None:
				time.sleep(0.1)
			if out != '':
				sys.stdout.write(out)
				self.dmesg_output.emit(out)
				sys.stdout.flush()

class TempPowerPoller(Thread):

	def __init__(self, parent=None):
		Thread.__init__(self)
		self.logger = logging.getLogger('main_logger')
		self.logger.info('[TEMP/PWR] __init__() called')
		self.parent = parent

		if INA219_CH0_ENABLE:
			self.ina219_ch0 = INA219(I2C_BUS, addr=int(INA219_ADDR_CH0, 16))
			self.ina219_ch0.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
			self.ina219_ch0.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
			self.ina219_ch0.bus_voltage_range = BusVoltageRange.RANGE_16V
			self.logger.info('[TEMP/PWR] enable_ina219_ch0=True, INA219 on I2C addr {ADDR}, ADCRES_12BIT_32S, RANGE_16V'.format(ADDR=INA219_ADDR_CH0))

		if INA219_CH1_ENABLE:
			self.ina219_ch1 = INA219(I2C_BUS, addr=int(INA219_ADDR_CH1, 16))
			self.ina219_ch1.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
			self.ina219_ch1.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
			self.ina219_ch1.bus_voltage_range = BusVoltageRange.RANGE_16V
			self.logger.info('[TEMP/PWR] enable_ina219_ch1=True, INA219 on I2C addr {ADDR} ADCRES_12BIT_32S, RANGE_16V'.format(ADDR=INA219_ADDR_CH1))

	def pollTemperatures(self):
		if ENABLE_ONEWIRE:
			try:
				output = subprocess.check_output(['cat', '/sys/bus/w1/devices/{TEMP_ID}/w1_slave'.format(TEMP_ID=DCDC_TEMP_ID)])
				self.parent.datapool.f_temp_dcdc = int(re.findall(r"(?<!\d)\d{5}(?!\d)", output.decode('utf-8'))[0])/1000.0
				if self.parent.datapool.f_temp_dcdc > T_HIGH_DCDC_ERR:
					self.parent.datapool.b_temp_dcdc_err = True
					self.parent.datapool.b_temp_dcdc_warn = False
				elif self.parent.datapool.f_temp_dcdc > T_HIGH_DCDC_WARN:
					self.parent.datapool.b_temp_dcdc_err = False
					self.parent.datapool.b_temp_dcdc_warn = True
				else:
					self.parent.datapool.b_temp_dcdc_err = False
					self.parent.datapool.b_temp_dcdc_warn = False
			except Exception as e:
				self.parent.datapool.f_temp_dcdc = 1000.0
				self.parent.datapool.b_temp_dcdc_err = True
			try:
				output = subprocess.check_output(['cat', '/sys/bus/w1/devices/{TEMP_ID}/w1_slave'.format(TEMP_ID=OBC_TEMP_ID)])
				self.parent.datapool.f_temp_obc = int(re.findall(r"(?<!\d)\d{5}(?!\d)", output.decode('utf-8'))[0])/1000.0
				if self.parent.datapool.f_temp_obc > T_HIGH_OBC_ERR:
					self.parent.datapool.b_temp_obc_err = True
					self.parent.datapool.b_temp_obc_warn = False
				elif self.parent.datapool.f_temp_obc > T_HIGH_OBC_WARN:
					self.parent.datapool.b_temp_obc_err = False
					self.parent.datapool.b_temp_obc_warn = True
				else:
					self.parent.datapool.b_temp_obc_err = False
					self.parent.datapool.b_temp_obc_warn = False
			except Exception as e:
				self.parent.datapool.f_temp_obc = 0.0
				self.parent.datapool.b_temp_obc_err = True

			try:
				output = subprocess.check_output(['cat', '/sys/bus/w1/devices/{TEMP_ID}/w1_slave'.format(TEMP_ID=BATT_TEMP_ID)])
				self.parent.datapool.f_temp_batt = int(re.findall(r"(?<!\d)\d{5}(?!\d)", output.decode('utf-8'))[0])/1000.0
				if self.parent.datapool.f_temp_batt > T_HIGH_BATT_ERR:
					self.parent.datapool.b_temp_batt_err = True
					self.parent.datapool.b_temp_batt_warn = False
				elif self.parent.datapool.f_temp_batt > T_HIGH_BATT_WARN:
					self.parent.datapool.b_temp_batt_err = False
					self.parent.datapool.b_temp_batt_warn = True
				else:
					self.parent.datapool.b_temp_batt_err = False
					self.parent.datapool.b_temp_batt_warn = False
			except Exception as e:
				self.parent.datapool.f_temp_batt = 0.0
				self.parent.datapool.b_temp_batt_err = True

		output = subprocess.check_output(['vcgencmd', 'measure_temp'])
		floats = re.findall("\d+\.\d+", output.decode('utf-8'))
		f_temp_obc_core = float(floats[0])
		self.parent.datapool.f_temp_obc_core = f_temp_obc_core
		if self.parent.datapool.f_temp_obc_core > T_HIGH_OBC_CORE_ERR:
			self.parent.datapool.b_temp_obc_core_err = True
			self.parent.datapool.b_temp_obc_core_warn = False
		elif self.parent.datapool.f_temp_obc_core > T_HIGH_OBC_CORE_WARN:
			self.parent.datapool.b_temp_obc_core_err = False
			self.parent.datapool.b_temp_obc_core_warn = True
		else:
			self.parent.datapool.b_temp_obc_core_err = False
			self.parent.datapool.b_temp_obc_core_warn = False


		if 	self.parent.datapool.b_temp_dcdc_err or self.parent.datapool.b_temp_dcdc_warn or \
			self.parent.datapool.b_temp_obc_err or self.parent.datapool.b_temp_obc_warn or \
			self.parent.datapool.b_temp_batt_err or self.parent.datapool.b_temp_batt_warn or \
			self.parent.datapool.b_temp_obc_core_err or self.parent.datapool.b_temp_obc_core_warn:
			self.parent.alarm.enable()
		else:
			self.parent.alarm.disable()

	def pollPower(self):
		if INA219_CH0_ENABLE:
			self.parent.datapool.f_voltage_obc = self.ina219_ch0.bus_voltage  # voltage on V- (load side)
			self.parent.datapool.f_current_obc = self.ina219_ch0.current/1000.0 # current in mA
			self.parent.datapool.f_power_obc = self.parent.datapool.f_voltage_obc * self.parent.datapool.f_current_obc
			self.logger.info('[TEMP/PWR] pollPower() called CH0: {POWER}W ({VOLT}V/{AMPS}A)'.format(POWER=round(self.parent.datapool.f_power_obc, 2), VOLT=round(self.parent.datapool.f_voltage_obc, 2), AMPS=round(self.parent.datapool.f_current_obc, 2)))

		if INA219_CH1_ENABLE:
			self.parent.datapool.f_voltage_mon = self.ina219_ch1.bus_voltage  # voltage on V- (load side)
			self.parent.datapool.f_current_mon = self.ina219_ch1.current/1000.0 # current in mA
			self.parent.datapool.f_power_mon = self.parent.datapool.f_voltage_mon * self.parent.datapool.f_current_mon
			self.logger.info('[TEMP/PWR] pollPower() called CH1: {POWER}W ({VOLT}V/{AMPS}A)'.format(POWER=round(self.parent.datapool.f_power_mon, 2), VOLT=round(self.parent.datapool.f_voltage_mon, 2), AMPS=round(self.parent.datapool.f_current_mon, 2)))

		self.parent.datapool.f_power_tot = self.parent.datapool.f_power_mon + self.parent.datapool.f_power_obc

	def run(self):
		while True:
			self.pollTemperatures()
			self.pollPower()
			time.sleep(2)


class Poller(QThread):

	memory_signal = pyqtSignal(object)
	ifconfig_signal = pyqtSignal(object)

	def __init__(self, parent=None):
		QThread.__init__(self)
		self.logger = logging.getLogger('main_logger')
		self.logger.info('[POLLER] __init__() called')
		self.parent = parent

	def pollGPS(self):
		self.parent.datapool.b_gps_enabled = GPIO.input(GPS_PWR_PIN)

	def pollIMU(self):
		self.parent.datapool.b_imu_enabled = GPIO.input(IMU_PWR_PIN)

	def pollNetwork(self):
		output = subprocess.check_output(['ifconfig'])
		if 'eth0' in output.decode('utf-8'):
			if 'eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>' in output.decode('utf-8'):
				self.parent.datapool.b_eth0_status = State.CONNECTED
				ps = subprocess.Popen(('ip', 'address', 'show', 'eth0'), stdout=subprocess.PIPE)
				proc_output = subprocess.check_output(('grep', 'inet'), stdin=ps.stdout).decode('utf-8').split('\n')[0]
				try:
					result = re.search('inet (.*)/', proc_output).group(1)
					self.parent.datapool.s_eth0_ip = result
				except Exception as e:
					pass
			else:
				self.parent.datapool.b_eth0_status = State.NO_LINK
		else:
			self.parent.datapool.b_eth0_status = State.DISCONNECTED

		if 'wlan0' in output.decode('utf-8'):
			if 'wlan0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>' in output.decode('utf-8'):
				self.parent.datapool.b_wlan0_status = State.CONNECTED
				ps = subprocess.Popen(('ip', 'address', 'show', 'wlan0'), stdout=subprocess.PIPE)
				proc_output = subprocess.check_output(('grep', 'inet'), stdin=ps.stdout).decode('utf-8').split('\n')[0]
				try:
					result = re.search('inet (.*)/', proc_output).group(1)
					self.parent.datapool.s_wlan0_ip = result
				except Exception as e:
					self.parent.datapool.s_wlan0_ip = ''
			else:
				self.parent.datapool.b_wlan0_status = State.NO_LINK
				self.parent.datapool.s_wlan0_ip = ''
		else:
			self.parent.datapool.b_wlan0_status = State.DISCONNECTED
			self.parent.datapool.s_wlan0_ip = ''

	def pollMemory(self):
		output = subprocess.check_output(['cat', '/proc/meminfo'])
		lines = output.decode('utf-8').split('\n')
		self.memory_signal.emit(lines)

	def pollProcesses(self):
		ps = subprocess.Popen(('ps', '-e'), stdout=subprocess.PIPE)
		output = subprocess.check_output((	'grep', '-e', 'systemd', '-e', 'xastir', '-e', 'gqrx', '-e', 'dump1090', '-e', 'ads-b.pl', \
													'-e', 'match', '-e', 'rtl_ais', '-e', 'acarsdec', '-e', 'dumpvdl2', '-e', 'speaker-test', \
													'-e', 'gpsd', '-e', 'opencpn', '-e', 'fldigi'), stdin=ps.stdout).decode('utf-8').split('\n')

		if 'xastir' in ''.join(output):
			self.parent.datapool.b_status_nav = True
		else:
			self.parent.datapool.b_status_nav = False

		if 'gqrx' in ''.join(output):
			self.parent.datapool.b_status_gqrx = True
		else:
			self.parent.datapool.b_status_gqrx = False

		if 'dump1090' in ''.join(output):
			self.parent.datapool.b_status_dump1090 = True
		else:
			self.parent.datapool.b_status_dump1090 = False

		if 'ads-b.pl' in ''.join(output):
			self.parent.datapool.b_status_adsb = True
		else:
			self.parent.datapool.b_status_adsb = False

		if 'match' in ''.join(output):
			self.parent.datapool.b_status_key = True
		else:
			self.parent.datapool.b_status_key = False

		if 'rtl_ais' in ''.join(output):
			self.parent.datapool.b_status_ais = True
		else:
			self.parent.datapool.b_status_ais = False

		if 'acarsdec' in ''.join(output):
			self.parent.datapool.b_status_acars = True
		else:
			self.parent.datapool.b_status_acars = False

		if 'dumpvdl2' in ''.join(output):
			self.parent.datapool.b_status_vdl2 = True
		else:
			self.parent.datapool.b_status_vdl2 = False

		if 'speaker-test' in ''.join(output):
			self.parent.datapool.b_status_speakertest = True
		else:
			self.parent.datapool.b_status_speakertest = False

		if 'gpsd' in ''.join(output):
			self.parent.datapool.b_status_gpsd = True
		else:
			self.parent.datapool.b_status_gpsd = False

		if 'opencpn' in ''.join(output):
			self.parent.datapool.b_status_opencpn = True
		else:
			self.parent.datapool.b_status_opencpn = False

		if 'fldigi' in ''.join(output):
			self.parent.datapool.b_status_fldigi = True
		else:
			self.parent.datapool.b_status_fldigi = False

	def pollRF(self):
		try:
			ps = subprocess.Popen(('rtl_udp', '-d', '10', '-f', '104000000'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			output = subprocess.check_output(('grep', 'RF1'), stdin=ps.stdout).decode('utf-8').split('\n')
			output = ''.join(output)
			if 'RF1' in output:
				self.parent.datapool.e_RF1_status = State.CONNECTED
				self.parent.datapool.i_RF1_index = int(output.split(':')[0])
			else:
				self.parent.datapool.e_RF1_status = State.DISCONNECTED
		except Exception as e:
			self.parent.datapool.e_RF1_status = State.DISCONNECTED

		try:
			ps = subprocess.Popen(('rtl_udp', '-d', '10', '-f', '104000000'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			output = subprocess.check_output(('grep', 'RF2'), stdin=ps.stdout).decode('utf-8').split('\n')
			output = ''.join(output)
			if 'RF2' in output:
				self.parent.datapool.e_RF2_status = State.CONNECTED
				self.parent.datapool.i_RF2_index = int(output.split(':')[0])
			else:
				self.parent.datapool.e_RF2_status = State.DISCONNECTED
		except Exception as e:
			self.parent.datapool.e_RF2_status = State.DISCONNECTED

	def pollTCPservers(self):
		ps = subprocess.Popen(('ps', 'aux'), stdout=subprocess.PIPE)

		try:
			output = subprocess.check_output(('grep', 'rtl_tcp'), stdin=ps.stdout).decode('utf-8').split('\n')

			match_string_RF1 = "rtl_tcp -d {INDEX} -P {PPM}".format(INDEX=self.parent.datapool.i_RF1_index , PPM=RF1_PPM, PORT=RF1_TCP_PORT)
			match_string_RF2 = "rtl_tcp -d {INDEX} -P {PPM}".format(INDEX=self.parent.datapool.i_RF2_index , PPM=RF2_PPM, PORT=RF2_TCP_PORT)

			if match_string_RF1 in ''.join(output):
				self.parent.datapool.b_status_tcpserver_RF1 = True
			else:
				self.parent.datapool.b_status_tcpserver_RF1 = False


			if match_string_RF2 in ''.join(output):
				self.parent.datapool.b_status_tcpserver_RF2 = True
			else:
				self.parent.datapool.b_status_tcpserver_RF2 = False

		except Exception as e:
			self.parent.datapool.b_status_tcpserver_RF1 = False
			self.parent.datapool.b_status_tcpserver_RF2 = False

	def pollUptime(self):
		output = subprocess.check_output(['uptime']).decode('utf-8')
		self.parent.datapool.s_obc_uptime = output


	def run(self):
		while True:
			self.pollNetwork()
			self.pollProcesses()
			self.pollRF()
			self.pollGPS()
			self.pollIMU()
			self.pollTCPservers()
			self.pollUptime()
			time.sleep(2)


class GPS(Thread):

	telemetry = None
	connected = False

	debug = True
	packet = None

	gpsd = None

	def __init__(self, parent, gpsd_ip, gpsd_port):
		Thread.__init__(self)
		self.logger = logging.getLogger('main_logger')
		self.logger.info('Initiated GPS thread')
		self.parent = parent

		self.m = mgrs.MGRS()

		gpsd.connect()
		self.connected = True
		self.logger.info('Connected to GPSD server at {HOST}:{PORT}'.format(HOST=gpsd_ip, PORT=gpsd_port))
		time.sleep(3)
		self.packet = gpsd.get_current()
		devinfo = gpsd.device()
		self.parent.parent.datapool.s_gps_path = devinfo['path']
		self.parent.parent.datapool.s_gps_speed = devinfo['speed']
		self.parent.parent.datapool.s_gps_driver = devinfo['driver']

	def run(self):
		while self.connected:
			try:
				self.packet = gpsd.get_current() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
				self.parent.parent.datapool.s_gps_time = str(self.packet.time)
				self.parent.parent.datapool.f_gps_alt = self.packet.alt
				self.parent.parent.datapool.f_gps_lat = self.packet.lat
				self.parent.parent.datapool.f_gps_lon = self.packet.lon
				self.parent.parent.datapool.s_gps_mgrs = self.m.toMGRS(self.packet.lat, self.packet.lon).decode('utf-8')
				self.parent.parent.datapool.i_gps_mode = self.packet.mode
				self.parent.parent.datapool.l_gps_sats = self.packet.sats_valid
				self.parent.parent.datapool.i_gps_numsats = self.packet.sats_valid
				self.parent.parent.datapool.s_gps_locator = to_grid(self.packet.lat, self.packet.lon)

				if self.packet.mode == 2 or self.packet.mode == 3:
					gpsLogger.info(',{UTC},{MODE},{LAT},{LON},{ALT},{MGRS},{LOC},{SATS}'.format(	UTC=str(self.packet.time), \
																									MODE=self.packet.mode, \
																									LAT=self.packet.lat, \
																									LON=self.packet.lon, \
																									ALT=self.packet.alt, \
																									MGRS=self.m.toMGRS(self.packet.lat, self.packet.lon).decode('utf-8'), \
																									LOC=to_grid(self.packet.lat, self.packet.lon), \
																									SATS=self.packet.sats_valid))


				time.sleep(1)
			except Exception as e:
				self.logger.error(e)
				time.sleep(1)



def setup_logger(name, log_file, level=logging.INFO):
	formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
	logging.Formatter.converter = time.gmtime
	fileHandler = logging.FileHandler(log_file)
	streamHandler = logging.StreamHandler()

	fileHandler.setFormatter(formatter)
	streamHandler.setFormatter(formatter)

	logger = logging.getLogger(name)
	logger.setLevel(level)
	logger.addHandler(fileHandler)
	logger.addHandler(streamHandler)

	return logger



if __name__ == '__main__':

	path = os.path.dirname(os.path.abspath(__file__))
	now = datetime.datetime.utcnow()

	mainLogger = setup_logger('main_logger', '{PATH}/main_{DATE}.log'.format(PATH=MAIN_LOG_PATH, DATE=now.strftime("%Y%m%d_%H%M%S")), level=logging.INFO)
	gpsLogger = setup_logger('gps_logger', '{PATH}/gps_{DATE}.log'.format(PATH=GPS_LOG_PATH, DATE=now.strftime("%Y%m%d_%H%M%S")), level=logging.INFO)

	a = QApplication(sys.argv)
	app = Main()
	app.show()
	a.exec_()
	os._exit(0)
