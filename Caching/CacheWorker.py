import pickle
from pathlib import Path
from sys import getsizeof
from datetime import datetime
from RangeDict import OrderedRangeDict


class LRUIndex(object):
	def __init__(self, capacity):
		self.capacity = capacity
		self.cache = OrderedRangeDict()
	
	def get(self, key):
		try:
			te  = self.cache.pop(key)
			if(isinstance(te,tuple)):
				k, value = te
				self.cache[k] = value
				return value
			else:
				return -1
		except KeyError:
			return -1
	
	def set(self, key, value):
		if not isinstance(key, tuple):
			raise KeyError("Key is not a Tuple")
		try:
			self.cache.pop(key)
		except KeyError:
			if len(self.cache) >= self.capacity:
				self.cache.popitem(last=False)
		self.cache[key] = value


class DeckPagePool(object):
	def __init__(self, page_id: str, page_size: int, path: Path):
		self.page_id = page_id
		self._page_size = page_size
		self.serialization_path = path
		self.cached = []
		self.no_index_pages = 4
		self.index = LRUIndex(self.no_index_pages) #50 000 000
		
		self._elements = {}
		self._min_id = datetime.now()
		self._max_id = datetime.fromtimestamp(float(0))
	
	def __setitem__(self, note_id, note):
		if getsizeof(self._elements) > self._page_size/(self.no_index_pages + 1):
			filename = self.serialization_path.as_posix() + f'/{self.page_id}_{str(float((self._min_id - datetime(1970, 1, 1)).total_seconds()))}' \
			                                                f'_{str(float( (self._max_id - datetime(1970, 1, 1)).total_seconds()))}'
			with open(filename, 'wb') as f:
				pickle.dump(self._elements, f)
			self.cached.append((float((self._min_id - datetime(1970, 1, 1)).total_seconds()), float( (self._max_id - datetime(1970, 1, 1)).total_seconds()) ))
			self._reset()
		else:
			self._elements[note_id] = note
			if datetime.fromtimestamp(float(note_id)/1000) < self._min_id:
				self._min_id = datetime.fromtimestamp(float(note_id)/1000)
			if datetime.fromtimestamp(float(note_id)/1000) > self._max_id:
				self._max_id = datetime.fromtimestamp(float(note_id)/1000)
	
	def __getitem__(self, note_id):
		if note_id in self._elements.keys():
			return self._elements[note_id]
		res = self.index.get(float(note_id)/1000)
		if res  != -1 and res is not None:
			return res
		else:
			for ix in self.cached:
				if ix[0] <= float(note_id)/1000 <= ix[1]:
					filename = self.serialization_path.as_posix() + f'/{self.page_id}_{str(ix[0])}_{str(ix[1])}'
					with open(filename, "rb") as f:
						self.index.set(ix,pickle.load(f))
					if res := self.index.get(float(note_id)/1000) != -1:
						return res
					else:
						raise Exception("NOTE ID not present in pickled file")
				else:
					continue
	
	def _reset(self):
		self._min_id = datetime.now()
		self._max_id = datetime.fromtimestamp(float(0))
		self._elements = {}

class CacheManager(object):
	def __float__(self):
		self.pages = []
