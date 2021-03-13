#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import os
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
import logging
import subprocess
import gpsd
import mgrs
import re
import zmq
from enum import Enum
import json
import argparse
from cyberdeck import RemoteCyberdeck
import copy

buttonStyleIdle = 		"border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\";"
buttonStyleClicked = 	"border: 1px solid black; border-radius: 25px; background-color: rgb(0, 255, 0); font: 9pt \"Noto Sans\";"
buttonStyleClickedRed = "border: 1px solid black; border-radius: 25px; background-color: rgb(255, 0, 0); font: 9pt \"Noto Sans\";"

boxStyleNight = 		"background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
boxStyleNormal = 		""

buttonStyleIdleNight = 		"border: 1px solid red; border-radius: 25px; background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
buttonStyleClickedNight = 	"border: 1px solid red; border-radius: 25px; background-color: rgb(255, 0, 0); color: rgb(0, 0, 0);"

nightModeBackground = 	"background-color: rgb(0, 0, 0);"
normalBackground = 		'background-color: rgb(186, 186, 186);'

GREEN = 				'background-color: rgb(0, 255, 0); font: 9pt \"Noto Sans\";'
RED = 					'background-color: rgb(255, 0, 0); font: 9pt \"Noto Sans\";'
ORANGE =				'background-color: rgb(255, 165, 0); font: 9pt \"Noto Sans\";'

def is_time_between(begin_time, end_time, check_time=None):
	# If check time is not given, default to current UTC time
	check_time = check_time or datetime.datetime.utcnow().time()
	if begin_time < end_time:
		return check_time >= begin_time and check_time <= end_time
	else: # crosses midnight
		return check_time >= begin_time or check_time <= end_time

