# -*- coding: utf-8 -*-
# main.py
# Copyright (C) 2017-2018 Too-Naive and contributors
#
# This module is part of WelcomeBot-Telegram and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
from __future__ import unicode_literals
import sys
import time
import libpy.Log as Log
from libpy.Config import Config
from botlib.tgbot import bot_class
import libpy.BackupSQL as BackupSQL

def main():
	Log.info('Strat initializing....')
	Log.info('Debug enable: {}',Log.get_debug_info()[0])
	Log.debug(1,'Debug level: {}',Log.get_debug_info()[1])
	bot_class()
	Log.info('Bot is now running!')
	Log.info('Starting BackupSQL daemon')
	BackupSQL.sql_backup_daemon().start()
	Log.info('BackupSQL daemon is now running')
	while True:
		time.sleep(30)

def init():
	reload(sys)
	sys.setdefaultencoding('utf8')

if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == '--restore':
		BackupSQL.restore_sql()
	else:
		init()
		main()