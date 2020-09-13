#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

from configparser import SafeConfigParser
import ast
import logging
import os

class Datapool():

	#Temperatures
	f_temp_dcdc = 0.0
	b_temp_dcdc_err = False
	b_temp_dcdc_warn = False

	f_temp_obc = 0.0
	b_temp_obc_err = False
	b_temp_obc_warn = False

	f_temp_obc_core = 0.0
	b_temp_obc_core_err = False
	b_temp_obc_core_warn = False

	f_temp_batt = 0.0
	b_temp_batt_err = False
	b_temp_batt_warn = False

	#Voltages and currents
	f_voltage_obc = 1.0
	f_current_obc = 1.0
	f_power_obc = 1.0

	f_voltage_mon = 0.0
	f_current_mon = 0.0
	f_power_mon = 0.0

	f_power_tot = 0.0

	#gps data
	f_gps_lat = 0.0
	f_gps_lon = 0.0
	f_gps_alt = 0.0
	s_gps_time = ''
	l_gps_sats = []
	i_gps_mode = 0
	i_gps_numsats = 0
	s_gps_mgrs = ''
	s_gps_path = ''
	s_gps_speed = 0
	s_gps_driver = ''
	s_gps_locator = ''

	#Process states
	b_status_nav = False
	b_status_gqrx = False
	b_status_key = False
	b_status_ais = False
	b_status_acars = False
	b_status_vdl2 = False
	b_status_adsb = False
	b_status_dump1090 = False
	b_status_speakertest = False
	b_status_gpsd = False
	b_status_opencpn = False
	b_status_fldigi = False
	b_status_tcpserver_RF1 = False
	b_status_tcpserver_RF2 = False

	#Power states
	b_audio_enabled = False
	b_imu_enabled = False
	b_gps_enabled = False
	b_usb_enabled = False

	#RF1
	e_RF1_status = ''
	i_RF1_index = 100

	#RF2
	e_RF2_status = ''
	i_RF2_index = 100

	#Comms
	b_eth0_status = ''
	s_eth0_ip = ''
	b_wlan0_status = ''
	s_wlan0_ip = ''

	#Obc
	s_obc_uptime = ''

	def __init__(self, config_path):

		try:
			self.parser = SafeConfigParser()
			self.parser.read(config_path)
		except Exception as e:
			print(e)


		self.T_HIGH_OBC_ERR = self.parser.getfloat('limits', 'T_HIGH_OBC_ERR')
		self.T_HIGH_OBC_WARN = self.parser.getfloat('limits', 'T_HIGH_OBC_WARN')

		self.T_HIGH_OBC_CORE_ERR = self.parser.getfloat('limits', 'T_HIGH_OBC_CORE_ERR')
		self.T_HIGH_OBC_CORE_WARN = self.parser.getfloat('limits', 'T_HIGH_OBC_CORE_WARN')

		self.T_HIGH_BATT_ERR = self.parser.getfloat('limits', 'T_HIGH_BATT_ERR')
		self.T_HIGH_BATT_WARN = self.parser.getfloat('limits', 'T_HIGH_BATT_WARN')

		self.T_HIGH_DCDC_ERR = self.parser.getfloat('limits', 'T_HIGH_DCDC_ERR')
		self.T_HIGH_DCDC_WARN = self.parser.getfloat('limits', 'T_HIGH_DCDC_WARN')


		self.BATT_TEMP_ID = self.parser.get('temp-ids', 'BATT_TEMP_ID')
		self.DCDC_TEMP_ID = self.parser.get('temp-ids', 'DCDC_TEMP_ID')
		self.OBC_TEMP_ID = self.parser.get('temp-ids', 'OBC_TEMP_ID')

		self.AUDIO_PWR_PIN = self.parser.getint('pin-assignments', 'AUDIO_PWR_PIN')
		self.GPS_PWR_PIN = self.parser.getint('pin-assignments', 'GPS_PWR_PIN')
		self.IMU_PWR_PIN = self.parser.getint('pin-assignments', 'IMU_PWR_PIN')
		self.ALARM_LED_PIN = self.parser.getint('pin-assignments', 'ALARM_LED_PIN')

		self.INA219_ADDR_CH0 = self.parser.get('address-assignment', 'INA219_ADDR_CH0')
		self.INA219_ADDR_CH1 = self.parser.get('address-assignment', 'INA219_ADDR_CH1')

		self.AUTOSTART_NAV = self.parser.getboolean('start', 'AUTOSTART_NAV')
		self.DISABLE_USB_UPON_START = self.parser.getboolean('start', 'DISABLE_USB_UPON_START')
		self.DISABLE_AUDIO_UPON_START = self.parser.getboolean('start', 'DISABLE_AUDIO_UPON_START')

		self.RF1_SER = self.parser.get('rf', 'RF1_SER')
		self.RF1_PPM = self.parser.getint('rf', 'RF1_PPM')
		self.RF1_TCP_PORT = self.parser.getint('rf', 'RF1_TCP_PORT')

		self.RF2_SER = self.parser.get('rf', 'RF2_SER')
		self.RF2_PPM = self.parser.getint('rf', 'RF2_PPM')
		self.RF2_TCP_PORT = self.parser.getint('rf', 'RF2_TCP_PORT')

		self.INA219_CH0_ENABLE = self.parser.getboolean('status', 'INA219_CH0_ENABLE')
		self.INA219_CH1_ENABLE = self.parser.getboolean('status', 'INA219_CH1_ENABLE')
		self.ENABLE_ONEWIRE = self.parser.getboolean('status', 'ENABLE_ONEWIRE')