class DeviceWidget(QWidget):
	def __init__(self, parent, device):
		super(DeviceWidget, self).__init__()

		self.parent = parent

		self.device = device

		self.groupbox = QtWidgets.QGroupBox(self.device["config"]["s_id"])
		self.groupbox.setStyleSheet("font: 9pt \"Noto Sans\";")
		self.groupbox.setAlignment(Qt.AlignHCenter)
		self.vbox = QtWidgets.QVBoxLayout()
		#self.vbox.sizeConstraint = QtWidgets.QLayout.SetFixedSize
		if self.device["config"]["s_id"] == "gps":
			self.device.get("status", {}).pop('mode_enum', None)
			self.device.get("status", {}).pop('track', None)
			self.device.get("status", {}).pop('hspeed', None)
			self.device.get("status", {}).pop('climb', None)
			self.device.get("status", {}).pop('sats_visible', None)
			self.device.get("status", {}).pop('mgrs', None)
			self.device.get("status", {}).pop('alt', None)
			self.device.get("status", {}).pop('sats_used', None)
			self.device.get("status", {}).pop('time_utc', None)
			for key in list(self.device["status"]):
				if "error" in key:
					self.device.get("status", {}).pop(key, None)





		blanking_label = QtWidgets.QLabel("")
		blanking_label.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
		self.vbox.addWidget(blanking_label)

		for key in self.device["status"]:
			label_name = "{}_{}_statuslabel".format(self.device["config"]["s_id"], key)
			setattr(self, label_name, QtWidgets.QLabel(key))
			if "power" in key:
				label = getattr(self, label_name)
				label.setStyleSheet('background-color: rgb(0, 255, 0);')
				label.setAlignment(QtCore.Qt.AlignCenter)

			self.vbox.addWidget(getattr(self, label_name))



		if self.device["config"]["b_allow_powerstate"]:

			self.buttonsWidget = QtWidgets.QWidget()
			self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)


			configButton = "{}_config_button".format(self.device["id"])
			setattr(self, configButton, QtWidgets.QToolButton())
			self.configbutton = getattr(self, configButton)
			self.configbutton.setText("Config")
			self.configbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 10pt \"Noto Sans\"; min-height: 25 px")
			self.configbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

			powerButton = "{}_powerbutton_button".format(self.device["id"])
			setattr(self, powerButton, QtWidgets.QToolButton())
			self.powerbutton = getattr(self, powerButton)
			self.powerbutton.setText("START")
			self.powerbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 10pt \"Noto Sans\"; min-height: 25 px")
			self.powerbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

			self.buttonsWidgetLayout.addWidget(self.configbutton)
			self.buttonsWidgetLayout.addWidget(self.powerbutton)

			self.vbox.addStretch(50)
			self.groupbox.setLayout(self.vbox)
			self.vbox2 = QtWidgets.QVBoxLayout()
			self.vbox2.addWidget(self.groupbox)
			self.vbox2.addWidget(self.buttonsWidget)
			self.setLayout(self.vbox2)

			self.powerbutton.pressed.connect(self.powerOnOffDevice)
			self.configbutton.pressed.connect(lambda: self.parent.configwindow.setConfig(self.device["config"]))

		else:

			self.buttonsWidget = QtWidgets.QWidget()
			self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)

			configButton = "{}_config_button".format(self.device["id"])
			setattr(self, configButton, QtWidgets.QToolButton())
			self.configbutton = getattr(self, configButton)
			self.configbutton.setText("Config")
			self.configbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 10pt \"Noto Sans\"; min-height: 25 px")
			self.configbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

			self.buttonsWidgetLayout.addWidget(self.configbutton)


			self.vbox.addStretch(20)
			self.groupbox.setLayout(self.vbox)
			self.vbox2 = QtWidgets.QVBoxLayout()
			self.vbox2.addWidget(self.groupbox)
			self.vbox2.addWidget(self.buttonsWidget)
			self.setLayout(self.vbox2)

			self.configbutton.pressed.connect(lambda: self.parent.configwindow.setConfig(self.device["config"]))

	def updateView(self, device):

		self.device = device

		id = self.device["id"]
		status = self.device["status"]
		config = self.device["config"]

		#label = widget.findChild(QtWidgets.QLabel, "{}_{}_statuslabel".format(system, key))
		for key in status:
			try:
				value = status[key]
				label = getattr(self, "{}_{}_statuslabel".format(id, key))
				if "voltage" in key:
					label.setText("U={} V <font color=\"green\">OK</font>".format(round(value, 3)))
				elif "current" in key:
					label.setText("I={} A".format(round(value, 2)))
				elif "consumption" in key:
					label.setText("P={} W".format(round(value, 2)))
				elif "volume" in key or "brightness" in key or "level" in key:
					label.setText("{}={}%".format(key, round(value, 2)))
				elif "temp" in key:
					label.setText("{}={}°C".format(key, round(value, 1)))
				elif "power" in key:
					if value:
						label.setStyleSheet(GREEN)
						if key == "rf1_power" or key == "rf2_power":
							label.setText("{} ON".format(key.split("_")[0].upper()))
						elif key == "j1a_power" or key == "j1b_power":
							label.setText("{} ON {}".format(key.split("_")[0].upper(), "(5V)" if key == "j1a_power" else "(9-36V)"))
						else:
							label.setText("ON")

						if self.device["config"]["b_allow_powerstate"]:
							self.powerbutton.setText("OFF")
					else:
						label.setStyleSheet(RED)
						if key == "rf1_power" or key == "rf2_power":
							label.setText("{} OFF".format(key.split("_")[0].upper()))
						elif key == "j1a_power" or key == "j1b_power":
							label.setText("{} OFF {}".format(key.split("_")[0].upper(), "(5V)" if key == "j1a_power" else "(9-36V)"))
						else:
							label.setText("OFF")

						if self.device["config"]["b_allow_powerstate"]:
							self.powerbutton.setText("ON")

				elif "lat" in key or "lon" in key:
					label.setText("{}={}°".format(key, round(value, 6)))
				elif "time" in key:
					label.setText("{}".format(value))
				elif "charge_state" in key:
					if value == "CHARGING" or value == "DONE CHARGING":
						label.setStyleSheet(GREEN)
					elif value == "DISCHARGING":
						label.setStyleSheet(RED)
					elif value == "IDLE":
						label.setStyleSheet("")
					else:
						label.setStyleSheet("")

					label.setText(value)

				elif key == "t_left":
					label.setText("{}={} hrs".format(key, round(value, 1)))

				elif key == "eth0" or key == "wlan0" or key == "wlan1":
					if not value == "NO LINK" and not value == "NOT AVLBL":
						label.setStyleSheet(GREEN)
					else:
						label.setStyleSheet("")
					

					label.setText("{}".format(value))
					label.setAlignment(QtCore.Qt.AlignCenter)

				elif key == "ssid" or key == "conn":	
					label.setText("{}".format(value))
					label.setAlignment(QtCore.Qt.AlignCenter)

				elif key == "mode":
					label.setAlignment(QtCore.Qt.AlignCenter)
					if value == 3:
						label.setText("3D FIX")
						label.setStyleSheet(GREEN)
					elif value == 2:
						label.setText("2D FIX")
						label.setStyleSheet(ORANGE)
					elif value == 1 or value == 0:
						label.setText("NO FIX")
						label.setStyleSheet(RED)
				else:
					label.setText("{} = {}".format(key, value))
			except Exception as e:
				pass

	def powerOnOffDevice(self):
		if not self.device["status"]["power"]:
			response = self.parent.cyberdeck.set_power(self.device["id"], True)
		else:
			response = self.parent.cyberdeck.set_power(self.device["id"], False)


