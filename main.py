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

def main():
	global bot
	bot = telepot.Bot(botToken)
	bot.message_loop(onMessage)
	while True:
		bot.getMe()
		time.sleep(10)


def init():
	reload(sys)
	sys.setdefaultencoding('utf8')

command_match = re.compile(r'^\/(clear|setwelcome|ping|reload)(@[a-zA-Z_]*bot)?')
setcommand_match = re.compile(r'^\/setwelcome(@[a-zA-Z_]*bot)?\s((.|\n)*)$')
gist_match = re.compile(r'^https:\/\/gist.githubusercontent.com\/.+\/[a-z0-9]{32}\/raw\/[a-z0-9]{40}\/.*$')
clearcommand_match = re.compile(r'^\/clear(@[a-zA-Z_]*bot)?$')
reloadcommand_match = re.compile(r'^\/reload(@[a-zA-Z_]*bot)?$')

content_type_concerned = ["new_chat_member"]
group_type = ['group','supergroup']
admin_type = ['creator','administrator']

groupcache = []

def onMessage(msg):
	global bot
	content_type, chat_type, chat_id = telepot.glance(msg)
	#if content_type in content_type_concerned:
	if msg['chat']['type'] in group_type:
		if content_type=='text' and command_match.match(msg['text']):
			if bot.getChatMember(chat_id,bot.getMe()['id'])['status'] in admin_type:
				if bot.getChatMember(chat_id,msg['from']['id'])['status'] not in admin_type:
					bot.sendMessage(chat_id,'Permission Denied.\n你没有权限，快滚',
						reply_to_message_id=msg['message_id'])
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
'''
			if bot.getChatMember(chat_id,msg['from']['id'])['status'] == "member":
				bot.restrictChatMember(chat_id,msg['from']['id'])
				bot.deleteMessage((chat_id,msg['message_id']))
'''

if __name__ == '__main__':
	init()
	main()