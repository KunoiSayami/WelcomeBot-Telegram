# -*- coding: utf-8 -*-
# main.py
# Copyright (C) 2017 Too-Naive and contributors
#
# This module is part of WelcomeBot-Telegram and is released under
# the GPL v3 License: https://www.gnu.org/licenses/gpl-3.0.txt
from __future__ import unicode_literals
import sys
import time
import telepot
import libpy.Log as Log
import re,urllib2,random
from libpy.Config import Config
from threading import Lock,Thread
import libpy.BackupSQL as BackupSQL
from base64 import b64encode,b64decode
from libpy.TgBotLib import telepot_bot
from libpy.MainDatabase import MainDatabase

bot = None
syncLock = Lock()

command_match = re.compile(r'^\/(clear|setwelcome|ping|reload|poem|setflag)(@[a-zA-Z_]*bot)?')
setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
clearcommand_match = re.compile(r'^\/clear(@[a-zA-Z_]*bot)?$')
reloadcommand_match = re.compile(r'^\/reload(@[a-zA-Z_]*bot)?$')
poemcommand_match = re.compile(r'^\/poem(@[a-zA-Z_]*bot)?$')
setflagcommand_match = re.compile(r'^\/setflag(@[a-zA-Z_]*bot)?\s([a-zA-Z_]+)\s([01])$')

content_type_concerned = ['new_chat_member']
group_type = ['group','supergroup']
admin_type = ['creator','administrator']
flag_type = ['poemable','ignore_err']

group_cache = None
poem_cache = None

# To delete this assert, please check line 44: os.getloadavg()
import platform
assert platform.system() != 'Linux'

def getloadavg():
	r = os.getloadavg()
	return '{} {} {}'.format(r[0],r[1],r[2])

class bot_class(telepot_bot):
	def custom_init(self,*args,**kwargs):
		#self.message_loop(self.onMessage)
		t = Thread(target=self.__specfunc)
		t.daemon = True
		t.start()

	def __specfunc(self):
		syncLock.acquire()
		self.message_loop(self.onMessage)
		syncLock.release()

	def getChatMember(self,*args):
		return self.bot.getChatMember(*args)

	def onMessage(self,msg):	
		global group_cache,poem_cache
		Log.debug(3,'Incoming message')
		content_type, chat_type, chat_id = self.glance(msg)
		if content_type == 'new_chat_member' and msg['new_chat_participant']['id'] == self.getid():
			is_admin = group_cache.add((chat_id,None,0,1))
			assert(is_admin != -1)
			with MainDatabase() as db:
				db.execute("INSERT INTO `welcomemsg` (`group_id`) VALUES (%d)"%chat_id)
			return
		if content_type == 'left_chat_member' and msg['left_chat_member']['id'] == self.getid():
			group_cache.delete(chat_id)
			return
		if msg['chat']['type'] in group_type:
			if content_type=='text' and msg['text'][0] =='/' and command_match.match(msg['text']):
				result = poemcommand_match.match(msg['text'])
				if result:
					if group_cache.get(chat_id)['poemable']:
						result = poem_cache.get()
						if not result:
							result = b64encode('TBD')
						self.sendMessage(chat_id,b64decode(result),
							reply_to_message_id=msg['message_id'])
						return
					elif not group_cache.get(chat_id)['ignore_err']:
						self.sendMessage(chat_id,'Permission Denied.\n*你没有资格念他的诗，你给我出去*',
								parse_mode='Markdown',reply_to_message_id=msg['message_id'])
						return
					return
				if self.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
					if not group_cache.get(chat_id)['ignore_err']:
						self.sendMessage(chat_id,'Permission Denied.\n你没有权限，快滚',
							reply_to_message_id=msg['message_id'])
					if group_cache.get_is_admin(chat_id):
						self.bot.restrictChatMember(chat_id,msg['from']['id'],until_date=msg['date']+60)
					return
				result = setcommand_match.match(msg['text'])
				if result:
					welcomemsg = str(result.group(2))
					result = gist_match.match(welcomemsg)
					if result:
						r = urllib2.urlopen(welcomemsg)
						welcomemsg = r.read()
						r.close()
					if len(welcomemsg) > 4096:
						self.sendMessage(chat_id,"*Error*:Welcome message is too long.(len() must smaller than 4096)",
							parse_mode='Markdown',reply_to_message_id=msg['message_id'])
						return
					group_cache.edit((chat_id,b64encode(welcomemsg)))
					self.sendMessage(chat_id,"*Set welcome message to:*\n%s"%welcomemsg,
						disable_web_page_preview=True,parse_mode='Markdown',reply_to_message_id=msg['message_id'])
					return
				result = clearcommand_match.match(msg['text'])
				if result:
					group_cache.edit((chat_id,None))
					self.sendMessage(chat_id,"*Clear welcome message successfully!*",
						parse_mode='Markdown',reply_to_message_id=msg['message_id'])
					return
				result = reloadcommand_match.match(msg['text'])
				if result :
					if msg['from']['id'] != Config.bot.owner:
						self.sendMessage(chat_id,"*Please contant owner to reload configuration*",
							parse_mode='Markdown',reply_to_message_id=msg['message_id'])
						return
					group_cache.load()
					poem_cache.reload()
					self.sendMessage(chat_id,"*Reload configuration and poem successfully!*",
						parse_mode='Markdown',reply_to_message_id=msg['message_id'])
					return
				result = setflagcommand_match.match(msg['text'])
				if result:
					if str(result.group(2)) not in flag_type:
						if not group_cache.get(chat_id)['ignore_err']:
							self.sendMessage(chat_id,"*Error*: Flag \"%s\" not exist"%str(result.group(2)),
								parse_mode='Markdown',reply_to_message_id=msg['message_id'])
						return
					group_cache.editflag((chat_id,str(result.group(2)),int(result.group(3))))
					self.sendMessage(chat_id,"*Set flag \"%s\" to \"%d\" successfully!*"%(str(result.group(2)),int(result.group(3))),
						parse_mode='Markdown',reply_to_message_id=msg['message_id'])
					return
				self.sendMessage(chat_id,'*Current chat_id:{}\nYour id:{}\nBot runtime:{}\nSystem load avg: {}*'.format(
					chat_id, msg['from']['id'], Log.get_runtime(), getloadavg),
					parse_mode='Markdown',reply_to_message_id=msg['message_id'])
			elif content_type in content_type_concerned:
				result = group_cache.get(chat_id)['msg']
				if result:
					self.sendMessage(chat_id,b64decode(result),parse_mode='Markdown',
						disable_web_page_preview=True,reply_to_message_id=msg['message_id'])

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

