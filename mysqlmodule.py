# -*- coding: utf-8 -*-
#
#This source code was published under GPL v3
#
#Copyright (C) 2017 Too-Naive
#
import MySQLdb as mysqldb

class mysqlModule:
	def __init__(self,host,port,user,passwd,dbName=None):
		self.host = host
		self.port = port
		self.user = user
		self.passwd = passwd
		self.dbName = dbName
		if not self.dbName:
			self.db = mysqldb.connect(host=self.host,user=self.user,passwd=self.passwd,
				charset='utf8',port=self.port)
		else:
			self.db = mysqldb.connect(host=self.host,user=self.user,passwd=self.passwd,
				db=self.dbName,charset='utf8',port=self.port)
		self.cursor = self.db.cursor()
	def execute(self,sql):
		return self.cursor.execute(sql)
	def getData(self):
		return self.cursor.fetchall()
	def query(self,sql):
		self.execute(sql)
		return self.getData()
	def close(self):
		self.db.commit()
		self.db.close()