class ProcessWidget(QWidget):
	def __init__(self, parent, process):
		super(ProcessWidget, self).__init__()

		self.parent = parent

		self.process = process
		self.buttonsWidget = QtWidgets.QWidget()
		self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)

		self.groupbox = QtWidgets.QGroupBox(self.process["config"]["s_id"])
		self.groupbox.setStyleSheet("font: 9pt \"Noto Sans\";")
		self.groupbox.setAlignment(Qt.AlignHCenter)
		self.vbox = QtWidgets.QVBoxLayout()

		blanking_label = QtWidgets.QLabel("")
		blanking_label.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
		self.vbox.addWidget(blanking_label)

		for key in self.process["status"]:
			label_name = "{}_{}_statuslabel".format(self.process["config"]["s_id"], key)
			setattr(self, label_name, QtWidgets.QLabel(key))
			if key == "running":
				label = getattr(self, label_name)
				label.setStyleSheet('background-color: rgb(0, 255, 0); font: 9pt \"Noto Sans\"')
				label.setAlignment(QtCore.Qt.AlignCenter)

			self.vbox.addWidget(getattr(self, label_name))

		self.buttonsWidget = QtWidgets.QWidget()
		self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)


		configButton = "{}_config_button".format(self.process["id"])
		setattr(self, configButton, QtWidgets.QToolButton())
		self.configbutton = getattr(self, configButton)
		self.configbutton.setText("Config")
		self.configbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\"; min-height: 35 px")
		self.configbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

		startStopButton = "{}_startstop_button".format(self.process["id"])
		setattr(self, startStopButton, QtWidgets.QToolButton())
		self.startstopbutton = getattr(self, startStopButton)
		self.startstopbutton.setText("START")
		self.startstopbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\"; min-height: 35 px")
		self.startstopbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

		self.buttonsWidgetLayout.addWidget(self.configbutton)
		self.buttonsWidgetLayout.addWidget(self.startstopbutton)

		self.vbox.addStretch(20)
		self.groupbox.setLayout(self.vbox)
		self.vbox2 = QtWidgets.QVBoxLayout()
		self.vbox2.addWidget(self.groupbox)
		self.vbox2.addWidget(self.buttonsWidget)
		self.setLayout(self.vbox2)

		self.startstopbutton.pressed.connect(self.startStopProcess)
		self.configbutton.pressed.connect(lambda: self.parent.configwindow.setConfig(self.process["config"]))

	def updateView(self, process):

		self.process = process

		id = self.process["id"]
		status = self.process["status"]
		config = self.process["config"]

		for key in status:
			value = status[key]
			label = getattr(self, "{}_{}_statuslabel".format(id, key))
			if key == "running":
				if value:
					label.setStyleSheet(GREEN)
					label.setText("ON")
					self.startstopbutton.setText("STOP")
				else:
					label.setStyleSheet(RED)
					label.setText("OFF")
					self.startstopbutton.setText("START")
			elif key == "i_samprate":
				label.setText("{} Msps".format(float(value)/1000000.0))
			elif key == "i_decimation":
				label.setText("{} decimate".format(value))
			elif key == "b_bias":
				if value:
					label.setStyleSheet(GREEN)
					label.setText("RF BIAS ON")
				else:
					label.setStyleSheet(RED)
					label.setText("RF BIAS OFF")
			else:
				label.setText("{} = {}".format(key, value))

	def startStopProcess(self):
		if not self.process["status"]["running"]:
			response = self.parent.cyberdeck.start_process(self.process["id"])
		else:
			response = self.parent.cyberdeck.stop_process(self.process["id"])


