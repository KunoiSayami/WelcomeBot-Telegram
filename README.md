# Telegram Welcome bot

## Acceptable command

**Remember: Bot only receive administrators' and owner's command**

Command | Parameter(s) | Description
----|----|---
`/setwelcome` | `(gist link \| markdown text)` | Set welcome message
`/clear` | N/A | Clear setting welcome message
`/ping` | N/A | Return current session information
`/setflag ` | `(flags) (1\|0)` | Setting bot flags
<!--
`/poem` | N/A | Read poetry (TBD)
-->
### Placeholder

Bot is now support placeholder, using them in welcome message, 
bot will auto-replace them to what you wish

Placeholder | Replace to
---|----
`$name` | user nickname

_Known bug: If username contains markdown characters may cause markdown error (replace process not work)_

### Flags detail

Flag | Description | Default
---|----|---
no_welcome | Bot will auto delete previous welcome message | False
ignore_err | Show ~~rude~~ message to no privilege member who using bot command | True
no_blue | While bot is admin, it will delete bot command after 5 seconds (need delete privilege) | False 
no_new_member | Bot will auto delete \`Joined group' message (system generated) (need delete privilege) | False
no_service_msg | Bot will auto delete service message | False
<!--
poemable | Switch enable poem function for this group | False
-->

### Example

Set welcome message to **Welcome \[who\] to my group**:
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

In principle, need python 3.7.x interpreter and PostgreSQL database

The following libraries are required:

* pyrogram
* asyncpg
* aiohttp

### First use

* Copy `data/config.ini.default` to `data/config.ini`
* Change the database configure and telegram bot token in `config.ini`
* Import `group_welcome.sql` to database which you will connect

### Run

After configure, you can use `./welcome_bot.py` to run this bot

### v3.0 -> v4.0 migration

You should run `./welcome_bot.py upgrade` after updated code, that's all.

## Hint

#### To clone repo, please use the following code

```bash
git clone https://github.com/KunoiSayami/WelcomeBot-Telegram.git $TargetFolder
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

## LICENSE

[![](https://www.gnu.org/graphics/agplv3-155x51.png)](https://www.gnu.org/licenses/agpl-3.0.txt)
   
Copyright (C) 2017-2022 KunoiSayami

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
