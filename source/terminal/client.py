# *************************
# Python
# *************************
import io
import sys
import zlib
import marshal

# *************************
# Package
# *************************
from .sockets import ThreadCaller, TCPStreamClient, TCPStreamIO, TCPFrameIO

class TerminalClient(TCPStreamClient, TCPStreamIO, TCPFrameIO, ThreadCaller):
	encoding = 'utf-8'
	auto_disconnect = True

	def __init__(self, *args, **kwargs):
		super(TerminalClient, self).__init__(*args, **kwargs)
		self.connected = False
		return

	def io_create(self):
		self.reader = io.TextIOWrapper(io.BufferedReader(self.rfile, buffer_size=1), encoding=self.encoding, line_buffering=True)
		return

	def io_remove(self):
		self.reader = None
		return

	def connect(self):
		if self.connected:
			raise RuntimeError('Client is already connected to server.')
		if self.client_init():
			if self.client_connect():
				self.stream_files_create()
				self.io_create()
				self.connected = True
				return True
			try:
				self.client_disconnect()
			except:
				pass
		try:
			self.client_fini()
		except:
			pass
		return False

	def disconnect(self):
		if not self.connected:
			raise RuntimeError('Client is not connected to server.')
		self.connected = False
		try:
			self.io_remove()
		except:
			pass
		try:
			self.stream_files_remove()
		except:
			pass
		try:
			self.client_disconnect()
		except:
			pass
		try:
			self.client_fini()
		except:
			pass
		return

	def send_script(self, filename, script):
		if self.client_address is not None:
			filename = '{0[0]}:{0[1]}|{1}'.format(self.client_address, filename)
			result = self.send_frame(zlib.compress(marshal.dumps((filename, script), 2)))
			if not result and self.auto_disconnect and self.connected:
				self.disconnect()
			return result
		return False

	def send_command(self, script):
		return self.send_script('<command>', script)

	def update_locals(self, uuid):
		return self.send_command('update_locals({!r})'.format(uuid))

	def fetch_logs(self):
		return self.send_command('fetch_logs();')

	def print_loop(self, writer = None):
		if writer is None:
			writer = sys.stdout
		if not self.connected:
			raise RuntimeError('Client is not connected to server.')
		while True:
			try:
				line = self.reader.readline()
				if not line:
					break
				writer.write(line)
			except:
				break
		if self.auto_disconnect and self.connected:
			self.disconnect()
		return

	def print_start(self, writer = None):
		return self.call_in_thread(target=self.print_loop, args=(writer, ), kwargs={}, daemon=True)
