# -*- coding: utf-8 -*-
# groupcache.py
# Copyright (C) 2017-2018 Too-Naive and contributors
#
# This module is part of WelcomeBot-Telegram and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
from __future__ import unicode_literals
import telepot
import libpy.Log as Log
from libpy.MainDatabase import MainDatabase

admin_type = ['creator','administrator']



class group_cache_class:
	def __init__(self,**kwargs):
		self.g = dict()
		if 'init' in kwargs:
			self.bot = kwargs['bot']

	def load(self,init=False,**kwargs):
		Log.debug(2,'Entering group_cache_class.load()')
		self.__init__()
		with MainDatabase() as db:
			result = db.query("SELECT * FROM `welcomemsg`")
			Log.debug(1,'in group_cache_class.load(): [exp(not result) = {}]',not result)
		for x in result:
			self.add(x)
		if init:
			#syncLock.release()
			kwargs['syncLock'].release()
		Log.info('Load welcomemsg table successful.')
		Log.debug(2,'Exiting group_cache_class.load()')

	def add(self,x,need_check_admin=True,not_found=False):
		if need_check_admin:
			try:
				result = self.__check_admin(self.bot.getChatMember(x[0],self.bot.getid())['status'])
			except telepot.exception.BotWasKickedError:
				if not not_found:
					self.__db_del(x[0])
					Log.info('Delete kicked chat:{}',x[0])
					return
			except telepot.exception.TelegramError as e:
				if e[0] == 'Bad Request: chat not found':
					if not not_found:
						self.__db_del(x[0])
						Log.error('Delete not found chat:{}',x[0])
					Log.error('in group_cache_class.add() chat_id : {} not found',x[0])
				elif e[0] == 'Forbidden: bot is not a member of the supergroup chat':
					self.__db_del(x[0])
					Log.error('Delete kicked chat:{}', x[0])
				else:
					raise e
			finally:
				result = 0
		else:
			result = 0
		self.g[x[0]]={'msg': x[1],
			'is_admin':result,
			'poemable':x[2],
			'ignore_err':x[3],
			'noblue':x[4]}

	def __db_add(self,chat_id):
		with MainDatabase() as db:
			db.execute("INSERT INTO `welcomemsg` (`group_id`) VALUES (%d)"%chat_id)

	def delete(self,chat_id):
		try:
			del self.g[chat_id]
			self.__db_del(chat_id)
		except KeyError:
			Log.error('Can\'t find {} in delete()',chat_id)

	def get(self,chat_id):
		try:
			Log.debug(2,'Calling group_cache_class.get() [chat_id in self.g  = {}]', chat_id in self.g)
			Log.debug(2,'[self.g[{}] = {}]', chat_id, self.g[chat_id])
			return self.g[chat_id]
		except KeyError:
			Log.error('Can\'t find {} in get()',chat_id)
			bot.sendMessage(chat_id,'It\'s seems that database broken, please reset welcome message.')
			self.add((chat_id,None,0,1,0),not_found=True)
			self.__db_add(chat_id)
			return {'msg':None}

	def __db_del(self,chat_id):
		with MainDatabase() as db:
			db.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %d"%(chat_id))

	def __check_admin(self,status):
		if status in admin_type:
			return 1
		else:
			return 0

	def get_is_admin(self,chat_id):
		return {1:True,0:False}.get(self.get(chat_id)['is_admin'])

	def edit(self,x):
		with MainDatabase() as db:
			if x[1]:
				db.execute("UPDATE `welcomemsg` SET `msg` = '%s' WHERE `group_id` = %d"%(x[1],x[0]))
			else:
				db.execute("UPDATE `welcomemsg` SET `msg` = NULL WHERE `group_id` = %d"%x[0])
		self.g[x[0]]['msg'] = x[1]

	def editflag(self,x):
		if self.g[x[0]][x[1]] == x[2]:
			return
		self.g[x[0]][x[1]] = x[2]
		with MainDatabase() as db:
			db.execute("UPDATE `welcomemsg` SET `%s` = %d WHERE `group_id` = %d"%(x[1],x[2],x[0]))