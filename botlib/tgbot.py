# -*- coding: utf-8 -*-
# tgbot.py
# Copyright (C) 2017 Too-Naive and contributors
#
# This module is part of WelcomeBot-Telegram and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
from __future__ import unicode_literals
import os
import time
import MySQLdb
import traceback
import re,urllib2
import libpy.Log as Log
import telepot.exception
from libpy.Config import Config
from threading import Lock,Thread
from libpy.TgBotLib import telepot_bot
from base64 import b64encode,b64decode
from botlib.poemcache import poem_class
from libpy.MainDatabase import MainDatabase
from botlib.groupcache import group_cache_class


command_match = re.compile(r'^\/(clear|setwelcome|ping|reload|poem|setflag)(@[a-zA-Z_]*bot)?\s?')
setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
clearcommand_match = re.compile(r'^\/clear(@[a-zA-Z_]*bot)?$')
reloadcommand_match = re.compile(r'^\/reload(@[a-zA-Z_]*bot)?$')
poemcommand_match = re.compile(r'^\/poem(@[a-zA-Z_]*bot)?$')
pingcommand_match = re.compile(r'^\/ping(@[a-zA-Z_]*bot)?$')
setflagcommand_match = re.compile(r'^\/setflag(@[a-zA-Z_]*bot)?\s([a-zA-Z_]+)\s([01])$')

content_type_concerned = ['new_chat_member']
group_type = ['group','supergroup']
admin_type = ['creator','administrator']
flag_type = ['poemable','ignore_err','noblue']

# To delete this assert, please check line 43: os.getloadavg()
import platform
assert platform.system() == 'Linux', 'This program must run in Linux-like systems'

def getloadavg():
	return '{} {} {}'.format(*os.getloadavg())

markdown_symbols = ['_', '*', '~', '#', '^', '&', '`']

def username_splice_and_fix(f):
	name = '{}'.format(f['first_name'])
	if 'last_name' in f:
		name += ' {}'.format(f['last_name'])
	name = name if len(name) <= 20 else name[:20]+'...'
	for x in markdown_symbols:
		name.replace( x, '')
	return name

class delete_target_message(Thread):
	def __init__(self, bot, chat_id, message_id):
		Thread.__init__(self)
		self.daemon = True
		self.bot = bot
		self.target = (chat_id,message_id)

	def run(self):
		time.sleep(5)
		try:
			self.bot.deleteMessage(self.target)
		except telepot.exception.TelegramError as e:
			if e[1] == 400:
				pass

