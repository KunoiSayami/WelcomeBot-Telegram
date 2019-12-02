from libpy3.mysqldb import mysqldb as MDB

class mysqldb(MDB):
	def insert_last_message_id(self, chat_id: int, message_id: int):
		self.execute("UPDATE `welcomemsg` SET `pervious_msg` = %s WHERE `group_id` = %s", (message_id, chat_id))
	
	def query_last_message_id(self, chat_id: int) -> int:
		return self.query1("SELECT `pervious_msg` FROM `welcomemsg` WHERE `group_id` = %s", chat_id)['pervious_msg']