#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Tom Mladenov'

import datetime

class Packet(object):

	def __init__(self, tag, payload):

		self.tag = tag
		self.utc = datetime.datetime.utcnow()
		self.payload = payload