class bot_class(telepot_bot):
	def custom_init(self,*args,**kwargs):
		#self.message_loop(self.onMessage)
		self.syncLock = Lock()
		self.syncLock.acquire()
		t = Thread(target=self.__specfunc)
		t.daemon = True
		t.start()
		Log.info('Initializing other cache')
		self.gcache = group_cache_class(bot=self,init=True)
		self.gcache.load(init=True,syncLock=self.syncLock)
		self.pcache = poem_class()
		self.fail_with_md = 'Markdown configure error, check settings or contact bot administrator if you think you are right'

	def __specfunc(self):
		self.syncLock.acquire()
		self.message_loop(self.onMessage)
		self.syncLock.release()

	def getChatMember(self,*args):
		return self.bot.getChatMember(*args)

	def onMessage(self,msg):
		content_type, chat_type, chat_id = self.glance(msg)

		# Added process
		if content_type == 'new_chat_member' and msg['new_chat_participant']['id'] == self.getid():
			self.gcache.add((chat_id, None, 0, 1, 0))
			with MainDatabase() as db:
				try:
					db.execute("INSERT INTO `welcomemsg` (`group_id`) VALUES (%d)"%chat_id)
				except MySQLdb.IntegrityError as e:
					if e[0] == 1062:
						Log.error('IntegrityError:{}', e[1])
					else:
						traceback.print_exc()
						raise e
			self.sendMessage(chat_id,'Please using /setwelcome to setting welcome message',
				reply_to_message_id=msg['message_id'])
			return

		# kicked process
		elif content_type == 'left_chat_member' and msg['left_chat_member']['id'] == self.getid():
			self.gcache.delete(chat_id)
			return

		# Main process
		elif msg['chat']['type'] in group_type:
			if content_type == 'text':
				get_result = self.gcache.get(chat_id)
				if 'entities' in msg and msg[
					'entities'][0]['type'] == 'bot_command' and msg[
						'text'][0] == '/': # Prevent suchas './sudo'
					if get_result['noblue']:
						delete_target_message(self.bot, chat_id, msg['message_id']).start()

					# Match bot command check
					if command_match.match(msg['text']):

						# Match /poem command
						result = poemcommand_match.match(msg['text'])
						if result:
							if get_result['poemable']:
								result = self.pcache.get()
								if not result:
									result = b64encode('TBD')
								self.sendMessage(chat_id, b64decode(result),
									reply_to_message_id=msg['message_id'])
								return
							elif not get_result['ignore_err']:
								self.sendMessage(chat_id, 'Permission Denied.\n*你没有资格念他的诗，你给我出去*',
										parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							return

						# Other command need admin privilege, check it.
						if self.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
							if not get_result['ignore_err']:
								self.sendMessage(chat_id, 'Permission Denied.\n你没有权限，快滚',
									reply_to_message_id=msg['message_id'])
							if self.gcache.get_is_admin(chat_id):
								self.bot.restrictChatMember(chat_id, msg['from']['id'], until_date=msg['date']+60)
							return

						# Match /setwelcome command
						result = setcommand_match.match(msg['text'])
						if result:
							welcomemsg = str(result.group(2))
							result = gist_match.match(welcomemsg)
							if result:
								r = urllib2.urlopen(welcomemsg)
								welcomemsg = r.read()
								r.close()
							if len(welcomemsg) > 4096:
								self.sendMessage(chat_id, "*Error*:Welcome message is too long.(len() must smaller than 4096)",
									parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							self.gcache.edit((chat_id, b64encode(welcomemsg)))
							self.sendMessage(chat_id, "*Set welcome message to:*\n%s"%welcomemsg,
								disable_web_page_preview=True, parse_mode='Markdown', reply_to_message_id=msg['message_id'])
							return

						# Match /clear command
						result = clearcommand_match.match(msg['text'])
						if result:
							self.gcache.edit((chat_id, None))
							self.sendMessage(chat_id, "*Clear welcome message successfully!*",
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])
							return

						# Match /reload command
						result = reloadcommand_match.match(msg['text'])
						if result :
							if msg['from']['id'] != Config.bot.owner:
								self.sendMessage(chat_id, "*Please contant owner to reload configuration*",
									parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							self.gcache.load()
							self.pcache.reload()
							self.sendMessage(chat_id, "*Reload configuration and poem successfully!*",
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])
							return

						# Match /setflag command
						result = setflagcommand_match.match(msg['text'])
						if result:
							if str(result.group(2)) not in flag_type:
								if not get_result['ignore_err']:
									self.sendMessage(chat_id, "*Error*: Flag \"%s\" not exist"%str(result.group(2)),
										parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							self.gcache.editflag((chat_id,str(result.group(2)),int(result.group(3))))
							self.sendMessage(chat_id, "*Set flag \"%s\" to \"%d\" successfully!*"%(str(result.group(2)), int(result.group(3))),
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])
							return

						# Finally match /ping
						if pingcommand_match.match(msg['text']):
							self.sendMessage(chat_id, '*Current chat_id:* `{}`\n*Your id:* `{}`\n*Bot runtime: {}\nSystem load avg: {}*'.format(
								chat_id, msg['from']['id'], Log.get_runtime(), getloadavg()),
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])

			elif content_type in content_type_concerned:
				result = self.gcache.get(chat_id)['msg']
				if result:
					self.sendMessage(chat_id, b64decode(result).replace('$name', username_splice_and_fix(msg['new_chat_participant'])),
						parse_mode='Markdown', disable_web_page_preview=True, reply_to_message_id=msg['message_id'])
