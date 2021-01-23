from collections import OrderedDict


class RangeDict(dict):
	def __getitem__(self, item):
		if not isinstance(item, tuple):
			for key in self:
				if key[0] <= item <= key[1]:
					return self[key]
			raise KeyError(item)
		else:
			return super().__getitem__(item)
	
	def __setitem__(self, a, b):
		if isinstance(a, tuple):
			if a[0] < a[1]:
				dict.__setitem__(self, a, b)
			else:
				raise KeyError("a0 can't be larger then a1")
		else:
			raise KeyError("Key is not Tuple")


class OrderedRangeDict(dict):
	minKeys = {}
	
	def __int__(self, other=(), **kws):
		super().__init__(other=other, kwargs=kws)
	
	def __getitem__(self, item):
		if not isinstance(item, tuple):
			for key in self.minKeys.values():
				if key[0] <= item <= key[1]:
					return super(OrderedRangeDict, self).__getitem__(key[0])
			raise KeyError(item)
		else:
			return super(OrderedRangeDict, self).__getitem__(item)
	
	def __setitem__(self, a, b):
		if isinstance(a, tuple):
			if a[0] < a[1]:
				self.minKeys[a[0]] = a
				super().__setitem__(a, b)
			else:
				raise KeyError("a0 can't be larger then a1")
		else:
			raise KeyError("Key is not Tuple")
	
	def pop(self, key):
		if(isinstance(key,tuple)):
			if key in self.minKeys.values():
				self.minKeys.pop(key[0])
				return tuple([key,super().pop(key[0])])
		else:
			for k in self.minKeys.values():
				if k[0] <= key <= k[1]:
					self.minKeys.pop(k[0])
					return tuple([k,super().pop(k)])
			
	
	def popitem(self, last: bool = ...):
		v, k = super(OrderedRangeDict, self).popitem(last=last)
		res = tuple([self.minKeys[v], k])
		self.minKeys.pop(v)
		return res
