# Telegram Welcome bot

A bot can receive new chat member then show the welcome message

## Acceptable command

**Remember: Bot only receive admins' and owner's command**

Command | Parameter(s) | Description
----|--|---
`/setwelcome` | `(gist link \| markdown text)` | Set welcome message
`/setflag ` | `(flags) (1\|0)` | Setting bot flags
`/clear` | N/A | Clear setting welcome message
`/ping` | N/A | Return current session information
`/poem` | N/A | Read poetry (TBD)

### Placeholder

Bot is now support placeholder, using them in welcome message, 
bot will auto-replace them to what you wish

Placeholder | Replace to
---|----
`$name` | user nickname

_Known bug: If user name contains markdown characters may cause markdown error (replace process not work)_

### Flags detail

Flag | Description | Default
---|----|---
poemable | Switch enable poem function for this group | False
ignore_err | Show ~~rude~~ message to no privilege member who using bot command | True
noblue | While bot is admin, it will delete bot command after 5 seconds (need delete privilege) | False 

### Example

Set welcome message to **Welcome [who] to my group**:
```
/setwelcome **Welcome $name to my group**
```
or
```
/setwelcome https://gist.githubusercontent.com/anonymous/6446fbae52916bc7fb092dd1ee3f8483/raw/4ad5231d5e2a68458e117db9bed97407dfe6f47b/welcomemsg
```

_After you run this command, bot will reply your a message_

Clear welcome message:
```
/clear
```

## Installation

### Runtime environment

In principle, need python 2.7.x interpreter and mysql database

The following libraries are required:
* telepot
* MySQLdb

### First use

* Copy `data/config.ini.default` to `data/config.ini`
* Change the database configure and telegram bot token in `config.ini`
* Import `groupwelcome.sql` to database which you will connect

### Run

After configure, you can using ./start.sh to run this bot

## Hint

#### To clone repo, please use the following code

```bash
git clone https://github.com/Too-Naive/WelcomeBot-Telegram.git $TargetFolder
cd $TargetFolder
git submodule update --init
```

#### To pull repo, please use the following code

```bash
git pull
git submodule update
```

#### If Bot is group admin
If bot is group admin, other member who not admin or owner using command will receive
1 minute cold down (need ban user privilege)

