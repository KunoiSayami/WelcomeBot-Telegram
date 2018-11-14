# -*- coding: utf-8 -*-
# tgbot.py
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
import os
import time
import MySQLdb
import traceback
import re, urllib2
import libpy.Log as Log
import telepot.exception
from libpy.Config import Config
from libpy.DiskCache import DiskCache
from libpy.TgBotLib import telepot_bot
from base64 import b64encode,b64decode
from threading import Lock, Thread, Timer
from botlib.poemcache import poem_class
from libpy.MainDatabase import MainDatabase
from botlib.groupcache import group_cache_class

command_match = re.compile(r'^\/(setwelcome|setflag|s|except(d|a))(@[a-zA-Z_]*bot)?\s?')
setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
clearcommand_match = re.compile(r'^\/clear(@[a-zA-Z_]*bot)?$')
reloadcommand_match = re.compile(r'^\/reload(@[a-zA-Z_]*bot)?$')
poemcommand_match = re.compile(r'^\/poem(@[a-zA-Z_]*bot)?$')
pingcommand_match = re.compile(r'^\/ping(@[a-zA-Z_]*bot)?$')
statuscommand_match = re.compile(r'\/status(@[a-zA-Z_]*bot)?$')
setflagcommand_match = re.compile(r'^\/setflag(@[a-zA-Z_]*bot)?\s([a-zA-Z_]+)\s([01])$')
setflag2command_match = re.compile(r'^\/s(@[a-zA-Z_]*bot)?\s([a-zA-Z_]+)\s([01])$')
botcommand_match = re.compile(r'^\/([a-zA-Z]+)\s?(@[a-zA-Z_]+)?$')
exceptcommand_match = re.compile(r'^\/except(d|a)(@[a-zA-Z_]*bot)?\s(.*)$')
noparmcommand_match = re.compile(r'^\/(clear|ping|reload|poem|status|d|l)(@[a-zA-Z_]*bot)?$')

