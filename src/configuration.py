from configparser import SafeConfigParser
import ast
import logging
import os


path = os.path.dirname(os.path.realpath(__file__))

FILENAME = path + '/config.ini'

try:
	parser = SafeConfigParser()
	parser.read(FILENAME)
except Exception as e:
	print(e)


T_HIGH_OBC_ERR = parser.getfloat('limits', 'T_HIGH_OBC_ERR')
T_HIGH_OBC_WARN = parser.getfloat('limits', 'T_HIGH_OBC_WARN')

T_HIGH_OBC_CORE_ERR = parser.getfloat('limits', 'T_HIGH_OBC_CORE_ERR')
T_HIGH_OBC_CORE_WARN = parser.getfloat('limits', 'T_HIGH_OBC_CORE_WARN')

T_HIGH_BATT_ERR = parser.getfloat('limits', 'T_HIGH_BATT_ERR')
T_HIGH_BATT_WARN = parser.getfloat('limits', 'T_HIGH_BATT_WARN')

T_HIGH_DCDC_ERR = parser.getfloat('limits', 'T_HIGH_DCDC_ERR')
T_HIGH_DCDC_WARN = parser.getfloat('limits', 'T_HIGH_DCDC_WARN')


BATT_TEMP_ID = parser.get('temp-ids', 'BATT_TEMP_ID')
DCDC_TEMP_ID = parser.get('temp-ids', 'DCDC_TEMP_ID')
OBC_TEMP_ID = parser.get('temp-ids', 'OBC_TEMP_ID')

AUDIO_PWR_PIN = parser.getint('pin-assignments', 'AUDIO_PWR_PIN')
GPS_PWR_PIN = parser.getint('pin-assignments', 'GPS_PWR_PIN')
IMU_PWR_PIN = parser.getint('pin-assignments', 'IMU_PWR_PIN')
ALARM_LED_PIN = parser.getint('pin-assignments', 'ALARM_LED_PIN')

INA219_ADDR_CH0 = parser.get('address-assignment', 'INA219_ADDR_CH0')
INA219_ADDR_CH1 = parser.get('address-assignment', 'INA219_ADDR_CH1')

AUTOSTART_NAV = parser.getboolean('start', 'AUTOSTART_NAV')
DISABLE_USB_UPON_START = parser.getboolean('start', 'DISABLE_USB_UPON_START')
DISABLE_AUDIO_UPON_START = parser.getboolean('start', 'DISABLE_AUDIO_UPON_START')

RF1_SER = parser.get('rf', 'RF1_SER')
RF1_PPM = parser.getint('rf', 'RF1_PPM')
RF1_TCP_PORT = parser.getint('rf', 'RF1_TCP_PORT')

RF2_SER = parser.get('rf', 'RF2_SER')
RF2_PPM = parser.getint('rf', 'RF2_PPM')
RF2_TCP_PORT = parser.getint('rf', 'RF2_TCP_PORT')

GPS_LOG_PATH = parser.get('log', 'GPS_LOG_PATH')
MAIN_LOG_PATH = parser.get('log', 'MAIN_LOG_PATH')

INA219_CH0_ENABLE = parser.getboolean('status', 'INA219_CH0_ENABLE')
INA219_CH1_ENABLE = parser.getboolean('status', 'INA219_CH1_ENABLE')
ENABLE_ONEWIRE = parser.getboolean('status', 'ENABLE_ONEWIRE')
