#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from server import Server
from packet import Packet

import sys
import os
import uvicorn
import logging
import time
import inspect


#Load server
server = Server()

#Load API
api = FastAPI()

def execute_function_subsystem(**kwargs):
	#print("Server subsystem function invocation: {}.{}({})".format(kwargs["system"], kwargs["function_name"], kwargs["args"]))
	try:
		s = [sys for sys in server.systems if sys.config["s_id"] == kwargs["system"]][0]
		target_function = getattr(s, kwargs["function_name"])
		if kwargs["args"]:
			return target_function(*kwargs["args"])
		else:
			return target_function()
	except IndexError:
		return {"success": False, "response": "System with provided ID not found"}
	except Exception as e:
		return {"success": False, "response": str(e)}


@api.put("/ping")
def ping():
	return {"success": True, "response": "pong"}

@api.get("/systems")
def get_systems():
	return server.get_systems()

@api.get("/config")
def get_config():
	return server.get_config()

@api.post("/config")
def save_config():
	return server.save_config()

@api.get("/status")
def get_status():
	return server.get_status()

@api.get("/configstatus")
def get_configstatus():
	return server.get_configstatus()


@api.get("/systems/{system}/config")
def get_config(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/{system}/config")
def set_config(system: str, key: str, value: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=[key, value])

@api.get("/systems/{system}/status")
def get_status(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)

@api.get("/systems/{system}/configstatus")
def get_configstatus(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/{system}/power")
def set_power(system: str, power: bool):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=[power])

@api.put("/systems/{system}/power/toggle")
def toggle_power(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/{system}/start_process")
def start_process(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/{system}/stop_process")
def stop_process(system: str):
	return execute_function_subsystem(system=system, function_name=inspect.stack()[0][3], args=None)





@api.put("/systems/obc/reboot")
def reboot():
		return execute_function_subsystem(system="obc", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/obc/shutdown")
def shutdown():
	return execute_function_subsystem(system="obc", function_name=inspect.stack()[0][3], args=None)


#-------------AUDIO-------------
@api.put("/systems/audio/volume")
def set_volume(volume: int):
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=[volume])

@api.put("/systems/audio/volume/increment")
def increment_volume():
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/audio/volume/decrement")
def decrement_volume():
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/audio/mute")
def set_mute(muted: bool):
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=[muted])

@api.put("/systems/audio/mute/toggle")
def toggle_mute():
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/audio/test")
def set_test(test: bool):
	return execute_function_subsystem(system="audio", function_name=inspect.stack()[0][3], args=[test])


#-------------DISPLAY-------------
@api.put("/systems/display/brightness")
def set_brightness(brightness: int):
	return execute_function_subsystem(system="display", function_name=inspect.stack()[0][3], args=[brightness])

@api.put("/systems/display/brightness/increment")
def increment_brightness():
	return execute_function_subsystem(system="display", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/display/brightness/decrement")
def decrement_brightness():
	return execute_function_subsystem(system="display", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/display/screenshot")
def screenshot():
	return execute_function_subsystem(system="display", function_name=inspect.stack()[0][3], args=None)

@api.get("/systems/rigctl/frequency")
def get_frequency():
	return execute_function_subsystem(system="rigctl", function_name=inspect.stack()[0][3], args=None)

@api.put("/systems/rigctl/frequency")
def set_frequency(frequency: float):
	return execute_function_subsystem(system="rigctl", function_name=inspect.stack()[0][3], args=[frequency])

@api.get("/systems/rigctl/mode")
def get_mode():
	return execute_function_subsystem(system="rigctl", function_name=inspect.stack()[0][3], args=None)



def custom_openapi():
	if api.openapi_schema:
		return api.openapi_schema
	openapi_schema = get_openapi(
		title="RPi Cyberdeck API",
		version="0.1.0",
		description="API interface description to interact with a RPi Cyberdeck",
		routes=api.routes,
	)
	api.openapi_schema = openapi_schema
	return api.openapi_schema


if __name__ == '__main__':

	log_config = uvicorn.config.LOGGING_CONFIG
	log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s %(module)s - %(message)s"
	log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(module)s - %(message)s"

	api.openapi = custom_openapi

	uvicorn.run(api, host=server.host, port=server.port, log_config=log_config, headers=[('Server', server.s_header_description)])
	server.stop_threads()
	sys.exit("Please wait until all systems are stopped...")