class ApplicationWidget(QWidget):
	def __init__(self, parent, application):
		super(ApplicationWidget, self).__init__()

		self.parent = parent

		self.application = application
		self.buttonsWidget = QtWidgets.QWidget()
		self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)

		self.groupbox = QtWidgets.QGroupBox(self.application["config"]["s_id"])
		self.groupbox.setStyleSheet("font: 9pt \"Noto Sans\";")
		self.groupbox.setAlignment(Qt.AlignHCenter)
		self.vbox = QtWidgets.QVBoxLayout()

		blanking_label = QtWidgets.QLabel("")
		blanking_label.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
		self.vbox.addWidget(blanking_label)

		for key in self.application["status"]:
			label_name = "{}_{}_statuslabel".format(self.application["config"]["s_id"], key)
			setattr(self, label_name, QtWidgets.QLabel(key))
			if key == "running":
				label = getattr(self, label_name)
				label.setStyleSheet('background-color: rgb(0, 255, 0);')
				label.setAlignment(QtCore.Qt.AlignCenter)

			self.vbox.addWidget(getattr(self, label_name))

		self.buttonsWidget = QtWidgets.QWidget()
		self.buttonsWidgetLayout = QtWidgets.QHBoxLayout(self.buttonsWidget)


		stopButton = "{}_stop_button".format(self.application["id"])
		setattr(self, stopButton, QtWidgets.QToolButton())
		self.stopbutton = getattr(self, stopButton)
		self.stopbutton.setText("STOP")
		self.stopbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\"; min-height: 35 px")
		self.stopbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

		startButton = "{}_start_button".format(self.application["id"])
		setattr(self, startButton, QtWidgets.QToolButton())
		self.startbutton = getattr(self, startButton)
		self.startbutton.setText("START")
		self.startbutton.setStyleSheet("border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\"; min-height: 35 px")
		self.startbutton.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

		self.buttonsWidgetLayout.addWidget(self.stopbutton)
		self.buttonsWidgetLayout.addWidget(self.startbutton)

		self.vbox.addStretch(20)
		self.groupbox.setLayout(self.vbox)
		self.vbox2 = QtWidgets.QVBoxLayout()
		self.vbox2.addWidget(self.groupbox)
		self.vbox2.addWidget(self.buttonsWidget)
		self.setLayout(self.vbox2)

		self.stopbutton.pressed.connect(lambda: self.parent.cyberdeck.stop_process(self.application["id"]))
		self.startbutton.pressed.connect(lambda: self.parent.cyberdeck.start_process(self.application["id"]))

	def updateView(self, application):

		self.application = application

		id = self.application["id"]
		status = self.application["status"]
		config = self.application["config"]

		for key in status:
			value = status[key]
			label = getattr(self, "{}_{}_statuslabel".format(id, key))
			if key == "running":
				if value:
					label.setStyleSheet(GREEN)
					label.setText("ON")
				else:
					label.setStyleSheet(RED)
					label.setText("OFF")
			else:
				label.setText("{} = {}".format(key, value))


class Statusbar(QDialog):

	def __init__(self, parent=None):
		super(Statusbar, self).__init__(parent)
		gui = path + '/gui/statusbar.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.move(0, 450)
		self.show()

	def popup(self):
		self.show()
		self.activateWindow()

class Barmenu(QWidget):

	def __init__(self, parent=None):
		super(Barmenu, self).__init__(parent)
		gui = path + '/gui/barmenu.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.move(615, 10)
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

		self.main_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(0))
		self.proc_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(1))
		self.apps_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(2))
		self.data_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(3))
		self.misc_button.pressed.connect(lambda: self.stackedWidget.setCurrentIndex(4))

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


