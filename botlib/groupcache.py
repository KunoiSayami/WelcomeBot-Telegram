# -*- coding: utf-8 -*-
# groupcache.py
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
import telepot
import libpy.Log as Log
from libpy.datastruct import switch_class
from libpy.MainDatabase import MainDatabase
from base64 import b64decode, b64encode

admin_type = ('creator', 'administrator')
flag_name = (u'no_welcome', u'no_new_member', u'no_service_msg')

class gc_base_switch:
	def __init__(self, tuple_attr, base_value=0):
		self.attr = {tuple_attr[x-1]:x for x in xrange(1, len(tuple_attr)+1)}
		self.pri_set = switch_class(base_value)
	def __int__(self):
		return int(self.pri_set)
	def __getitem__(self, str_key):
		key = self.attr[str_key]
		# raise KeyError if key not found
		return self.pri_set[key]
	def __setitem__(self, str_key, value):
		key = self.attr[str_key]
		self.pri_set[key] = value

class group_cache_class:
	def __init__(self, **kwargs):
		self.g = dict()
		#self.external_dict = dict()
		if 'init' in kwargs:
			self.bot = kwargs['init']

	def load(self):
		Log.debug(2, 'Entering group_cache_class.load()')
		self.__init__()
		with MainDatabase() as db:
			result = db.query("SELECT * FROM `welcomemsg`")
		for x in result:
			self.add(x)
		#if init:
			#syncLock.release()
			#kwargs['syncLock'].release()
		Log.info('Load welcomemsg table successful.')
		Log.debug(2, 'Exiting group_cache_class.load()')

	def add(self, x, need_check_admin=True, not_found=False):
		if need_check_admin:
			try:
				result = {True:1, False:0}.get(self.bot.getChatMember(x[0], self.bot.getid())['status'])
			except telepot.exception.BotWasKickedError:
				if not not_found:
					self.__db_del(x[0])
					Log.info('Delete kicked chat:{}', x[0])
					return
			except telepot.exception.TelegramError as e:
				if e[0] == 'Bad Request: chat not found':
					if not not_found:
						self.__db_del(x[0])
						Log.warn('Delete not found chat:{}', x[0])
					Log.warn('in group_cache_class.add() chat_id : {} not found', x[0])
				elif 'Forbidden: bot is not a member of the' in e[0]:
					self.__db_del(x[0])
					Log.warn('Delete kicked chat:{}', x[0])
				else:
					raise e
			finally:
				result = 0
		else:
			result = 0
		self.g[x[0]]={'msg': x[1],
			'is_admin': result,
			'poemable': x[2],
			'ignore_err': x[3],
			'noblue': x[4],
			'other': gc_base_switch(flag_name, x[5]),
			'except': eval(b64decode(x[6]))}

	def __db_add(self, chat_id):
		with MainDatabase() as db:
			db.execute("INSERT INTO `welcomemsg` (`group_id`) VALUES (%d)"%chat_id)

	def delete(self, chat_id):
		try:
			del self.g[chat_id]
			self.__db_del(chat_id)
		except KeyError:
			Log.error('Can\'t find {} in delete()', chat_id)

	def get(self, chat_id):
		try:
			Log.debug(2, 'Calling group_cache_class.get() [chat_id in self.g  = {}]', chat_id in self.g)
			Log.debug(2, '[self.g[{}] = {}]', chat_id, self.g[chat_id])
			return self.g[chat_id]
		except KeyError:
			Log.error('Can\'t find {} in get()',chat_id)
			self.add((chat_id, None, 0, 1, 0, 0, b64encode(repr([]))), not_found=True)
			self.__db_add(chat_id)
			self.bot.sendMessage(chat_id, 'It\'s seems that database broken, please reset welcome message.')
			return {'msg':None}

	def except_(self,chat_id, command, is_del=False):
		if is_del:
			try:
				self.g[chat_id]['except'].remove(command)
			except ValueError:
				return False
		else:
			self.g[chat_id]['except'].append(command)
			if len(b64encode(repr(self.g[chat_id]['except']))) > 498:
				self.g[chat_id]['except'].remove(command)
				return False
			self.g[chat_id]['except'] = list(set(self.g[chat_id]['except']))
		with MainDatabase() as db:
			db.execute("UPDATE `welcomemsg` SET `except` = '{}' WHERE `group_id` = {}".format(
				b64encode(repr(self.g[chat_id]['except'])), chat_id))
		return True

	def __db_del(self, chat_id):
		with MainDatabase() as db:
			db.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %d"%(chat_id))

	def get_is_admin(self, chat_id):
		return {1:True, 0:False}.get(self.get(chat_id)['is_admin'])

	def edit(self, x):
		with MainDatabase() as db:
			if x[1]:
				db.execute("UPDATE `welcomemsg` SET `msg` = '%s' WHERE `group_id` = %d"%(x[1], x[0]))
			else:
				db.execute("UPDATE `welcomemsg` SET `msg` = NULL WHERE `group_id` = %d"%x[0])
		self.g[x[0]]['msg'] = x[1]

	def editflag(self, x):
		'''
			x must be `tuple',
			x structure:
				(chat_id, flag_string_name, flag_value)
		'''
		#Log.debug(1, 'x = {}, x in flag_name = {}, flag_name = {}', repr(x), repr(x in flag_name), repr(flag_name))
		if x[1] in flag_name:
			if self.g[x[0]]['other'][x[1]] == x[2]:
				return
			self.g[x[0]]['other'][x[1]] = x[2]
			with MainDatabase() as db:
				db.execute("UPDATE `welcomemsg` set `other` = {} WHERE `group_id` = {}".format(
					int(self.g[x[0]]['other']), x[0]))
		else:
			if self.g[x[0]][x[1]] == x[2]:
				return
			self.g[x[0]][x[1]] = x[2]
			with MainDatabase() as db:
				db.execute("UPDATE `welcomemsg` SET `%s` = %d WHERE `group_id` = %d"%(x[1], x[2], x[0]))