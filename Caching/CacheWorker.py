import pickle
from pathlib import Path
from sys import getsizeof
from RangeDict import OrderedRangeDict
from collections import OrderedDict


# A VERY IMPORTANT NOTE to self:
# if you ever decide on letting the user determine how much of their computer memory to use per page
# do add a warning that the smaller the memory size the more is the number of files written to memory is going to be
#

class LRUIndex(object):
	def __init__(self, capacity):
		self.capacity = capacity
		self.cache = OrderedRangeDict()
	
	def get(self, key):
		try:
			te = self.cache.pop(key)
			if te is not None:
				if isinstance(te, tuple):
					k, value = te
					self.cache[k] = value
					return value
				else:
					return -1
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
		self.index = LRUIndex(self.no_index_pages)  # 50 000 000
		
		self._elements = {}
		self._min_id = 9999999999999999
		self._max_id = 00
	
	def __setitem__(self, note_id, note):
		print(f'Size of Page{str(self.page_id)}  = '
		      f'{str((getsizeof(self._elements) + getsizeof(self.index)) / 1048576)}, '
		      f'{str(getsizeof(self._elements) > self._page_size / (self.no_index_pages + 1))}')
		
		if getsizeof(self._elements) > self._page_size / (self.no_index_pages + 1):
			self.serialize()
		
		self._elements[note_id] = note
		self._min_id = min(int(note_id), self._min_id)
		self._max_id = max(int(note_id), self._max_id)
	
	def __getitem__(self, note_id):
		if note_id in self._elements.keys():
			return self._elements[note_id]
		
		res = self.index.get(note_id)
		if res != -1 and res is not None:
			return res[note_id]
		else:
			for ix in self.cached:
				if ix[0] <= note_id <= ix[1]:
					filename = self.serialization_path.as_posix() + f'/{self.page_id}_{str(ix[0])}_{str(ix[1])}'
					with open(filename, "rb") as f:
						loaded_file = pickle.load(f)
						
						if len(self._elements.keys()) == 0:
							self._elements = loaded_file
							return self._elements[note_id]
						else:
							self.index.set(ix, loaded_file)
							res = self.index.get(note_id)
							if res != -1 and res is not None:
								return res[note_id]
							else:
								raise Excebption("NOTE ID not present in pickled file")
				else:
					continue
	
	def _reset(self):
		self._min_id = 99999999999999
		self._max_id = 0
		self._elements = {}
	
	def serialize(self):
		filename = self.serialization_path.as_posix() + f'/{self.page_id}_{str(int(self._min_id))}_{str(int(self._max_id))}'
		with open(filename, 'wb') as f:
			pickle.dump(self._elements, f)
		self.cached.append((int(self._min_id), int(self._max_id)))
		self._reset()
	
	def serialize_all(self):
		self.serialize()
		self.index = LRUIndex(self.no_index_pages)


class LRUCacheManager(object):
	def __init__(self, mx_size):
		self.max_size: int = mx_size
		self._active_pages: OrderedDict[str, DeckPagePool] = OrderedDict()
		self._inactive_pages: dict = {}
	
	def _size_of_ac_pages(self) -> int:
		return sum(
			list(
				map(lambda x: getsizeof(x), self._active_pages)
			)
		)
	
	def __setitem__(self, key: str, value: DeckPagePool):
		print(f'Size of CACHE Manager Pages: {str(self._size_of_ac_pages() / 1048576)}')
		if key not in self._active_pages.keys():
			try:
				self._active_pages.pop(key)
			except KeyError:
				sizeof_to_be_inserted = getsizeof(value)
				while self._size_of_ac_pages() + sizeof_to_be_inserted >= self.max_size:
					k, v = self._active_pages.popitem(last=False)
					v.serialize_all()
					self._inactive_pages[k] = v
			self._active_pages[key] = value
	
	def __getitem__(self, item):
		if item in self._active_pages.keys():
			try:
				value = self._active_pages.pop(item)
				self._active_pages[item] = value
				return value
			except KeyError:
				return -1
		else:
			try:
				te = self._inactive_pages.pop(item)
				if te is not None:
					k, v = te
					self.__setitem__(k, v)
					return v
			except KeyError as E:
				print(E)
				return -1
	
	def keys(self):
		return tuple(self._inactive_pages.keys()) + tuple(self._active_pages.keys())