#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import os
import sys
import time

from PyQt5.QtCore import (QCoreApplication, QObject, QRunnable, QThread, pyqtSignal, QEvent, Qt, QVariant, QTimer, QAbstractTableModel)
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QWidget, QListWidgetItem, QFileDialog, QTableWidgetItem, qApp
from PyQt5.uic import loadUi
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QImage, QIcon, QPixmap, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QBrush

class SondeFrame(object):

	def __init__(self, datetime, type, id, frame, lat, lon, alt, heading, vel_h, vel_v, sats):

		self.datetime = datetime
		self.type = type
		self.id = id
		self.frame = frame
		self.lat = lat
		self.lon = lon
		self.alt = alt
		self.heading = heading
		self.vel_h = vel_h
		self.vel_v = vel_v
		self.sats = sats



class SondeFrameTableModel(QtCore.QAbstractTableModel):

	def __init__(self, data):
		QtCore.QAbstractTableModel.__init__(self)
		self._data = data

	def setHeader(self, header):
		self._header = header

	def rowCount(self, parent):
		return len(self._data)

	def columnCount(self, parent):
		return len(self._header)

	def data(self, index, role):
		if index.isValid():
			if role != QtCore.Qt.DisplayRole:
				return None
			else:
				switcher={
							0: str(self._data[index.row()].datetime),
							1: self._data[index.row()].type,
							2: self._data[index.row()].id,
							3: str(self._data[index.row()].frame),
							4: str(self._data[index.row()].lat),
							5: str(self._data[index.row()].lon),
							6: str(self._data[index.row()].alt),
							7: str(self._data[index.row()].heading),
							8: str(self._data[index.row()].vel_h),
							9: str(self._data[index.row()].vel_v),
							10: str(self._data[index.row()].sats)
						}

				return switcher.get(index.column(), "N/A")

	def headerData(self, section, orientation, role):
		if role != QtCore.Qt.DisplayRole or orientation != QtCore.Qt.Horizontal:
			return None
		return self._header[section]
