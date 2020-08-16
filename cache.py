# -*- coding: utf-8 -*-
# cache.py
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
import time
from typing import Dict, List, Optional

from libpy3.aiomysqldb import MySqlDB


class GroupAdmins:
	def __init__(self):
		self._admins_list: Optional[List[int]] = None
		self._last_fetch: float = 0.0

	@property
	def admins_list(self) -> Optional[List[int]]:
		if time.time() - self._last_fetch > 120:
			return None
		return self._admins_list

	@admins_list.setter
	def admins_list(self, value: List[int]) -> List[int]:
		del self._admins_list
		self._admins_list = value
		self._last_fetch = time.time()
		return self._admins_list

class GroupProperty:
	def __init__(self, text: Optional[str], no_welcome: bool, no_service_msg: bool,
	             no_new_member: bool, no_blue: bool, ignore_err: bool):
		self._welcome_text: Optional[str] = text
		self._no_welcome: bool = no_welcome
		self._no_service_msg: bool = no_service_msg
		self._no_new_member: bool = no_new_member
		self._no_blue: bool = no_blue
		self._ignore_err: bool = ignore_err
		self._admins_list: GroupAdmins = GroupAdmins()

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
		return self._ignore_err

	@no_welcome.setter
	def no_welcome(self, value: bool) -> None:
		self._no_welcome = value

	@no_service_msg.setter
	def no_service_msg(self, value: bool) -> None:
		self._no_service_msg = value

	@no_blue.setter
	def no_blue(self, value: bool) -> None:
		self._no_blue = value

	@no_new_member.setter
	def no_new_member(self, value: bool) -> None:
		self._no_new_member = value

	@ignore_err.setter
	def ignore_err(self, value: bool) -> None:
		self._ignore_err = value

	@property
	def welcome_text(self) -> Optional[str]:
		return self._welcome_text

	@welcome_text.setter
	def welcome_text(self, value: str) -> None:
		self._welcome_text = value

	@property
	def last_fetch(self) -> float:
		return self._last_fetch

	@last_fetch.setter
	def last_fetch(self, value: float) -> float:
		self._last_fetch = value
		return value

	@property
	def admins(self) -> Optional[List[int]]:
		return self._admins_list.admins_list

	@admins.setter
	def admins(self, value: List[int]) -> List[int]:
		self._admins_list.admins_list = value
		return value

# FIXME: using redis instead built-in dict
class GroupCache:
	def __init__(self, conn: MySqlDB):
		self.conn = conn
		self.groups = {}

	@classmethod
	async def create(cls, conn: MySqlDB):
		self = GroupCache(conn)
		await self.read_database()
		return self

	@staticmethod
	def _str2bool(s: str) -> bool:
		return s == 'Y'

	@staticmethod
	def _bool2str(s: bool) -> str:
		return 'Y' if s else 'N'

	async def read_database(self) -> None:
		sqlObj = await self.conn.query("SELECT * FROM `welcomemsg` WHERE `available` = 'Y'")
		for x in sqlObj:
			self.groups.update({x['group_id']: self.get_group_property_from_dict(x)})

	def __getitem__(self, key: int) -> Optional[GroupProperty]:
		return self.groups.get(key)

	@staticmethod
	def get_group_property_from_dict(d: Dict[str, str]) -> GroupProperty:
		return GroupProperty(
				#b64decode(x['msg'].encode()).decode(),
				d['msg'],
				GroupCache._str2bool(d['no_welcome']),
				GroupCache._str2bool(d['no_service']),
				GroupCache._str2bool(d['no_new_member']),
				GroupCache._str2bool(d['no_blue']),
				GroupCache._str2bool(d['ignore_err'])
				)

	async def insert_group(self, chat_id: int) -> GroupProperty:
		#if chat_id in self.groups: return self.groups[chat_id]
		#sqlObj = self.conn.query1("SELECT * FROM `welcomemsg` WHERE `group_id` = %s", chat_id)
		#if sqlObj is not None:
		#	self.update_group(chat_id, self.get_group_property_from_dict(sqlObj))
		await self.update_group(chat_id, GroupProperty(None, False, False, False, False, True))
		return self.groups[chat_id]

	async def update_group(self, chat_id: int, new_property: GroupProperty, no_update: bool=False) -> None:
		self.groups.update({chat_id: new_property})
		if no_update: return
		if await self.conn.query1("SELECT 1 FROM `welcomemsg` WHERE `group_id` = %s", chat_id) is None:  # type: ignore
			await self.conn.execute("INSERT INTO `welcomemsg` (`group_id`, `msg`, `ignore_err`, `no_blue`, `no_service`, `no_welcome`, `no_new_member`) VALUE (%s, %s, %s, %s, %s, %s, %s)",
				(
					chat_id,
					new_property.welcome_text,
					self._bool2str(new_property.ignore_err),
					self._bool2str(new_property.no_blue),
					self._bool2str(new_property.no_service_msg),
					self._bool2str(new_property.no_welcome),
					self._bool2str(new_property.no_new_member)
				)) # type: ignore
		else:
			await self.conn.execute("UPDATE `welcomemsg` SET `msg` = %s, `ignore_err` = %s, `no_blue` = %s, `no_service` = %s, `no_welcome` = %s, `no_new_member` = %s WHERE `group_id` = %s",
				(
					new_property.welcome_text,
					self._bool2str(new_property.ignore_err),
					self._bool2str(new_property.no_blue),
					self._bool2str(new_property.no_service_msg),
					self._bool2str(new_property.no_welcome),
					self._bool2str(new_property.no_new_member),
					chat_id
				)) # type: ignore

	async def delete_group(self, chat_id: int) -> None:
		#if self.groups.pop(chat_id, None) is not None:
		await self.conn.execute("DELETE FROM `welcomemsg` WHERE `group_id` = %s", chat_id)  # type: ignore
