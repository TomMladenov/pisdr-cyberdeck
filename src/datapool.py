#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

from configuration import *

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

	def __init__(self, parent=None):
		pass