class group_cache_class:
	def __init__(self):
		self.g = dict()

	def load(self,init=False):
		Log.debug(2,'Entering group_cache_class.load()')
		self.__init__()
		with MainDatabase() as db:
			result = db.query("SELECT * FROM `welcomemsg`")
			Log.debug(1,'in group_cache_class.load(): [exp(not result) = {}]',not result)
		for x in result:
			self.add(x)
		if init:
			syncLock.release()
		Log.info('Load welcomemsg table successful.')
		Log.debug(2,'Exiting group_cache_class.load()')

	def add(self,x,need_check_admin=True,not_found=False):
		global bot
		if need_check_admin:
			try:
				result = self.__check_admin(bot.getChatMember(x[0],bot.getid())['status'])
			except telepot.exception.BotWasKickedError:
				if not not_found:
					self.__db_del(x[0])
					Log.info('Delete kicked chat:{}',x[0])
				return -1
			except telepot.exception.TelegramError as e:
				if e[0] == 'Bad Request: chat not found':
					if not not_found:
						self.__db_del(x[0])
						Log.error('Delete not found chat:{}',x[0])
					Log.error('in group_cache_class.add() chat_id : {} not found',chat_id)
				else:
					raise e
				return -1
		else:
			result = 0
		self.g[x[0]]={'msg' : x[1],
			'is_admin':result,
			'poemable':x[2],
			'ignore_err':x[3]}
		return self.g[x[0]]['is_admin']

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
			return self.g[chat_id]
		except KeyError:
			Log.error('Can\'t find {} in get()',chat_id)
			bot.sendMessage(chat_id,'It\'s seems that database broken, please reset welcome message.')
			self.add((chat_id,None,0,1),not_found=True)
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


def main():
	global bot,group_cache,poem_cache
	Log.info('Strat initializing....')
	Log.info('Debug enable: {}',Log.get_debug_info()[0])
	Log.debug(1,'Debug level: {}',Log.get_debug_info()[1])
	syncLock.acquire()
	bot = bot_class()
	Log.info('Initializing other cache')
	group_cache = group_cache_class()
	group_cache.load(init=True)
	poem_cache = poem_class()
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