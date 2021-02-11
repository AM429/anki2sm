import sqlite3


def EmptyString(s: str) -> str:
	if s is None or len(s) == 0:
		return ""
	else:
		return s


class Model:
	def __init__(self, mid, typeofD, css, latexPre, latexPost):
		self.id = mid
		self.type = typeofD
		self.flds = None
		self.tmpls = None
		self.css = css
		self.latexPre = None
		self.latexPost = None
	
	def __str__(self):
		return ("<Model{id:" + EmptyString(self.id) + ",flds:[" + ','.join(
			str(e) for e in self.flds) + "],templates:[" + ','.join(str(e) for e in self.tmpls) + "]")
	
	def __repr__(self):
		return ("<Model{id:" + EmptyString(self.id) + ",flds:[" + ','.join(
			str(e) for e in self.flds) + "],templates:[" + ','.join(str(e) for e in self.tmpls) + "]")


class Template:
	def __init__(self, name, qfmt, did, bafmt, afmt, ordi, bqfmt):
		self.name = name
		self.qfmt = qfmt
		self.did = did
		self.bafmt = bafmt
		self.afmt = afmt
		self.ord = ordi
		self.bqfmt = bqfmt
	
	def __str__(self):
		return ("<Template{name:" + EmptyString(self.name) + ",qfmt:" + EmptyString(self.qfmt) + ",did:" + EmptyString(
			self.did) + ",bafmt:" + EmptyString(self.bafmt) + ",afmt:" + EmptyString(self.afmt) + ",ord:" + str(
			self.ord) + ",bqfmt:" + EmptyString(self.bqfmt) + "}>").replace("\n", "\\n")
	
	def __repr__(self):
		return ("<Template{name:" + EmptyString(self.name) + ",qfmt:" + EmptyString(self.qfmt) + ",did:" + EmptyString(
			self.did) + ",bafmt:" + EmptyString(self.bafmt) + ",afmt:" + EmptyString(self.afmt) + ",ord:" + str(
			self.ord) + ",bqfmt:" + EmptyString(self.bqfmt) + "}>").replace("\n", "\\n")


class Card:
	def __init__(self, cid, qs, ans):
		self.cid = cid
		self.q = qs
		self.a = ans
		self.afactor =None
		self.ufactor =None
		self.lapses =None
		self.last_rep = None
		self.repetitions = None
		self.interval = None
		self.nid = None
		
	def __str__(self):
		return ("<Card{Question:" + EmptyString(self.q) + ",Answer:" + EmptyString(self.a) + "}>").replace("\n", "")
	
	def __repr__(self):
		return ("<Card{Question:" + EmptyString(self.q) + ",Answer:" + EmptyString(self.a) + "}>").replace("\n", "")


class Collection:
	def __init__(self, did, name,is_subdeck=False ):
		self.name = name
		self.did = did
		self.cards = []
		self.isSub = is_subdeck
	
	def __str__(self):
		return "<Collection{name:" + EmptyString(self.name) + ",did:" + EmptyString(self.did) + ", cards:[" + ','.join(
			str(e) for e in self.cards) + "]}>"
	
	def __repr__(self):
		return "<Collection{name:" + EmptyString(self.name) + ",did:" + EmptyString(self.did) + ", cards:[" + ','.join(
			str(e) for e in self.cards) + "]}>"




class Note:
	def __init__(self, model, flds):
		self.model = model
		self.flds = flds
		self.tags = None
	
	def __str__(self):
		return "<Note{model:" + str(self.model) + ",Fields: " + str(self.flds) + "}>"
	
	def __repr__(self):
		return "<Note{model:" + str(self.model) + ",Fields: " + str(self.flds) + "}>"


class SQLNote(Note):
	def __init__(self, path, did,nid,models):
		query = f'SELECT id,mid,tags,flds from notes WHERE id={nid}'
		conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
		cursor = conn.cursor()
		cursor.execute(query)
		nid, mid, tags, flds = cursor.fetchone()
		
		self.model = models[str(mid)]
		self.flds = flds
		self.tags = EmptyString(tags).split(" ")