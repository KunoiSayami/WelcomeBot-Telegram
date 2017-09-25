from __future__ import print_function, division
import sys
import time
from threading import Lock
from botlib.Config import Config

printLock = Lock()
logFile = Config.log.logfile and open(Config.log.logfile, 'a')

def info(fmt, *args, **kwargs):
	log('INFO', Config.log.log_info, Config.log.print_info, fmt.format(*args), **kwargs)

def error(fmt, *args, **kwargs):
	log('ERROR', Config.log.log_err, Config.log.print_err, fmt.format(*args), **kwargs)

def debug(fmt, *args, **kwargs):
	log('DEBUG', Config.log.log_debug, Config.log.print_debug, fmt.format(*args), **kwargs)

def reopen(path):
	global logFile
	if logFile:
		logFile.close()
	logFile = open(path, 'a')

def log(lvl, bLog, prtTarget, s, start='', end='\n'):
	s = '{}[{}][{}] {}{}'.format(start, time.strftime('%Y-%m-%d %H:%M:%S'), lvl, s, end)
	f = {'stdout': sys.stdout, 'stderr': sys.stderr}.get(prtTarget)
	printLock.acquire()
	try:
		if f:
			f.write(s)
			f.flush()
		if bLog and logFile:
			logFile.write(s)
			logFile.flush()
	finally:
		printLock.release()
