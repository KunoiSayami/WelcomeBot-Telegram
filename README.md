# Telegram Welcome bot

A bot can receive new chat member then show the welcome message

## Runtime environment

In principle, need python 2.7.x interpreter and mysql database

The following libraries are required:
* telepot
* MySQLdb

## First use

* Copy `data/config.ini.default` to `data/config.ini`
* Change the database configure and telegram bot token in `config.ini`
* Import `groupwelcome.sql` to database which you will connect

## Run

After configure, you can using ./start.sh to run this bot

## Hint

#### To clone repo, please use the following code

```bash
git clone https://github.com/Too-Naive/WelcomeBot-Telegram.git $TargetFolder
cd $TargetFolder
git submodule init
git submodule update
```

#### To pull repo, please use the following code

```bash
git pull
git submodule update
```