class ConfigWindow(QWidget):

	def __init__(self, parent):
		super(ConfigWindow, self).__init__(None)
		self.parent = parent
		gui = path + '/gui/config_window.ui'
		loadUi(gui, self)

		self.setWindowTitle("Configuration Window")

		vheader = self.configtable.verticalHeader()
		vheader.setVisible(False)

		hheader = self.configtable.horizontalHeader()
		scrollbar = self.configtable.verticalScrollBar()
		scrollbar.setStyleSheet("QScrollBar:vertical { width: 30px; }")
		self.configtable.setHorizontalHeaderLabels(["key", "value"])

		self.configtable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
		self.configtable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

		self.setFixedSize(self.size())
		self.move(130, 130)
		self.hide()

		self.dialog_buttons.clicked.connect(self.dialogHandler)


	def updateLocalConfig(self, key, value):
		self.localConfig[key] = value

	def dialogHandler(self, button):
		sb = self.dialog_buttons.standardButton(button)
		if sb == QtWidgets.QDialogButtonBox.Apply:
			self.applyCurrentSettings()
		elif sb == QtWidgets.QDialogButtonBox.SaveAll:
			self.applyCurrentSettings()
			self.hide()
		elif sb == QtWidgets.QDialogButtonBox.Close:
			self.hide()
		else:
			pass

	def applyCurrentSettings(self):
		#Iterate over the widgets, and update the local copy of the remote configuration
		for i in range(0, len(self.remoteConfig)):
			item = self.configtable.item(i, 1)
			if item == None:
				item = self.configtable.cellWidget(i, 1)
			key = self.configtable.item(i, 0).text()

			type_tag = key[:2]
			if type_tag == "s_":
				if "device" in key:
					self.updateLocalConfig(key, item.currentText()) #Combobox
				else:
					self.updateLocalConfig(key, item.text()) #Normal str

			elif type_tag == "f_" or type_tag == "i_":
				self.updateLocalConfig(key, item.value())

			elif type_tag == "b_":
				if item.checkState() == QtCore.Qt.Checked:
					self.updateLocalConfig(key, 1)
				else:
					self.updateLocalConfig(key, 0)

			else:
				pass

		#Now that the local configuration has been updated with the GUI changes, compare local to remote config and update differences
		for key in self.localConfig:
			if self.remoteConfig[key] != self.localConfig[key]:
				print("Requesting update KEY:{} REMOTE:{} LOCAL:{}".format(key, self.remoteConfig[key], self.localConfig[key]))
				response = self.parent.cyberdeck.set_config(self.remoteConfig["s_id"], key, self.localConfig[key])
				if response["success"]:
					self.remoteConfig = response["config"]


	def setConfig(self, config):
		self.remoteConfig = config
		self.localConfig = copy.copy(config) # Local configuration is initially a copy of the remote
		self.configtable.clearContents()

		self.unit_label.setText("Currently configuring: {}".format(self.remoteConfig["s_id"]))
		self.configtable.setRowCount(len(self.remoteConfig))
		self.configtable.setColumnCount(2)

		i = 0
		for key in self.remoteConfig:
			self.configtable.setItem(i, 0, QTableWidgetItem(key))
			type_tag = key[:2]
			if type_tag == "s_":
				if key == "s_device":
					comboBox = QtWidgets.QComboBox()
					comboBox.addItem("rf1")
					comboBox.addItem("rf2")
					comboBox.addItem("alsa")
					index = comboBox.findText(self.remoteConfig[key])
					comboBox.setCurrentIndex(index)
					self.configtable.setCellWidget(i, 1, comboBox)


				else:
					tableItem = QTableWidgetItem(str(self.remoteConfig[key]))
					self.configtable.setItem(i, 1, tableItem)

			elif type_tag == "f_":
				floatEdit = QtWidgets.QDoubleSpinBox()
				floatEdit.setMaximum(50000.0)
				floatEdit.setMinimum(0.0)
				floatEdit.setSingleStep(0.01)
				floatEdit.setValue(self.remoteConfig[key])
				self.configtable.setCellWidget(i, 1, floatEdit)

			elif type_tag == "b_":
				tableItem = QTableWidgetItem()
				tableItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
				if self.remoteConfig[key]:
					tableItem.setCheckState(QtCore.Qt.Checked)
				else:
					tableItem.setCheckState(QtCore.Qt.Unchecked)
				self.configtable.setItem(i, 1, tableItem)

			elif type_tag == "i_":
				intEdit = QtWidgets.QSpinBox()
				intEdit.setMaximum(2147483647)
				intEdit.setValue(self.remoteConfig[key])
				self.configtable.setCellWidget(i, 1, intEdit)

			elif type_tag == "l_":
				tableItem = QTableWidgetItem(str(self.remoteConfig[key]))


			i = i + 1

		self.popup()

	def popup(self):
		self.show()
		self.showMaximized()
		self.activateWindow()


class MessageWindow(QWidget):

	def __init__(self, parent=None):
		super(MessageWindow, self).__init__(parent)
		gui = path + '/gui/message_window.ui'
		loadUi(gui, self)

		self.setFixedSize(self.size())
		self.setWindowTitle("Message Window")
		self.move(180, 180)
		self.hide()

		self.dialog_button.accepted.connect(self.hide)
		self.dialog_button.rejected.connect(self.hide)

	def setMessage(self, message):
		self.message_label.setText(message)

	def popup(self):
		self.show()
		self.showMaximized()
		self.activateWindow()


