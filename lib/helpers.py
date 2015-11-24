import traceback

class Event(object):
	def __init__(self, delegates=None):
		self.__delegates = delegates if delegates is not None else set()
		return

	def __iadd__(self, delegate):
		if delegate not in self.__delegates:
			self.__delegates.add(delegate)
		return self

	def __isub__(self, delegate):
		if delegate in self.__delegates:
			self.__delegates.discard(delegate)
		return self

	def register(self, delegate):
		self.__iadd__(delegate)
		return

	def unregister(self, delegate):
		self.__isub__(delegate)
		return

	def __call__(self, *args, **kwargs):
		for delegate in self.__delegates:
			try:
				delegate(*args, **kwargs)
			except:
				traceback.print_exc()
		return

	def clear(self):
		self.__delegates.clear()
		return

	def __repr__(self):
		return 'Event({}):{!r}'.format(len(self.__delegates), self.__delegates)

	def __del__(self):
		return
