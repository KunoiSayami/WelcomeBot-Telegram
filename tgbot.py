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
import asyncio
import datetime
import logging
import os
import platform
import re
from configparser import ConfigParser
from typing import NoReturn

import aiohttp
import pyrogram.errors
from pyrogram import (ChatPermissions, Client, ContinuePropagation, Filters,
                      Message, MessageHandler, User)

from cache import GroupCache
from tgmysqldb import mysqldb

# To delete this assert, please check line 42: os.getloadavg()
assert platform.system() == 'Linux', 'This program must run in Linux-like systems'

def getloadavg() -> str:
	return ' '.join(map(str, os.getloadavg()))

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
	return ''.join(x for x in name if x not in markdown_symbols)
	#return ''.join(filter(lambda x: x not in markdown_symbols, name))


class WelcomeBot:
	def __init__(self):
		logger.debug('Enter WelcomeBot.__init__()')
		config = ConfigParser()
		config.read('data/config.ini')
		self.bot: Client = Client(config.get('bot', 'bot_token').split(':')[0],
							config.get('bot', 'api_id'),
							config.get('bot', 'api_hash'),
							bot_token=config.get('bot', 'bot_token'))
		self._bot_id: int = int(self.bot.session_name)
		self.conn: mysqldb = None
		self._bot_name = None
		self.loaddatetime: datetime.datetime = datetime.datetime.now().replace(microsecond=0)
		self.groups: GroupCache = None
		self.error_message: str = config.get('bot', 'error_message', fallback='')
		self.init_receiver()

	@staticmethod
	def send_and_delete(msg: Message, text: str, delay: int) -> NoReturn:
		asyncio.run_coroutine_threadsafe(WelcomeBot.bootstrap_send_message_timer(msg, text, delay), asyncio.get_event_loop())

	@staticmethod
	async def bootstrap_send_message_timer(msg: Message, text: str, delay: int) -> NoReturn:
		msg = await msg.reply(text, parse_mode='markdown', disable_web_page_preview=True)
		await asyncio.sleep(delay)
		await msg.delete()

	@classmethod
	async def create(cls) -> 'WelcomeBot':
		config = ConfigParser()
		config.read('data/config.ini')
		self = WelcomeBot()
		self.conn = await mysqldb.create(config.get('database', 'host'),
				config.get('database', 'user'),
				config.get('database', 'password'),
				config.get('database', 'db'))
		self.groups = await GroupCache.create(self.conn)
		return self

	async def run(self) -> NoReturn:
		await self.bot.start()
		if self._bot_name is None:
			self._bot_name = (await self.bot.get_me()).username
			logger.debug('Fetched bot username => %s', self._bot_name)
		try:
			await self.bot.idle()
		except InterruptedError:
			logger.debug('Catch!')

	async def stop(self) -> NoReturn:
		await self.bot.stop()
		await self.conn.close()

	@property
	def bot_id(self) -> int:
		return self._bot_id

	@property
	def bot_name(self) -> str:
		return self._bot_name

	async def new_chat_member(self, client: Client, msg: Message) -> NoReturn:
		if self.bot_id in msg.new_chat_members:
			await self.groups.insert_group(msg.chat.id)
			await msg.reply('Please use /setwelcome to set welcome message')
			#msg.reply('This bot is refactoring code, feature may not available during this time')
		else:
			group_setting = self.groups[msg.chat.id]
			if group_setting is None:
				group_setting = await self.groups.insert_group(msg.chat.id)
			welcome_text = group_setting.welcome_text
			if welcome_text is not None:
				try:
					last_msg = await msg.reply(welcome_text.replace('$name', parse_user_name(msg.from_user)), parse_mode='markdown', disable_web_page_preview=True).message_id
				except pyrogram.errors.ChatWriteForbidden:
					logger.error('Got ChatWriterForbidden in %d', msg.chat.id)
					await msg.chat.leave()
					await self.groups.delete_group(msg.chat.id)
					return
				pervious_msg = await self.conn.query_last_message_id(msg.chat.id)
				await self.conn.insert_last_message_id(msg.chat.id, last_msg)
				if self.groups[msg.chat.id].no_welcome:
					if pervious_msg is not None:
						await client.delete_messages(msg.chat.id, pervious_msg)

	async def left_chat_member(self, _client: Client, msg: Message) -> NoReturn:
		if self.bot_id in msg.left_chat_member:
			await self.groups.delete_group(msg.chat.id)

	async def privileges_control(self, client: Client, msg: Message) -> NoReturn:
		bot_name = re.match(r'^\/(setwelcome|clear|status)(@[a-zA-Z_]*bot)?\s?', msg.text).group(2)
		if bot_name is not None and bot_name[1:] != self.bot_name:
			return
		group_info = self.groups[msg.chat.id]
		if group_info.admins is None:
			admins = await client.get_chat_members(msg.chat.id, filter='administrators')
			group_info.admins = [x.user.id for x in admins]
			await self.groups.update_group(msg.chat.id, group_info)
			logger.info('Updated administrator list in %d, new list is => %s', msg.chat.id, group_info.admins)
		if msg.from_user.id in group_info.admins:
			raise ContinuePropagation
		else:
			if not group_info.ignore_err and self.error_message != '':
				await msg.reply(self.error_message)
				try:
					await client.restrict_chat_member(msg.chat.id, msg.from_user.id, ChatPermissions(can_send_messages=False), msg.date + 60)
				except:
					pass

	async def set_welcome_message(self, _client: Client, msg: Message) -> NoReturn:
		result = setcommand_match.match(msg.text)
		welcomemsg = str(result.group(2))
		result = gist_match.match(welcomemsg)
		if result:
			async with aiohttp.ClientSession(raise_for_status=True) as session:
				async with session.get(welcomemsg) as response:
					welcomemsg = await response.text()
		if len(welcomemsg) > 2048:
			await msg.reply("**Error**:Welcome message is too long.(len() must smaller than 2048)", parse_mode='markdown')
			return
		p = self.groups[msg.chat.id]
		p.welcome_text = welcomemsg
		await self.groups.update_group(msg.chat.id, p)
		await msg.reply(f"**Set welcome message to:**\n{welcomemsg}", parse_mode='markdown', disable_web_page_preview=True)

	async def clear_welcome_message(self, _client: Client, msg: Message) -> NoReturn:
		p = self.groups[msg.chat.id]
		p.welcome_text = ''
		await self.groups.update_group(msg.chat.id, p)
		await msg.reply("**Clear welcome message completed!**", parse_mode='markdown')

	def generate_status_message(self, _client: Client, msg: Message) -> NoReturn:
		info = self.groups[msg.chat.id]
		self.send_and_delete(msg, 'Current welcome messsage: {}'.format(info.welcome_text), 10)

	def response_ping_command(self, _client: Client, msg: Message) -> NoReturn:
		self.send_and_delete(msg, '**Current chat_id:** `{}`\n**Your id:** `{}`\n**Bot runtime**: `{}`\n**System load avg**: `{}`'.format(
			msg.chat.id, msg.from_user.id, self.get_runtime(), getloadavg()), 10)

	def set_group_prop(self, _client: Client, msg: Message) -> NoReturn:
		r = setflag_match.match(msg.text)
		if r is None:
			return self.send_and_delete(msg, 'Please read manual to use this command properly', 10)
		value = r.group(3) == '1'
		group_info = self.groups[msg.chat.id]
		if r.group(2) == 'no_welcome':
			group_info.no_welcome = value
		elif r.group(2) == 'no_blue':
			group_info.no_blue = value
		elif r.group(2) == 'ignore_err':
			group_info.ignore_err = value
		elif r.group(2) == 'no_service_msg':
			group_info.no_service_msg = value
		elif r.group(2) == 'no_new_member':
			group_info.no_new_member = value
		await self.groups.update_group(msg.chat.id, group_info)
		self.send_and_delete(msg, f'Set {r.group(2)} flag to **{value}** successfully!', 10)

	def init_receiver(self) -> NoReturn:
		self.bot.add_handler(MessageHandler(self.new_chat_member, Filters.new_chat_members))
		self.bot.add_handler(MessageHandler(self.left_chat_member, Filters.left_chat_member))
		self.bot.add_handler(MessageHandler(self.privileges_control, Filters.group & Filters.regex(r'^\/(setwelcome|clear|status|setflag)(@[a-zA-Z_]*bot)?\s?')))
		self.bot.add_handler(MessageHandler(self.set_welcome_message, Filters.group & Filters.regex(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')))
		self.bot.add_handler(MessageHandler(self.clear_welcome_message, Filters.group & Filters.regex(r'^\/clear(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.generate_status_message, Filters.group & Filters.regex(r'^\/status(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.response_ping_command, Filters.group & Filters.regex(r'^\/ping(@[a-zA-Z_]*bot)?$')))
		self.bot.add_handler(MessageHandler(self.set_group_prop, Filters.group & Filters.regex(r'^\/setflag(@[a-zA-Z_]*bot)?\s?')))

	def get_runtime(self) -> NoReturn:
		return str(datetime.datetime.now().replace(microsecond=0) - self.loaddatetime)


async def main() -> NoReturn:
	b = await WelcomeBot.create()
	await b.run()
	await b.stop()


if __name__ == '__main__':
	logging.getLogger("pyrogram").setLevel(logging.WARNING)
	logging.basicConfig(level=logging.DEBUG, format = '%(asctime)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s')
	asyncio.get_event_loop().run_until_complete(main())
