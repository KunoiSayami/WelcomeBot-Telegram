# -*- coding: utf-8 -*-
# tgbot.py
# Copyright (C) 2017-2020 KunoiSayami
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
import re
import logging
import datetime
from threading import Timer
import requests
from pyrogram import Client, Message, MessageHandler, Filters, User, \
	ContinuePropagation, ChatPermissions
from tgmysqldb import mysqldb
from cache import group_cache

# To delete this assert, please check line 37: os.getloadavg()
import platform
assert platform.system() == 'Linux', 'This program must run in Linux-like systems'

def getloadavg():
	return '{} {} {}'.format(*os.getloadavg())

setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
setflag_match = re.compile(r'^\/setflag(@[a-zA-Z_]*bot)?\s([a-zA-Z_]+)\s([01])$')

markdown_symbols = ('_', '*', '~', '#', '^', '&', '`')

logger = logging.getLogger(__file__)

def parse_user_name(user: User) -> str:
	name = user.first_name
	if user.last_name is not None:
		name = ' '.join((name, user.last_name))
	if len(name) > 20:
		name = name[:20] + '...'
	return ''.join(filter(lambda x: x not in markdown_symbols, name))

def send_and_delete(msg: Message, text: str, delay: int):
	m = msg.reply(text, parse_mode='markdown')
	t = Timer(delay, m.delete)
	t.daemon = True
	t.start()

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
		self._bot_id = int(self.bot.session_name)
		self.conn = mysqldb(self.config['database']['host'],
				self.config['database']['user'],
				self.config['database']['password'],
				self.config['database']['db'],
				autocommit=True)
		self._bot_name = None
		self.loaddatetime = datetime.datetime.now().replace(microsecond=0)
		self.groups = group_cache(self.conn, self.bot)
		self.error_message = ''
		if self.config.has_option('bot', 'error_message'):
			self.error_message = self.config['bot']['error_message']
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
	def bot_id(self) -> int:
		return self._bot_id

	@property
	def bot_name(self) -> str:
		if self._bot_name is None:
			self._bot_name = self.bot.get_me().username
			logger.debug('Fetched bot username => %s', self._bot_name)
		return self._bot_name

	def new_chat_member(self, client: Client, msg: Message):
		if self.bot_id in msg.new_chat_members:
			self.groups.insert_group(msg.chat.id)
			msg.reply('Please use /setwelcome to set welcome message')
			#msg.reply('This bot is refactoring code, feature may not available during this time')
		else:
			group_setting = self.groups[msg.chat.id]
			if group_setting is None:
				group_setting = self.groups.insert_group(msg.chat.id)
			welcome_text = group_setting.welcome_text
			if welcome_text is not None:
				last_msg = msg.reply(welcome_text.replace('$name', parse_user_name(msg.from_user)), parse_mode='markdown', disable_web_page_preview=True).message_id
				pervious_msg = self.conn.query_last_message_id(msg.chat.id)
				self.conn.insert_last_message_id(msg.chat.id, last_msg)
				if self.groups[msg.chat.id].no_welcome:
					if pervious_msg is not None:
						client.delete_messages(msg.chat.id, pervious_msg)

	def left_chat_member(self, _client: Client, msg: Message):
		if self.bot_id in msg.left_chat_member:
			self.groups.delete_group(msg.chat.id)

	def privileges_control(self, client: Client, msg: Message):
		bot_name = re.match(r'^\/(setwelcome|clear|status)(@[a-zA-Z_]*bot)?\s?', msg.text).group(2)
		if bot_name is not None and bot_name[1:] != self.bot_name:
			return
		group_info = self.groups[msg.chat.id]
		if group_info.admins is None:
			admins = client.get_chat_members(msg.chat.id, filter='administrators')
			group_info.admins = [x.user.id for x in admins]
			self.groups.update_group(msg.chat.id, group_info)
			logger.info('Updated administrator list in %d, new list is => %s', msg.chat.id, group_info.admins)
		if msg.from_user.id in group_info.admins:
			raise ContinuePropagation
		else:
			if not group_info.ignore_err and self.error_message != '':
				msg.reply(self.error_message)
				try:
					client.restrict_chat_member(msg.chat.id, msg.from_user.id, ChatPermissions(can_send_messages=False), msg.date + 60)
				except:
					pass

	def set_welcome_message(self, _client: Client, msg: Message):
		result = setcommand_match.match(msg.text)
		welcomemsg = str(result.group(2))
		result = gist_match.match(welcomemsg)
		if result:
			r = requests.get(welcomemsg)
			r.raise_for_status()
			welcomemsg = r.text
		if len(welcomemsg) > 2048:
			msg.reply("**Error**:Welcome message is too long.(len() must smaller than 4096)", parse_mode='markdown')
			return
		p = self.groups[msg.chat.id]
		p.welcome_text = welcomemsg
		self.groups.update_group(msg.chat.id, p)
		msg.reply(f"**Set welcome message to:**\n{welcomemsg}", parse_mode='markdown', disable_web_page_preview=True)

	def clear_welcome_message(self, _client: Client, msg: Message):
		p = self.groups[msg.chat.id]
		p.welcome_text = ''
		self.groups.update_group(msg.chat.id, p)
		msg.reply("**Clear welcome message completed!**", parse_mode='markdown')

	def generate_status_message(self, _client: Client, msg: Message):
		info = self.groups[msg.chat.id]
		send_and_delete(msg, 'Current welcome messsage: {}'.format(info.welcome_text), 10)

	def response_ping_command(self, _client: Client, msg: Message):
		send_and_delete(msg, '**Current chat_id:** `{}`\n**Your id:** `{}`\n**Bot runtime**: `{}`\n**System load avg**: `{}`'.format(
			msg.chat.id, msg.from_user.id, self.get_runtime(), getloadavg()), 10)

	def set_group_prop(self, _client: Client, msg: Message):
		r = setflag_match.match(msg.text)
		if r is None:
			return
		value = r.group(3) == '1'
		if r.group(2) == 'no_welcome':
			groupInfo = self.groups[msg.chat.id]
			groupInfo.no_welcome = value
			send_and_delete(msg, f'Set no welcome flag to **{value}** successfully!', 10)


	def init_receiver(self):
		self.bot.add_handler(MessageHandler(self.new_chat_member, Filters.new_chat_members))
		self.bot.add_handler(MessageHandler(self.left_chat_member, Filters.left_chat_member))
		self.bot.add_handler(MessageHandler(self.privileges_control, Filters.group & Filters.regex(r'^\/(setwelcome|clear|status)(@[a-zA-Z_]*bot)?\s?')))
		self.bot.add_handler(MessageHandler(self.set_welcome_message, Filters.group & Filters.regex(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')))
		self.bot.add_handler(MessageHandler(self.clear_welcome_message, Filters.group & Filters.regex(r'^\/clear(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.generate_status_message, Filters.group & Filters.regex(r'^\/status(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.response_ping_command, Filters.group & Filters.regex(r'^\/ping(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.set_group_prop, Filters.group & Filters.regex(r'^\/setflag(@[a-zA-Z_]*bot)?')))

	def get_runtime(self):
		return str(datetime.datetime.now().replace(microsecond=0) - self.loaddatetime)

if __name__ == '__main__':
	logging.getLogger("pyrogram").setLevel(logging.WARNING)
	logging.basicConfig(level=logging.DEBUG, format = '%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s')
	b = bot_class()
	b.run()
	b.stop()