content_type_concerned = ('new_chat_member')
group_type = ('group', 'supergroup')
admin_type = ('creator', 'administrator')
flag_type = ('poemable', 'ignore_err', 'noblue', 'no_welcome', 'no_new_member', 'no_service_msg')
service_msg_type = ('new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'pinned_message')

# To delete this assert, please check line 62: os.getloadavg()
import platform
assert platform.system() == 'Linux', 'This program must run in Linux-like systems'

def getloadavg():
	return '{} {} {}'.format(*os.getloadavg())

markdown_symbols = (u'_', u'*', u'~', u'#', u'^', u'&', u'`')

def username_splice_and_fix(f):
	name = '{}'.format(f['first_name'])
	if 'last_name' in f:
		name += ' {}'.format(f['last_name'])
	name = name if len(name) <= 20 else name[:20]+'...'
	return ''.join(filter(lambda x: x not in markdown_symbols, name))

class delete_target_message(Thread):
	def __init__(self, chat_id, message_id, time_delay=5):
		Thread.__init__(self)
		self.daemon = True
		#self.bot = bot
		self.target = (chat_id, message_id)
		self.time_delay = time_delay

	def run(self):
		time.sleep(self.time_delay)
		try:
			bot_class.bot_self.deleteMessage(self.target)
		except telepot.exception.TelegramError as e:
			if e[1] == 400:
				# Catch access denied
				return
			Log.warn('Catched telepot.exception.TelegramError:{}', repr(e))

status_gen_string = "".join(
'''Current welcome message: {}

Flag status:
poemable = {}
ignore_err = {}
noblue = {}
no_welcome = {}
no_new_member = {}
no_service_msg = {}
except_command = {}
''')

def sendMessage_and_delete(chat_id, msg, reply_to, timeout=5, *args):
	msgid = bot_class.bot_self.sendMessage(chat_id, msg.format(*args), reply_to_message_id=reply_to)['message_id']
	delete_target_message(chat_id, msgid, timeout).start()
	del msgid

def gen_status_msg(g):
	result = 'bnVsbA==' if g['msg'] is None else g['msg']
	return status_gen_string.format(b64decode(result), g['poemable'],
		g['ignore_err'], g['noblue'], g['other']['no_welcome'],
		g['other']['no_new_member'], g['other']['no_service_msg'], repr(g['except']))

class bot_class(telepot_bot):
	bot_self = None
	def custom_init(self, *args, **kwargs):
		self.syncLock = Lock()
		self.cache = DiskCache('data/id_cache', default_return_type=dict())
		self.external_store = self.cache.read_without_except()
		with self.syncLock:
			t = Thread(target=self.__specfunc)
			t.daemon = True
			t.start()
			Log.info('Initializing other cache')
			self.gcache = group_cache_class(init=self)
			self.gcache.load()
		self.pcache = poem_class()
		self.fail_with_md = 'Markdown configure error, check settings or contact bot administrator if you think you are right'

	def __specfunc(self):
		with self.syncLock:
			self.message_loop(self.onMessage)
		bot_class.bot_self = self.bot

	def getChatMember(self, *args):
		return self.bot.getChatMember(*args)

	def onMessage(self, msg):
		content_type, chat_type, chat_id = self.glance(msg)

		# Added process
		if content_type == 'new_chat_member' and msg['new_chat_participant']['id'] == self.getid():
			self.gcache.add((chat_id, None, 0, 1, 0, 0, b64encode(repr([]))))
			with MainDatabase() as db:
				try:
					db.execute("INSERT INTO `welcomemsg` (`group_id`) VALUES (%d)"%chat_id)
				except MySQLdb.IntegrityError as e:
					if e[0] == 1062:
						Log.error('IntegrityError:{}', e[1])
					else:
						traceback.print_exc()
						raise e
			self.sendMessage(chat_id,'Please use /setwelcome to set welcome message',
				reply_to_message_id=msg['message_id'])
			return

		# Kicked process
		elif content_type == 'left_chat_member' and msg['left_chat_member']['id'] == self.getid():
			self.gcache.delete(chat_id)
			return

		# Main process
		elif msg['chat']['type'] in group_type:

			# Show welcome message
			if content_type in content_type_concerned:
				result = self.gcache.get(chat_id)['msg']
				if self.gcache.get(chat_id)['other']['no_new_member']:
					delete_target_message(chat_id, msg['message_id'], 3).start()
				if result:
					if self.gcache.get(chat_id)['other']['no_welcome'] and \
						self.external_store.get(chat_id) is not None:
						delete_target_message(chat_id, self.external_store.get(chat_id), 0).start()
					self.external_store[chat_id] = self.sendMessage(chat_id, b64decode(result).replace('$name', username_splice_and_fix(msg['new_chat_participant'])),
						parse_mode='Markdown', disable_web_page_preview=True, reply_to_message_id=msg['message_id']).get('message_id')
					self.cache.write(self.external_store)

			elif content_type == 'text' and msg['text'][0] == '/':
				get_result = self.gcache.get(chat_id)
				result = botcommand_match.match(msg['text'])
				try:
					EntryCheck = 'entities' in msg and len(msg['entities']) > 0 and \
						msg['entities'][0]['type'] == 'bot_command'
				except IndexError:
					EntryCheck = False
					Log.warn('Catched IndexError, msg={}', repr(msg))

				if EntryCheck:
					if get_result['noblue'] and \
						(not result or result.group(1) not in self.gcache.get(chat_id)['except']):
						delete_target_message(chat_id, msg['message_id']).start()

					# Match bot command check
					if command_match.match(msg['text']) or noparmcommand_match.match(msg['text']):

						if msg['from']['id'] == Config.bot.owner:
							result = re.match(r'^\/d( (-?\d+))?$', msg['text'])
							if result:
								operid = chat_id if result.group(1) is None else result.group(2)
								self.gcache.delete(operid)
								self.gcache.add((operid, None, 0, 1, 0, 0, b64encode(repr([]))), not_found=True)
								delete_target_message(chat_id,
									self.sendMessage(chat_id, 'Operaction completed!', 
										reply_to_message_id=msg['message_id'])['message_id']).start()
								return

							result = re.match(r'^\/l$', msg['text'])
							if result:
								self.bot.leaveChat(chat_id)
								return

							result = setflag2command_match.match(msg['text'])
							if result:
								if str(result.group(2)) in flag_type:
									self.gcache.editflag((chat_id,str(result.group(2)),int(result.group(3))))
									delete_target_message(chat_id, self.sendMessage(chat_id, 'Operation completed!',
										reply_to_message_id=msg['message_id'])['message_id']).start()

						# Match /poem command
						result = poemcommand_match.match(msg['text'])
						if result:
							if get_result['poemable']:
								result = self.pcache.get()
								if not result:
									result = b64encode('TBD')
								self.bot.sendChatAction(chat_id, 'typing')
								time.sleep(3)
								self.sendMessage(chat_id, b64decode(result),
									reply_to_message_id=msg['message_id'])
								return
							elif not get_result['ignore_err']:
								self.sendMessage(chat_id, 'Permission Denied.\n*你没有资格念他的诗，你给我出去*',
										parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							return

						# Other command need admin privilege, check it.
						if self.getChatMember(chat_id, msg['from']['id'])['status'] not in admin_type:
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
							self.sendMessage(chat_id, "*Clear welcome message completed!*",
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])['message_id']
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
							self.sendMessage(chat_id, "*Reload configuration and poem completed!*",
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])
							return

						# Match /setflag command
						result = setflagcommand_match.match(msg['text'])
						'''
							result.group(2) is `flag name',
							result.group(3) is `flag value'
						'''
						if result:
							self.bot.sendChatAction(chat_id, 'typing')
							if str(result.group(2)) not in flag_type:
								if not get_result['ignore_err']:
									self.sendMessage(chat_id, "*Error*: Flag \"%s\" not exist"%str(result.group(2)),
										parse_mode='Markdown', reply_to_message_id=msg['message_id'])
								return
							self.gcache.editflag((chat_id, str(result.group(2)), int(result.group(3))))
							delete_target_message(chat_id, self.sendMessage(chat_id, "*Set flag \"%s\" to \"%d\" success!*"%(str(result.group(2)), int(result.group(3))),
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])['message_id']).start()
							return

						result = exceptcommand_match.match(msg['text'])
						if result:
							if result.group(1) == 'd':
								if self.gcache.except_(chat_id, result.group(3), True):
									sendMessage_and_delete(chat_id, 'Delete except command success', msg['message_id'])
								else:
									sendMessage_and_delete(chat_id, 'Delete except command fail. (Is command in except list? Tips: try using /status to see more)', msg['message_id'])
							else:
								if self.gcache.except_(chat_id, result.group(3)):
									sendMessage_and_delete(chat_id, 'Add except command success', msg['message_id'])
								else:
									sendMessage_and_delete(chat_id, 'Add except command fail with excpet list too long.', msg['message_id'])
							return

						# Match /status command
						if statuscommand_match.match(msg['text']):
							delete_target_message(chat_id, self.sendMessage(chat_id, gen_status_msg(self.gcache.get(chat_id)), reply_to_message_id=msg['message_id'])['message_id']).start()
							return

						# Finally match /ping
						if pingcommand_match.match(msg['text']):
							delete_target_message(chat_id, self.sendMessage(chat_id, '*Current chat_id:* `{}`\n*Your id:* `{}`\n*Bot runtime: {}\nSystem load avg: {}*'.format(
								chat_id, msg['from']['id'], Log.get_runtime(), getloadavg()),
								parse_mode='Markdown', reply_to_message_id=msg['message_id'])['message_id'], 10)

			elif content_type in service_msg_type and self.gcache.get(chat_id)['other']['no_service_msg']:
				delete_target_message(chat_id, msg['message_id'], 0).start()