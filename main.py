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

class group_cache_class:
	def __init__(self):
		self.g = dict()
	def load(self):
		self.__init__()
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		result = sql.query("SELECT * FROM `welcomemsg`")
		sql.close()
		for x in result:
			self.add(x)
	def add(self,x):
		global bot_id
		try:
			self.g[x[0]]={'msg' : x[1] , 'is_admin' : 
				self.__check_admin(bot.getChatMember(x[0],bot_id)['status'])}
			return self.g[x[0]]['is_admin']
		except telepot.exception.BotWasKickedError:
			self.__db_del(x[0])
			print('Delete kicked chat:%d'%x[0])
			return -1
		except telepot.exception.TelegramError as e:
			if e[0] == 'Bad Request: chat not found':
				self.__db_del(x[0])
				print('Delete not found chat:%d'%x[0])
			else:
				raise e
			return -1
	def delete(self,chat_id):
		try:
			del self.g[chat_id]
			self.__db_del(chat_id)
		except KeyError:
			print('Can\'t find %d in delete()'%chat_id)
	def get(self,chat_id):
		try:
			return self.g[chat_id]
		except KeyError:
			print('Can\'t find %d in get()'%chat_id)
			return {'msg':None}
	def __db_del(self,chat_id):
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		sql.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %d"%(chat_id))
		sql.close()
	def __check_admin(self,status):
		if status in admin_type:
			return 1
		else:
			return 0
	def get_is_admin(self,chat_id):
		if self.get(chat_id)['is_admin'] == 1:
			return True
		else:
			return False
	def edit(self,x):
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		if x[1]:
			sql.execute("UPDATE `welcomemsg` SET `msg` = '%s' WHERE `group_id` = %d"%(x[1],x[0]))
		else:
			sql.execute("UPDATE `welcomemsg` SET `msg` = NULL WHERE `group_id` = %d"%x[0])
		sql.close()
		self.g[x[0]]['msg'] = x[1]


def onMessage(msg):	
	global bot
	content_type, chat_type, chat_id = telepot.glance(msg)
	if content_type == 'new_chat_member' and msg['new_chat_participant']['id'] == bot_id:
		is_admin = group_cache.add((chat_id,None))
		assert(is_admin != -1)
		sql = mm(sqlhost,sqlport,sqluser,sqlpwd,sqlname)
		sql.execute("INSERT INTO `welcomemsg` (`group_id`,`msg`,`is_admin`) VALUES (%d,NULL,%d)"%(chat_id,is_admin))
		sql.close()
		return
	if content_type == 'left_chat_member' and msg['left_chat_member']['id'] == bot_id:
		group_cache.delete(chat_id)
		return
	if msg['chat']['type'] in group_type:
		if content_type=='text' and msg['text'][0] =='/' and command_match.match(msg['text']):
			if bot.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
				bot.sendMessage(chat_id,'Permission Denied.\n你没有权限，快滚',
					reply_to_message_id=msg['message_id'])
				if group_cache.get_is_admin(chat_id):
					bot.restrictChatMember(chat_id,msg['from']['id'],until_date=msg['date']+60)
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
					bot.sendMessage(chat_id,"*Error*:Welcome message is too long.(len() must smaller than 4096)",
						parse_mode='Markdown',reply_to_message_id=msg['message_id'])
					return
				group_cache.edit((chat_id,b64encode(welcomemsg)))
				bot.sendMessage(chat_id,"*Set welcome message to:*\n%s"%welcomemsg,
					disable_web_page_preview=True,parse_mode='Markdown',reply_to_message_id=msg['message_id'])
				return
			result = clearcommand_match.match(msg['text'])
			if result:
				group_cache.edit((chat_id,None))
				bot.sendMessage(chat_id,"*Clear welcome message successfully!*",
					parse_mode='Markdown',reply_to_message_id=msg['message_id'])
				return
			result = reloadcommand_match.match(msg['text'])
			if result:
				group_cache.load()
				bot.sendMessage(chat_id,"*Reload configuration successfully!*",
					parse_mode='Markdown',reply_to_message_id=msg['message_id'])
				return
			bot.sendMessage(chat_id,'*Current chat_id:%d\nYour id:%d*'%(chat_id,msg['from']['id']),
				parse_mode='Markdown',reply_to_message_id=msg['message_id'])
		elif content_type in content_type_concerned:
			result = group_cache.get(chat_id)['msg']
			if result:
				bot.sendMessage(chat_id,b64decode(result),parse_mode='Markdown',
					disable_web_page_preview=True,reply_to_message_id=msg['message_id'])

def main():
	global bot,group_cache,bot_id
	print('Start Main()')
	bot = telepot.Bot(botToken)
	print('Success login with token %s***********************%s'%(botToken[:4],botToken[-4:]))
	bot.message_loop(onMessage)
	print('message_loop() started\nGet bot id....')
	bot_id = bot.getMe()['id']
	group_cache = group_cache_class()
	group_cache.load()
	print('bot init finished')
	while True:
		bot.getMe()
		time.sleep(10)

def init():
	reload(sys)
	sys.setdefaultencoding('utf8')

if __name__ == '__main__':
	init()
	main()