class Main(QMainWindow):

	buttonStyleIdle = 		"border: 1px solid black; border-radius: 25px; background-color: rgb(186, 186, 186); font: 9pt \"Noto Sans\";"
	buttonStyleClicked = 	"border: 1px solid black; border-radius: 25px; background-color: rgb(0, 255, 0); font: 9pt \"Noto Sans\";"
	buttonStyleClickedRed = "border: 1px solid black; border-radius: 25px; background-color: rgb(255, 0, 0); font: 9pt \"Noto Sans\";"

	boxStyleNight = 		"background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
	boxStyleNormal = 		""

	buttonStyleIdleNight = 		"border: 1px solid red; border-radius: 25px; background-color: rgb(0, 0, 0); color: rgb(255, 0, 0);"
	buttonStyleClickedNight = 	"border: 1px solid red; border-radius: 25px; background-color: rgb(255, 0, 0); color: rgb(0, 0, 0);"

	nightModeBackground = 	"background-color: rgb(0, 0, 0);"
	normalBackground = 		'background-color: rgb(186, 186, 186);'

	GREEN = 				'background-color: rgb(0, 255, 0); font: 9pt \"Noto Sans\";'
	RED = 					'background-color: rgb(255, 0, 0); font: 9pt \"Noto Sans\";'
	ORANGE =				'background-color: rgb(255, 165, 0); font: 9pt \"Noto Sans\";'

	blackTextRedBackground = "background-color: rgb(255, 0, 0); color: rgb(0, 0, 0);"

	nightModeEnabled = False

	def __init__(self, ip, parent=None):
		super(Main, self).__init__(parent)
		gui = path + '/gui/toolbar.ui'
		loadUi(gui, self)

		self.deviceWidgets = []
		self.processWidgets = []

		self.cyberdeck = RemoteCyberdeck(ip, 5000, 5001)
		self.cyberdeck.start()

		self.setFixedSize(self.size())
		self.setWindowFlags(Qt.FramelessWindowHint)
		self.statusBar().hide()
		self.move(732, -5)

		#---------WINDOWS-----------
		self.statusbar = Statusbar()
		self.messagewindow = MessageWindow()
		self.configwindow = ConfigWindow(self)
		self.menuwindow = MenuWindow()
		self.menuwindow.setFocusPolicy(QtCore.Qt.StrongFocus)
		self.barmenu = Barmenu()
		#---------------------------

		#Main toolbar
		self.audio_volup_button.pressed.connect(self.incrementVolume)
		self.audio_voldown_button.pressed.connect(self.decrementVolume)
		self.audio_mute_button.pressed.connect(self.toggleMute)
		self.display_brightup_button.pressed.connect(self.incrementBrightness)
		self.display_brightdown_button.pressed.connect(self.decrementBrightness)
		self.nav_start_button.pressed.connect(lambda: self.cyberdeck.start_process("navigation"))
		self.key_start_button.pressed.connect(lambda: self.cyberdeck.start_process("keyboard"))
		self.gqrx_start_button.pressed.connect(lambda: self.cyberdeck.start_process("gqrx"))

		self.menu_button.pressed.connect(self.menuwindow.popup)
		self.menu_button.pressed.connect(self.statusbar.popup)
		self.display_screenshot_button.pressed.connect(self.takeScreenshot)
		self.display_toggle_button.pressed.connect(lambda: self.cyberdeck.toggle_power("display"))

		self.menuwindow.ip_addr_label.setText("IP:{}".format(ip))

		self.initWidgets()

		self.menuwindow.exit_button.pressed.connect(self.exitApplication)
		self.menuwindow.shutdown_button.pressed.connect(lambda: self.cyberdeck.shutdown())
		self.menuwindow.reboot_button.pressed.connect(lambda: self.cyberdeck.reboot())


		#Main GUI refresh timer task
		self.timer = QTimer()
		self.timer.timeout.connect(self.updateWidgets)
		self.timer.start(1000)

	def changeConfig(self, device):
		pass

	def incrementVolume(self):
		response = self.cyberdeck.increment_volume()
		if response["success"]:
			newvolume = response["status"]["volume"]
			self.barmenu.popup()
			self.barmenu.volume_bar.setValue(int(newvolume))

	def decrementVolume(self):
		response = self.cyberdeck.decrement_volume()
		if response["success"]:
			newvolume = response["status"]["volume"]
			self.barmenu.popup()
			self.barmenu.volume_bar.setValue(int(newvolume))

	def toggleMute(self):
		response = self.cyberdeck.toggle_mute()
		"""
		if response["success"]:
			if response["status"]["mute"]:
				self.audio_mute_button.setStyleSheet(self.buttonStyleClickedRed)
			else:
				self.audio_mute_button.setStyleSheet(self.buttonStyleIdle)
		"""

	def incrementBrightness(self):
		response = self.cyberdeck.increment_brightness()
		if response["success"]:
			newBrightness = response["status"]["brightness"]
			self.statusbar.display_brightness_label.setText('BL: ' + str(newBrightness) + '%')
			self.barmenu.popup()
			self.barmenu.display_brightness_bar.setValue(int(newBrightness))

	def decrementBrightness(self):
		response = self.cyberdeck.decrement_brightness()
		if response["success"]:
			newBrightness = response["status"]["brightness"]
			self.statusbar.display_brightness_label.setText('BL: ' + str(newBrightness) + '%')
			self.barmenu.popup()
			self.barmenu.display_brightness_bar.setValue(int(newBrightness))

	def takeScreenshot(self):
		response = self.cyberdeck.screenshot()
		if response["success"]:
			filename = response["file"]
			self.messagewindow.setMessage("Screenshot saved to /home/pi/Pictures/screenshots/{}".format(filename))
			self.messagewindow.popup()

	def showConfig(self, configstatus):

		device = configstatus["config"]["s_id"]




	def test(self, str):
		print(str)

	def initWidgets(self):

		response = self.cyberdeck.get_configstatus()
		if response["success"]:
			configstatus = response["configstatus"]


			ignored_systems = ["publisher", "indicator", "clock"]
			self.deviceWidgets = [DeviceWidget(self, d) for d in configstatus if d["config"]["s_type"] == "device" and not d["id"] in ignored_systems]
			self.processWidgets = [ProcessWidget(self, p) for p in configstatus if p["config"]["s_type"] == "process"]
			self.applicationWidgets = [ApplicationWidget(self, a) for a in configstatus if a["config"]["s_type"] == "application"]
			#self.deviceWidgets = [DeviceWidget(self, d) for d in configstatus if d["s_id"]]

			rows = 2
			columns = 6
			mylist = [[0 for x in range(columns)] for x in range(rows)]
			k = 0
			for i in range(rows):
				for j in range(columns):
					try:
						deviceWidget = self.deviceWidgets[k]
						self.menuwindow.device_grid.addWidget(deviceWidget, i, j)
						k += 1
					except Exception as e:
						pass


			rows = 2
			columns = 5
			mylist = [[0 for x in range(columns)] for x in range(rows)]
			k = 0
			for i in range(rows):
				for j in range(columns):
					try:
						processWidget = self.processWidgets[k]
						self.menuwindow.processes_grid.addWidget(processWidget, i, j)
						k += 1
					except Exception as e:
						pass

			rows = 3
			columns = 6
			mylist = [[0 for x in range(columns)] for x in range(rows)]
			k = 0
			for i in range(rows):
				for j in range(columns):
					try:
						applicationWidget = self.applicationWidgets[k]
						self.menuwindow.applications_grid.addWidget(applicationWidget, i, j)
						k += 1
					except Exception as e:
						pass




	def updateWidgets(self):
		if self.cyberdeck.connected:
			self.menuwindow.connection_status_label.setStyleSheet(self.GREEN)
			self.menuwindow.connection_status_label.setText("CONNECTED")
		else:
			self.menuwindow.connection_status_label.setStyleSheet(self.RED)
			self.menuwindow.connection_status_label.setText("DISCONNECTED")


		current_status = self.cyberdeck.status

		for item in current_status:
			id = item["id"]
			status = item["status"]
			config = item["config"]

			try:
				if config["s_type"] == "device":
					widget = [w for w in self.deviceWidgets if w.device["config"]["s_id"] == id][0]
					widget.updateView(item)

				elif config["s_type"] == "process":
					widget = [w for w in self.processWidgets if w.process["config"]["s_id"] == id][0]
					widget.updateView(item)

				elif config["s_type"] == "application":
					widget = [w for w in self.applicationWidgets if w.application["config"]["s_id"] == id][0]
					widget.updateView(item)

			except Exception as e:
				pass
				#print(str(e))




		#Update auxiliary widgets (non-grid based)

		self.statusbar.obc_temp1_label.setText("T={} °C".format(round([device["status"]["temp1"] for device in current_status if device["id"] == "obc"][0], 1)))


		self.statusbar.audio_volume_label.setText("Vol={} %".format([device["status"]["volume"] for device in current_status if device["id"] == "audio"][0]))
		self.statusbar.display_brightness_label.setText("Bl={} %".format([device["status"]["brightness"] for device in current_status if device["id"] == "display"][0]))
		self.statusbar.ptot_label.setText("P={} W".format(round([device["status"]["consumption"] for device in current_status if device["id"] == "obc"][0] + [device["status"]["consumption"] for device in current_status if device["id"] == "display"][0], 1)))
		self.statusbar.battery_level_label.setText("Batt={} %".format([device["status"]["level"] for device in current_status if device["id"] == "battery"][0]))

		self.menuwindow.systemtime_label.setText("System time: {}".format([device["status"]["time_utc"] for device in current_status if device["id"] == "clock"][0]))
		self.menuwindow.gpstime_label.setText("GPS time: {}".format([device["status"]["time_utc"] for device in current_status if device["id"] == "gps"][0]))


		if [device["status"]["mute"] for device in current_status if device["id"] == "audio"][0]:
			self.audio_mute_button.setStyleSheet(self.buttonStyleClickedRed)
		else:
			self.audio_mute_button.setStyleSheet(self.buttonStyleIdle)

		self.statusbar.clock_utctime_label.setText("{}".format([device["status"]["time_utc"] for device in current_status if device["id"] == "clock"][0]))


		if [device["status"]["power"] for device in current_status if device["id"] == "gps"][0]:
			self.statusbar.gps_power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.gps_power_label.setStyleSheet(RED)

		if [device["status"]["power"] for device in current_status if device["id"] == "audio"][0]:
			self.statusbar.audio_power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.audio_power_label.setStyleSheet(RED)

		if [device["status"]["power"] for device in current_status if device["id"] == "usb"][0]:
			self.statusbar.usb_power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.usb_power_label.setStyleSheet(RED)

		if [device["status"]["rf1_power"] for device in current_status if device["id"] == "rf"][0]:
			self.statusbar.rf_rf1power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.rf_rf1power_label.setStyleSheet(RED)

		if [device["status"]["rf2_power"] for device in current_status if device["id"] == "rf"][0]:
			self.statusbar.rf_rf2power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.rf_rf2power_label.setStyleSheet(RED)

		if [device["status"]["power"] for device in current_status if device["id"] == "lan"][0]:
			self.statusbar.lan_power_label.setStyleSheet(GREEN)
		else:
			self.statusbar.lan_power_label.setStyleSheet(RED)





		if [application["status"]["running"] for application in current_status if application["id"] == "navigation"][0]:
			self.nav_start_button.setStyleSheet(self.buttonStyleClicked)
		else:
			self.nav_start_button.setStyleSheet(self.buttonStyleIdle)

		if [application["status"]["running"] for application in current_status if application["id"] == "gqrx"][0]:
			self.gqrx_start_button.setStyleSheet(self.buttonStyleClicked)
		else:
			self.gqrx_start_button.setStyleSheet(self.buttonStyleIdle)

		if [application["status"]["running"] for application in current_status if application["id"] == "keyboard"][0]:
			self.key_start_button.setStyleSheet(self.buttonStyleClicked)
		else:
			self.key_start_button.setStyleSheet(self.buttonStyleIdle)


	def exitApplication(self):
		self.statusbar.close()
		self.menuwindow.close()
		self.configwindow.close()
		self.barmenu.close()
		self.close()


if __name__ == '__main__':

	path = os.path.dirname(os.path.abspath(__file__))
	now = datetime.datetime.utcnow()

	parser = argparse.ArgumentParser(
		description='')

	parser.add_argument(
		'-i', '--ipaddress', type=str, help='ip address of the server to connect to', required=True)

	args = parser.parse_args()

	a = QApplication(sys.argv)
	app = Main(ip=args.ipaddress)
	app.show()
	a.exec_()
	os._exit(0)
