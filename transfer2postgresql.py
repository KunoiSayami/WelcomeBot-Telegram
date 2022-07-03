#!/usr/bin/env python
# -*- coding: utf-8 -*-
# transfer2postgresql.py
# Copyright (C) 2022 KunoiSayami
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
import aiomysql
import asyncio
from configparser import ConfigParser

import asyncpg
from typing import Callable, Tuple, Union, Any

config = ConfigParser()
config.read("data/config.ini")
host = config.get("database", "host")
port = config.get("pgsql", "port")  # only for pgsql
muser = config.get("database", "user")
mpasswd = config.get("database", "password")
puser = config.get("pgsql", "user")
ppasswd = config.get("pgsql", "password")
mdatabase = config.get("database", "db")
pdatabase = config.get("pgsql", "database")


async def main() -> None:
    pgsql_connection = await asyncpg.connect(
        host=host, port=port, user=puser, password=ppasswd, database=pdatabase
    )
    mysql_connection = await aiomysql.create_pool(
        host=host,
        user=muser,
        password=mpasswd,
        db=mdatabase,
        charset="utf8mb4",
        cursorclass=aiomysql.cursors.Cursor,
    )
    if input("Do you want to delete all data? [y/N]: ").strip().lower() == "y":
        await clean(pgsql_connection)
        print("Clear database successfully")
    else:
        print("Skipped clear database")
    async with mysql_connection.acquire() as conn:
        async with conn.cursor() as cursor:
            await exec_and_insert(
                cursor,
                "SELECT * FROM poem",
                pgsql_connection,
                """INSERT INTO poem VALUES ($1)""",
            )
            await exec_and_insert(
                cursor,
                "SELECT * FROM welcomemsg",
                pgsql_connection,
                """INSERT INTO "welcome_msg" VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                transfer,
            )
    await pgsql_connection.close()
    mysql_connection.close()
    await mysql_connection.wait_closed()


def transfer(obj: Tuple[int, str, str, str]) -> Tuple[Union[bool, Any], ...]:
    def str2bool(x: str) -> bool:
        return True if x == "Y" else False

    return tuple(
        map(lambda x: str2bool(x) if isinstance(x, str) and x in ["Y", "N"] else x, obj)
    )


async def exec_and_insert(
    cursor,
    sql: str,
    pg_connection,
    insert_sql: str,
    process: Callable[[Any], Any] = None,
) -> None:
    print("Processing table:", sql[13:])
    try:
        if await pg_connection.fetchrow(f"{sql} LIMIT 1") is not None:
            if (
                input(
                    f"Table {sql[13:]} has data, do you still want to process insert? [y/N]: "
                )
                .strip()
                .lower()
                != "y"
            ):
                return
    except:
        pass
    await cursor.execute(sql)
    obj = await cursor.fetchall()
    for sql_obj in obj:
        if process is not None:
            sql_obj = process(sql_obj)
        await pg_connection.execute(insert_sql, *sql_obj)


async def clean(pgsql_connection: asyncpg.connection) -> None:
    await pgsql_connection.execute('''TRUNCATE "poem"''')
    await pgsql_connection.execute('''TRUNCATE "welcome_msg"''')


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
