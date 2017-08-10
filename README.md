# Telegram Welcome bot

A bot can receive new chat member then show the welcome message

## Runtime environment

In principle, need python 2.7.x interpreter and mysql database

The following libraries are required:
* telepot
* MySQLdb

## First use

* Rename `config.py.default` to `config.py`
* Change the database configure and telegram bot token in `config.py`
* Import `groupwelcome.sql` to database which you will connect

## Run

After configure, you can using ./start.sh to run this bot
