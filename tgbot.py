# -*- coding: utf-8 -*-
# tgbot.py
# Copyright (C) 2017-2019 KunoiSayami
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
from configparser import ConfigParser
import os
from libpy3.mysqldb import mysqldb
import logging
from pyrogram import Client, Message, MessageHandler, Filters, User
from cache import group_cache

# To delete this assert, please check line 62: os.getloadavg()
import platform
assert platform.system() == 'Linux', 'This program must run in Linux-like systems'

def getloadavg():
	return '{} {} {}'.format(*os.getloadavg())

markdown_symbols = ('_', '*', '~', '#', '^', '&', '`')

logger = logging.getLogger(__file__)

def parse_user_name(user: User) -> str:
	name = user.first_name
	if user.last_name is not None:
		name = ' '.join((name, user.last_name))
	if len(name) > 20:
		name = name[:20] + '...'
	return ''.join(filter(lambda x: x not in markdown_symbols, name))

class bot_class:
	bot_self = None
	def __init__(self):
		logger.debug('Enter bot_class.__init__()')
		self.config = ConfigParser()
		self.config.read('data/config.ini')
		self.bot = Client(self.config['bot']['bot_token'].split(':')[0],
							self.config['bot']['api_id'],
							self.config['bot']['api_hash'],
							bot_token=self.config['bot']['bot_token'])
		self._bot_id = int(self.config['bot']['bot_token'].split(':')[0])
		self.conn = mysqldb(self.config['database']['host'],
				self.config['database']['user'],
				self.config['database']['password'],
				self.config['database']['db'],
				autocommit=True)
		self.groups = group_cache(self.conn, self.bot)
		self.init_receiver()

	def run(self):
		self.bot.start()
		try:
			self.bot.idle()
		except InterruptedError:
			pass

	def stop(self):
		self.bot.stop()
		self.conn.close()

	@property
	def bot_id(self):
		return self._bot_id

	def new_chat_member(self, client: Client, msg: Message):
		if self.bot_id in msg.new_chat_members:
			self.groups.insert_group(msg.chat.id)
			#client.send_message(msg.chat.id, 'Please use /setwelcome to set welcome message', reply_to_message_id=msg.message_id)
			client.send_message(msg.chat.id, 'This bot is refactoring code, feature may not available during this time', reply_to_message_id=msg.message_id)
		else:
			welcome_text = self.groups[msg.chat.id].welcome_text
			if welcome_text is not None:
				client.send_message(msg.chat.id, welcome_text.replace('$name', parse_user_name(msg.from_user)), 'markdown', True, reply_to_message_id=msg.message_id)

	def left_chat_member(self, _client: Client, msg: Message):
		if self.bot_id in msg.left_chat_member:
			self.groups.delete_group(msg.chat.id)

	def init_receiver(self):
		self.bot.add_handler(MessageHandler(self.new_chat_member, Filters.new_chat_members))
		self.bot.add_handler(MessageHandler(self.left_chat_member, Filters.left_chat_member))

if __name__ == '__main__':
	b = bot_class()
	b.run()
	b.stop()