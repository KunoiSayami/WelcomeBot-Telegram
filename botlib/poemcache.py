# -*- coding: utf-8 -*-
# poemcache.py
# Copyright (C) 2017-2018 Too-Naive and contributors
#
# This module is part of WelcomeBot-Telegram and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
from __future__ import unicode_literals
import random
import libpy.Log as Log
from libpy.MainDatabase import MainDatabase

class poem_class:
	def __init__(self):
		random.seed()
		self.poem_pool = list()
		self.load()

	def load(self):
		with MainDatabase() as db:
			result = db.query("SELECT * FROM `poem`")
		for x in result:
			self.__add(x[0])

	def __add(self,poem_str):
		self.poem_pool.append(poem_str)

	def reload(self):
		self.__init__()

	def get(self):
		if not len(self.poem_pool):
			return None
		return self.poem_pool[random.randint(0,len(self.poem_pool)-1)]
