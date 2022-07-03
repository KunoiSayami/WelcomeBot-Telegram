# -*- coding: utf-8 -*-
# cache.py
# Copyright (C) 2017-2022 KunoiSayami
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
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from libpy3.aiopgsqldb import PgSQLdb


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
    def admins_list(self, value: List[int]) -> None:
        del self._admins_list
        self._admins_list = value
        self._last_fetch = time.time()


@dataclass(init=False)
class GroupProperty:
    welcome_text: Optional[str]
    no_welcome: bool
    no_service_msg: bool
    no_new_member: bool
    no_blue: bool
    ignore_err: bool

    def __init__(
        self,
        text: Optional[str],
        no_welcome: bool,
        no_service_msg: bool,
        no_new_member: bool,
        no_blue: bool,
        ignore_err: bool,
    ):
        self.welcome_text: Optional[str] = text
        self.no_welcome: bool = no_welcome
        self.no_service_msg: bool = no_service_msg
        self.no_new_member: bool = no_new_member
        self.no_blue: bool = no_blue
        self.ignore_err: bool = ignore_err
        self._admins_list: GroupAdmins = GroupAdmins()

    @property
    def admins(self) -> Optional[List[int]]:
        return self._admins_list.admins_list

    @admins.setter
    def admins(self, value: List[int]) -> None:
        self._admins_list.admins_list = value


class PostgreSQL(PgSQLdb):
    async def insert_last_message_id(self, chat_id: int, message_id: int) -> None:
        await self.execute(
            """UPDATE "welcome_msg" SET "previous_msg" = $1 WHERE "group_id" = $2""",
            message_id,
            chat_id,
        )

    async def query_last_message_id(self, chat_id: int) -> int:
        return (
            await self.query1(
                """SELECT "previous_msg" FROM "welcome_msg" WHERE "group_id" = $1""",
                chat_id,
            )
        )["previous_msg"]


# FIXME: using redis instead built-in dict
class GroupCache:
    def __init__(self, conn: PostgreSQL):
        self.conn = conn
        self.groups = {}

    @classmethod
    async def create(cls, conn: PostgreSQL) -> "GroupCache":
        self = GroupCache(conn)
        await self.read_database()
        return self

    async def read_database(self) -> None:
        sql_obj = await self.conn.query(
            """SELECT * FROM "welcome_msg" WHERE "available" = true"""
        )
        for x in sql_obj:
            self.groups.update({x["group_id"]: self.get_group_property_from_dict(x)})

    def __getitem__(self, key: int) -> Optional[GroupProperty]:
        return self.groups.get(key)

    @staticmethod
    def get_group_property_from_dict(d: Dict[str, Union[bool, str]]) -> GroupProperty:
        return GroupProperty(
            d["msg"],
            d["no_welcome"],
            d["no_service"],
            d["no_new_member"],
            d["no_blue"],
            d["ignore_err"],
        )

    async def insert_group(self, chat_id: int) -> GroupProperty:
        await self.update_group(
            chat_id, GroupProperty(None, False, False, False, False, True)
        )
        return self.groups[chat_id]

    async def update_group(
        self, chat_id: int, new_property: GroupProperty, no_update: bool = False
    ) -> None:
        self.groups.update({chat_id: new_property})
        if no_update:
            return
        if (
            await self.conn.query1(
                """SELECT 1 FROM "welcome_msg" WHERE "group_id" = $1""", chat_id
            )
            is None
        ):  # type: ignore
            await self.conn.execute(
                """INSERT INTO "welcome_msg" 
                                    ("group_id", "msg", "ignore_err", "no_blue", "no_service", 
                                    "no_welcome", "no_new_member") 
                                    VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                chat_id,
                new_property.welcome_text,
                new_property.ignore_err,
                new_property.no_blue,
                new_property.no_service_msg,
                new_property.no_welcome,
                new_property.no_new_member,
            )  # type: ignore
        else:
            await self.conn.execute(
                """UPDATE "welcome_msg" 
                                    SET "msg" = $1, "ignore_err" = $2, "no_blue" = $3, "no_service" = $4, 
                                    "no_welcome" = $5, "no_new_member" = $6 WHERE "group_id" = $7""",
                new_property.welcome_text,
                new_property.ignore_err,
                new_property.no_blue,
                new_property.no_service_msg,
                new_property.no_welcome,
                new_property.no_new_member,
                chat_id,
            )  # type: ignore

    async def delete_group(self, chat_id: int) -> None:
        await self.conn.execute("""DELETE FROM "welcome_msg" WHERE "group_id" = $1""", chat_id)  # type: ignore
