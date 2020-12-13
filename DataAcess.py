import sqlite3


class DataAccess(object):
	def __init__(self, path: str):
		self._db_path = path
		self.conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
	
	def query_db(self,query:str) -> list:
		cursor = self.conn.cursor()
		cursor.execute(query)
		rows = cursor.fetchall()
		return rows
	
	def dispose(self):
		self.conn.close()
		self.conn = None