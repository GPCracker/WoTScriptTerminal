import io
import sys
import types
import functools
import linecache
import traceback

from .sockets import TCPStreamServer, TCPStreamHandler, TCPStreamIO, TCPFrameIO

class StreamTee(object):
	def __init__(self, target, streams=None):
		self.target = target
		self.streams = streams if streams is not None else set()
		return

	def install(self, object, property, checkTypes=True):
		if checkTypes and not isinstance(getattr(object, property), types.FileType):
			raise RuntimeError('sys.stdout is not a file object.')
		setattr(object, property, self)
		return

	def remove(self, object, property, checkTypes=True):
		if checkTypes and getattr(object, property) is not self:
			raise RuntimeError('{0!r} is not a {1} object.'.format(getattr(object, property), self.__class__.__name__))
		setattr(object, property, self.target)
		return

	def __getattr__(self, name):
		result = getattr(self.target, name)
		if hasattr(result, '__call__'):
			return functools.partial(self.__callmethod__, name)
		return result

	def __callmethod__(self, name, *args, **kwargs):
		result = getattr(self.target, name)(*args, **kwargs) if not kwargs.pop('skipTarget', False) else None
		for stream in self.streams:
			try:
				getattr(stream, name)(*args, **kwargs)
			except TypeError:
				try:
					getattr(stream, name)(*[unicode(item) for item in args], **{key: unicode(value) for key, value in kwargs.items()})
				except:
					self.target.write(traceback.format_exc())
			except:
				self.target.write(traceback.format_exc())
		return result

	def __del__(self):
		return

class TerminalServer(TCPStreamServer):
	allow_reuse_address = True
	daemon_threads = True

	def setup(self):
		self.locals = dict()
		self.outtee = StreamTee(sys.stdout)
		self.errtee = StreamTee(sys.stderr)
		self.outtee.install(sys, 'stdout', False)
		self.errtee.install(sys, 'stderr', False)
		return

	def cleanup(self):
		self.outtee.remove(sys, 'stdout', True)
		self.errtee.remove(sys, 'stderr', True)
		self.outtee = None
		self.errtee = None
		self.locals = None
		return

	def launch(self):
		if not self.server_init() or not self.server_connect():
			return False
		self.server_start()
		return True

	def terminate(self):
		self.server_shutdown()
		self.server_disconnect()
		self.server_fini()
		return

class TerminalLocals(dict):
	@property
	def builtins(self):
		if not hasattr(self, '_builtins') or self._builtins is None:
			self._builtins = dict()
		return self._builtins

	@builtins.setter
	def builtins(self, value):
		self._builtins = value
		return

	def __missing__(self, key):
		return self.builtins[key]

class TerminalHandler(TCPStreamHandler, TCPStreamIO, TCPFrameIO):
	encoding = 'utf-8'

	def service_update_locals(self, uuid):
		self.locals, self.locals.builtins = self.server.locals.setdefault(uuid, self.locals), self.locals.builtins
		return

	def request_intro(self):
		self.stream_files_create()
		self.writer = io.TextIOWrapper(io.BufferedWriter(self.wfile, buffer_size=1), encoding=self.encoding, line_buffering=True)
		self.server.outtee.streams.add(self.writer)
		self.server.errtee.streams.add(self.writer)
		self.locals = TerminalLocals()
		self.locals.builtins = {'update_locals': self.service_update_locals}
		return

	def request_serve(self):
		filename = '{0[0]}:{0[1]}'.format(self.client_address)
		while True:
			binary_data = self.recv_frame()
			if not binary_data:
				break
			script = binary_data.decode(self.encoding)
			linecache.cache[filename] = None, None, map(lambda line: line + '\n', script.split('\n')), None
			try:
				exec(compile(script, filename, 'exec'), self.locals)
			except:
				try:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					sys.stderr.write(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback.tb_next)).join(['-' * 40 + '\n'] * 2))
				finally:
					exc_type = exc_value = exc_traceback = None
			del linecache.cache[filename]
		return

	def request_outro(self):
		self.locals.builtins = None
		self.locals = None
		self.server.outtee.streams.discard(self.writer)
		self.server.errtee.streams.discard(self.writer)
		self.writer = None
		self.stream_files_remove()
		return

class TerminalController(object):
	def __init__(self, *args, **kwargs):
		self.server = TerminalServer(*args, **kwargs)
		self.server.setup()
		self.server.launch()
		return

	def __del__(self):
		try:
			self.server.terminate()
			self.server.cleanup()
			self.server = None
		except:
			pass
		return
