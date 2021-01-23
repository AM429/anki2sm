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
			k, value = self.cache.pop(key)
			self.cache[k] = value
			return value
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
	def __int__(self, page_id: str, page_size: int, path: Path):
		self.page_id = page_id
		self._page_size = page_size
		self.serialization_path = path
		self.cached = []
		self.index = LRUIndex(4)
		
		self._elements = {}
		self._min_id = datetime.fromtimestamp(float(0))
		self._max_id = datetime.fromtimestamp(float(0))
	
	def __setitem__(self, note_id, note):
		if getsizeof(self._elements) > self._page_size:
			filename = self.serialization_path.as_posix() + f'/{self.page_id}_{str(datetime.timestamp(self._min_id))}' \
			                                                f'_{str(datetime.timestamp(self._max_id))}'
			with open(filename, 'w') as f:
				pickle.dump(self._elements, f)
			self.cached.append((float(datetime.timestamp(self._min_id)), float(datetime.timestamp(self._max_id))))
			self._reset()
		else:
			self._elements[note_id] = note
			if datetime.fromtimestamp(float(note_id)) < self._min_id:
				self._min_id = datetime.fromtimestamp(float(note_id))
			if datetime.fromtimestamp(float(note_id)) > self._max_id:
				self._max_id = datetime.fromtimestamp(float(note_id))
	
	def __getitem__(self, note_id):
		if note_id in self._elements.keys():
			return self._elements[note_id]
		elif res := self.index.get(float(note_id)) != -1:
			return res
		else:
			# unpickle the file and load it into the index
			pass

	def _reset(self):
		self._min_id = datetime.fromtimestamp(float(0))
		self._max_id = datetime.fromtimestamp(float(0))
		self._elements = {}
	
	def clean(self):
		pass


class CacheManager(object):
	def __int__(self):
		self.pages = []
