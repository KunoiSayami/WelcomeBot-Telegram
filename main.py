# -*- coding: utf-8 -*-
#
#This source code was published under GPL v3
#
#Copyright (C) 2017 Too-Naive
#
import telepot
import time
import sys
from config import botToken,sqlhost,sqlport,sqluser,sqlpwd,sqlname
from mysqlmodule import mysqlModule as mm
from base64 import b64encode,b64decode
import re,urllib2


bot = None
bot_id = 0

command_match = re.compile(r'^\/(clear|setwelcome|ping|reload)(@[a-zA-Z_]*bot)?')
setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
clearcommand_match = re.compile(r'^\/clear(@[a-zA-Z_]*bot)?$')
reloadcommand_match = re.compile(r'^\/reload(@[a-zA-Z_]*bot)?$')

content_type_concerned = ['new_chat_member']
group_type = ['group','supergroup']
admin_type = ['creator','administrator']

group_cache = None

class group_list:
	def __init__(self):
		self.group_id = []
		self.group_msg = []
		self.is_admin = []
	def append(self,x):
		global bot,bot_id
		self.group_id.append(x[0])
		self.group_msg.append(x[1])
		#self.is_admin.append(x[2])
		self.is_admin.append(self.__check_admin(bot.getChatMember(x[0],bot_id)['status']))
		return self.is_admin[:-1]
	def delete(self,chat_id):
		index = self.find_group_index(chat_id)
		del self.group_id[index]
		del self.group_msg[index]
		del self.is_admin[index]
	def find_group_index(self,chat_id):
		for x in xrange(0,len(self.group_id)):
			if self.group_id[x] == chat_id:
				return x
		return -1
	def check_admin(self,chat_id):
		index = self.find_group_index(chat_id)
		assert(index != -1)
		if self.is_admin[index] == 1:
			return True
		else:
			return False

class group_cache_class:
	def __init__(self):
		self.l = group_list()
	def load(self):
		self.__init__()
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		result = sql.query("SELECT * FROM `welcomemsg`")
		sql.close()
		for x in result:
			self.l.append(x)
	def getmsg(self,chat_id):
		pass
	def __check_admin(self,status):
		if status in admin_type:
			return 1
		else:
			return 0

def onMessage(msg):	
	global bot
	content_type, chat_type, chat_id = telepot.glance(msg)
	print(content_type)
	print(msg)
	if content_type = 'new_chat_member' and msg['new_chat_members']['id'] == bot_id:
		is_admin = group_cache.append((chat_id,None))
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		sql.execute("INSERT INTO `welcomemsg` (`group_id`,`msg`,`is_admin`) VALUES (%d,NULL,%d)"%(chat_id,is_admin))
		sql.close()
		return
	if content_type = 'left_chat_member' and msg['left_chat_member']['id'] == bot_id:
		group_cache.delete(chat_id)
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		sql.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %d"%(chat_id))
		sql.close()
		return
	if msg['chat']['type'] in group_type:
		if content_type=='text' and command_match.match(msg['text']):
			if bot.getChatMember(chat_id,bot.getMe()['id'])['status'] in admin_type:
				if bot.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
					bot.sendMessage(chat_id,'Permission Denied.\n你没有权限，快滚',
						reply_to_message_id=msg['message_id'])
					bot.restrictChatMember(chat_id,msg['from']['id'],until_date=msg['date']+60)
					return
			if bot.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
				bot.sendMessage(chat_id,'Permission Denied.\n你没有权限，快滚',
					reply_to_message_id=msg['message_id'])
				if group_cache.find_group_index()
			result = setcommand_match.match(msg['text'])
			if result:
				welcomemsg = str(result.group(2))
				result = gist_match.match(welcomemsg)
				if result:
					r = urllib2.urlopen(welcomemsg)
					welcomemsg = r.read()
					r.close()
				sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
				result = sql.query("SELECT * FROM `welcomemsg` WHERE `group_id` = %d"%chat_id)
				if not result:
					sql.execute("INSERT INTO `welcomemsg` (`group_id`,`msg`) VALUES (%d,'%s')"%(chat_id,b64encode(welcomemsg)))
				else:
					sql.execute("UPDATE `welcomemsg` SET `msg` = '%s' WHERE `group_id` = %d"%(b64encode(welcomemsg),chat_id))
				sql.close()
				bot.sendMessage(chat_id,"*Set welcome message to:*\n%s"%welcomemsg,
					disable_web_page_preview=True,parse_mode='Markdown',reply_to_message_id=msg['message_id'])
				return
			result = clearcommand_match.match(msg['text'])
			if result:
				sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
				result = sql.query("SELECT * FROM `welcomemsg` WHERE `group_id` = %d"%chat_id)
				if result:
					sql.execute("UPDATE `welcomemsg` SET `msg` = NULL WHERE `group_id` = %d"%chat_id)
				sql.close()
				bot.sendMessage(chat_id,"*Clear welcome message success!*",
					parse_mode='Markdown',reply_to_message_id=msg['message_id'])
				return
			result = reloadcommand_match.match(msg['text'])
			if result:

		elif content_type in content_type_concerned:
			sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
			result = sql.query("SELECT `msg` FROM `welcomemsg` WHERE `group_id` = %d"%chat_id)
			sql.close()
			if result:
				bot.sendMessage(chat_id,b64decode(result[0][0]),parse_mode='Markdown',
					disable_web_page_preview=True,reply_to_message_id=msg['message_id'])

def main():
	global bot,group_cache,bot_id
	bot = telepot.Bot(botToken)
	bot.message_loop(onMessage)
	bot_id = bot.getMe()['id']
	group_cache = group_cache_class()
	group_cache.load()
	while True:
		bot.getMe()
		time.sleep(10)

def init():
	reload(sys)
	sys.setdefaultencoding('utf8')

if __name__ == '__main__':
	init()
	main()