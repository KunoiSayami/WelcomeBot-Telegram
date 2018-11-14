# -*- coding: utf-8 -*-
# main.py
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
import sys
import time
import libpy.Log as Log
from libpy.Config import Config
from botlib.tgbot import bot_class

def main():
	Log.info('Strat initializing....')
	Log.info('Debug enable: {}',Log.get_debug_info()[0])
	Log.debug(1,'Debug level: {}',Log.get_debug_info()[1])
	bot_class()
	Log.info('Bot is now running!')
	while True:
		time.sleep(30)

def init():
	reload(sys)
	sys.setdefaultencoding('utf8')

if __name__ == '__main__':
	init()
	main()