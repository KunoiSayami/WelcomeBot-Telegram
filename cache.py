# -*- coding: utf-8 -*-
# cache.py
# Copyright (C) 2017-2019 KunoiSayami
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
from pyrogram import Client
from libpy3.mysqldb import mysqldb

class group_property:
	def __init__(self, text: str, no_welcome: bool, no_service_msg: bool,
	             no_new_member: bool, no_blue: bool, ignore_err: bool):
		self._welcome_text = text
		self._no_welcome = no_welcome
		self._no_service_msg = no_service_msg
		self._no_new_member = no_new_member
		self._no_blue = no_blue
		self._ignore_err = ignore_err
		self._admins_list = []
		self.last_fetch = 0

	@property
	def no_welcome(self) -> bool:
		return self._no_welcome

	@property
	def no_service_msg(self) -> bool:
		return self._no_service_msg

	@property
	def no_blue(self) -> bool:
		return self._no_blue

	@property
	def no_new_member(self) -> bool:
		return self._no_new_member

	@property
	def ignore_err(self) -> bool:
		return self.ignore_err

	@no_welcome.setter
	def no_welcome(self, value: bool):
		self._no_welcome = value

	@no_service_msg.setter
	def no_service_msg(self, value: bool):
		self._no_service_msg = value

	@no_blue.setter
	def no_blue(self, value: bool):
		self._no_blue = value

	@no_new_member.setter
	def no_new_member(self, value: bool):
		self._no_new_member = value

	@ignore_err.setter
	def ignore_err(self, value: bool):
		self._ignore_err = value

	@property
	def welcome_text(self):
		return self._welcome_text

	@welcome_text.setter
	def welcome_text(self, value: str):
		self._welcome_text = value


class group_cache:
	def __init__(self, conn: mysqldb, client: Client):
		self.conn = conn
		self.client = client
		self.groups = {}
	@staticmethod
	def __transform_to_bool(s: str) -> bool:
		return s == 'Y'

	@staticmethod
	def __transform_from_bool(s: bool) -> str:
		return 'Y' if s else 'M'

	def read_database(self):
		sqlObj = self.conn.query("SELECT * FROM `welcomemsg` WHERE `available` = 'Y'")
		for x in sqlObj:
			self.groups.update({x['group_id'], self.get_group_property_from_dict(x)})

	def __getitem__(self, key: int):
		return self.groups.get(key, None)

	@staticmethod
	def get_group_property_from_dict(d: dict) -> group_property:
		return group_property(
				#b64decode(x['msg'].encode()).decode(),
				d['msg'],
				group_cache.__transform_to_bool(d['no_welcome']),
				group_cache.__transform_to_bool(d['no_service']),
				group_cache.__transform_to_bool(d['no_new_member']),
				group_cache.__transform_to_bool(d['no_blue']),
				group_cache.__transform_to_bool(d['ignore_err'])
				)

	def insert_group(self, chat_id: int) -> group_property:
		#if chat_id in self.groups: return self.groups[chat_id]
		#sqlObj = self.conn.query1("SELECT * FROM `welcomemsg` WHERE `group_id` = %s", chat_id)
		#if sqlObj is not None:
		#	self.update_group(chat_id, self.get_group_property_from_dict(sqlObj))
		self.update_group(chat_id, group_property(None, False, False, False, False, True))
		return self.groups[chat_id]

	def update_group(self, chat_id: int, new_property: group_property, no_update: bool = False):
		self.groups.update({chat_id: new_property})
		if no_update: return
		if self.conn.query1("SELECT 1 FROM `welcomemsg` WHERE `group_id` = %s", chat_id) is None:
			self.conn.execute("INSERT INTO `welcomemsg` (`group_id`, `msg`, `ignore_err`, `no_blue`, `no_service`, `no_welcome`, `no_new_member`) VALUE (%s, %s, %s, %s, %s, %s, %s)",
				(
					chat_id,
					new_property.welcome_text,
					self.__transform_from_bool(new_property.ignore_err),
					self.__transform_from_bool(new_property.no_blue),
					self.__transform_from_bool(new_property.no_service_msg),
					self.__transform_from_bool(new_property.no_welcome),
					self.__transform_from_bool(new_property.no_new_member)
				))
		else:
			self.conn.execute("UPDATE `welcomemsg` SET `msg` = %s, `ignore_err` = %s, `no_blue` = %s, `no_service` = %s, `no_welcome` = %s, `no_new_member` = %s WHERE `group_id` = %s",
				(
					new_property.welcome_text,
					self.__transform_from_bool(new_property.ignore_err),
					self.__transform_from_bool(new_property.no_blue),
					self.__transform_from_bool(new_property.no_service_msg),
					self.__transform_from_bool(new_property.no_welcome),
					self.__transform_from_bool(new_property.no_new_member),
					chat_id
				))

	def delete_group(self, chat_id: int):
		#if self.groups.pop(chat_id, None) is not None:
		self.conn.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %s", chat_id)
