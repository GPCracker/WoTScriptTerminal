# *************************
# Python
# *************************
import io
import sys
import zlib
import types
import marshal
import functools
import linecache
import threading
import traceback

# *************************
# Package
# *************************
from .sockets import TCPStreamServer, TCPStreamHandler, TCPStreamIO, TCPFrameIO

class StreamTee(object):
	def __init__(self, target, streams=None):
		super(StreamTee, self).__init__()
		self.target = target
		self.lock = threading.Lock()
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

	def add(self, stream):
		self.lock.acquire()
		self.streams.add(stream)
		self.lock.release()
		return

	def discard(self, stream):
		self.lock.acquire()
		self.streams.discard(stream)
		self.lock.release()
		return

	def __getattr__(self, name):
		result = getattr(self.target, name)
		if hasattr(result, '__call__'):
			return functools.partial(self.__callmethod__, name)
		return result

	def __callmethod__(self, name, *args, **kwargs):
		result = getattr(self.target, name)(*args, **kwargs) if not kwargs.pop('skipTarget', False) else None
		self.lock.acquire()
		for stream in self.streams:
			try:
				getattr(stream, name)(*args, **kwargs)
			except TypeError:
				try:
					target_encoding = getattr(self.target, 'encoding', sys.getdefaultencoding())
					getattr(stream, name)(
						*[unicode(item, encoding=target_encoding) for item in args],
						**{key: unicode(value, encoding=target_encoding) for key, value in kwargs.items()}
					)
				except:
					self.target.write('-' * 40 + '\n')
					self.target.write(traceback.format_exc())
					self.target.write('-' * 40 + '\n')
			except:
				self.target.write('-' * 40 + '\n')
				self.target.write(traceback.format_exc())
				self.target.write('-' * 40 + '\n')
		self.lock.release()
		return result

	def __del__(self):
		return

class TerminalServer(TCPStreamServer):
	allow_reuse_address = True
	daemon_threads = True

	def setup(self):
		self.locals = dict()
		self.buffer = io.StringIO()
		self.outtee = StreamTee(sys.stdout)
		self.errtee = StreamTee(sys.stderr)
		self.outtee.add(self.buffer)
		self.errtee.add(self.buffer)
		self.outtee.install(sys, 'stdout', False)
		self.errtee.install(sys, 'stderr', False)
		return

	def cleanup(self):
		self.outtee.remove(sys, 'stdout', True)
		self.errtee.remove(sys, 'stderr', True)
		self.outtee.discard(self.buffer)
		self.errtee.discard(self.buffer)
		self.outtee = None
		self.errtee = None
		self.buffer = None
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

	def service_fetch_logs(self):
		self.writer.write(self.server.buffer.getvalue())
		return

	def request_intro(self):
		self.stream_files_create()
		self.writer = io.TextIOWrapper(io.BufferedWriter(self.wfile, buffer_size=1), encoding=self.encoding, line_buffering=True)
		self.server.outtee.add(self.writer)
		self.server.errtee.add(self.writer)
		self.locals = TerminalLocals()
		self.locals.builtins = {
			'update_locals': self.service_update_locals,
			'fetch_logs': self.service_fetch_logs
		}
		return

	def request_serve(self):
		while True:
			binary_data = self.recv_frame()
			if not binary_data:
				break
			filename, script = marshal.loads(zlib.decompress(binary_data))
			linecache.cache[filename] = None, None, list(map(lambda line: line + '\n', script.split('\n'))), None
			try:
				exec(compile(script, filename.encode(errors='ignore'), 'exec'), self.locals)
			except:
				try:
					exc_type, exc_value, exc_traceback = sys.exc_info()
					sys.stderr.write(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback.tb_next)).join(['-' * 40 + '\n'] * 2))
				finally:
					exc_type = exc_value = exc_traceback = None
		return

	def request_outro(self):
		self.locals.builtins = None
		self.locals = None
		self.server.outtee.discard(self.writer)
		self.server.errtee.discard(self.writer)
		self.writer = None
		self.stream_files_remove()
		return

class TerminalController(object):
	def __init__(self, *args, **kwargs):
		super(TerminalController, self).__init__()
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
