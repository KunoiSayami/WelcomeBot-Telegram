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
import struct
import time
from dataclasses import dataclass

import asyncpg

from libpy3.aiopgsqldb import PgSQLdb

DATABASE_CURRENT_VERSION = 1
PACK_FORMAT = "<h????????"


class GroupAdmins:
    def __init__(self):
        self._admins_list: list[int] | None = None
        self._last_fetch: float = 0.0

    @property
    def admins_list(self) -> list[int] | None:
        if time.time() - self._last_fetch > 120:
            return None
        return self._admins_list

    @admins_list.setter
    def admins_list(self, value: list[int]) -> None:
        del self._admins_list
        self._admins_list = value
        self._last_fetch = time.time()


@dataclass(init=False)
class GroupProperty:
    welcome_text: str | None
    no_welcome: bool
    no_service_msg: bool
    no_new_member: bool
    no_blue: bool
    ignore_err: bool
    poemable: bool
    no_channel: bool
    no_channel_msg: bool

    def __init__(
        self,
        text: str | None,
        no_welcome: bool,
        no_service_msg: bool,
        no_new_member: bool,
        no_blue: bool,
        ignore_err: bool,
        poemable: bool,
        no_channel: bool,
        no_channel_msg: bool,
    ):
        self.welcome_text: str | None = text
        self.no_welcome: bool = no_welcome
        self.no_service_msg: bool = no_service_msg
        self.no_new_member: bool = no_new_member
        self.no_blue: bool = no_blue
        self.ignore_err: bool = ignore_err
        self.poemable: bool = poemable
        self.no_channel: bool = no_channel
        self.no_channel_msg: bool = no_channel_msg
        self._admins_list: GroupAdmins = GroupAdmins()

    @property
    def admins(self) -> list[int] | None:
        return self._admins_list.admins_list

    @admins.setter
    def admins(self, value: list[int]) -> None:
        self._admins_list.admins_list = value

    @classmethod
    def unpack(cls, welcome_text: str, data: bytes) -> "GroupProperty":
        version, = struct.unpack("<h", data[:2])
        if version != DATABASE_CURRENT_VERSION:
            raise ValueError(
                f"except version {DATABASE_CURRENT_VERSION} but {version} found"
            )
        (
            _,
            no_welcome,
            no_service_msg,
            no_new_member,
            no_blue,
            ignore_err,
            poemable,
            no_channel,
            no_channel_msg,
        ) = struct.unpack(PACK_FORMAT, data)
        return cls(
            welcome_text,
            no_welcome,
            no_service_msg,
            no_new_member,
            no_blue,
            ignore_err,
            poemable,
            no_channel,
            no_channel_msg,
        )

    def pack(self) -> bytes:
        return struct.pack(
            PACK_FORMAT,
            DATABASE_CURRENT_VERSION,
            self.no_welcome,
            self.no_service_msg,
            self.no_new_member,
            self.no_blue,
            self.ignore_err,
            self.poemable,
            self.no_channel,
            self.no_channel_msg,
        )


class PostgreSQL(PgSQLdb):
    async def insert_last_message_id(self, chat_id: int, message_id: int) -> None:
        await self.execute(
            """UPDATE "welcome_msg" SET "previous_msg_id" = $1 WHERE "group_id" = $2""",
            message_id,
            chat_id,
        )

    async def query_last_message_id(self, chat_id: int) -> int:
        return (
            await self.query1(
                """SELECT "previous_msg_id" FROM "welcome_msg" WHERE "group_id" = $1""",
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

    def __getitem__(self, key: int) -> GroupProperty | None:
        return self.groups.get(key)

    @staticmethod
    def get_group_property_from_dict(d: asyncpg.Record) -> GroupProperty:
        return GroupProperty.unpack(d["msg"], d["flags"])

    async def insert_group(self, chat_id: int) -> GroupProperty:
        await self.update_group(
            chat_id,
            GroupProperty(None, False, False, False, False, True, False, False, False),
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
                                    ("group_id", "msg", "flags") 
                                    VALUES ($1, $2, $3)""",
                chat_id,
                new_property.welcome_text,
                new_property.pack(),
            )  # type: ignore
        else:
            await self.conn.execute(
                """UPDATE "welcome_msg" 
                                    SET "msg" = $1, "flags" = $2  WHERE "group_id" = $3""",
                new_property.welcome_text,
                new_property.pack(),
                chat_id,
            )  # type: ignore

    async def delete_group(self, chat_id: int) -> None:
        await self.conn.execute("""DELETE FROM "welcome_msg" WHERE "group_id" = $1""", chat_id)  # type: ignore
