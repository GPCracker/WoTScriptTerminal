import io
import sys
import errno
import select
import socket
import struct
import threading
import traceback

from .stream import SocketFileIO

class ThreadCaller(object):
	@staticmethod
	def call_in_thread(group=None, target=None, name=None, args=(), kwargs=None, daemon=False):
		thread = threading.Thread(group=group, target=target, name=name, args=args, kwargs=kwargs)
		thread.daemon = daemon
		thread.start()
		return thread

class TCPStreamServer(ThreadCaller):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	allow_reuse_address = False
	request_queue_size = 5
	daemon_threads = False

	@staticmethod
	def eintr_retry_call(func, *args, **kwargs):
		while True:
			try:
				return func(*args, **kwargs)
			except (OSError, select.error) as error:
				if error.args[0] != errno.EINTR:
					raise
		return

	def __init__(self, server_address, handler_class):
		self.server_address = server_address
		self.handler_class = handler_class
		self.socket = None
		self.shutdown_requested = threading.Event()
		self.shutdown_requested.clear()
		self.shutdown_completed = threading.Event()
		self.shutdown_completed.set()
		return

	def fileno(self):
		return self.socket.fileno() if self.socket else None

	def server_error(self):
		sys.stderr.write('-' * 40 + '\n')
		traceback.print_exc()
		sys.stderr.write('-' * 40 + '\n')
		return

	def server_init(self):
		try:
			self.socket = socket.socket(self.address_family, self.socket_type)
			if self.allow_reuse_address:
				self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
		except socket.error:
			self.server_error()
			return False
		return True

	def server_fini(self):
		try:
			self.socket = None
		except socket.error:
			self.server_error()
			return False
		return True

	def server_connect(self):
		try:
			self.socket.bind(self.server_address)
			self.socket.listen(self.request_queue_size)
			self.server_address = self.socket.getsockname()
		except socket.error:
			self.server_error()
			self.server_disconnect()
			return False
		return True

	def server_disconnect(self):
		try:
			self.socket.close()
		except socket.error:
			pass
		return

	def server_handle(self):
		try:
			request, client_address = self.request_get()
		except socket.error:
			return
		if self.request_verify(request, client_address):
			self.request_process(request, client_address)
		return

	def server_loop(self, poll_interval=0.5):
		if not self.shutdown_completed.is_set():
			raise RuntimeError('Shutdown is not completed.')
		try:
			self.shutdown_requested.clear()
			self.shutdown_completed.clear()
			while not self.shutdown_requested.is_set():
				rlist, wlist, xlist = self.eintr_retry_call(select.select, [self], [], [], poll_interval)
				if self in rlist:
					self.server_handle()
		finally:
			self.shutdown_requested.clear()
			self.shutdown_completed.set()
		return

	def server_start(self):
		return self.call_in_thread(target=self.server_loop, args=(), kwargs={}, daemon=self.daemon_threads)

	def server_shutdown(self):
		if self.shutdown_completed.is_set():
			raise RuntimeError('Shutdown is completed.')
		self.shutdown_requested.set()
		self.shutdown_completed.wait()
		return

	def request_get(self):
		return self.socket.accept()

	def request_shutdown(self, request):
		try:
			request.shutdown(socket.SHUT_WR)
		except socket.error:
			pass
		finally:
			self.request_cleanup(request)
		return

	def request_cleanup(self, request):
		try:
			request.close()
		except socket.error:
			pass
		return

	def request_verify(self, request, client_address):
		return True

	def request_thread(self, request, client_address):
		try:
			self.request_handle(request, client_address)
		except socket.error:
			self.request_error(request, client_address)
		except:
			self.handler_error(request, client_address)
		finally:
			self.request_shutdown(request)
		return

	def request_process(self, request, client_address):
		return self.call_in_thread(target=self.request_thread, args=(request, client_address), kwargs={}, daemon=self.daemon_threads)

	def request_handle(self, request, client_address):
		return self.handler_class(request, client_address, self)

	def request_error(self, request, client_address):
		sys.stderr.write('-' * 40 + '\n')
		sys.stderr.write('Socket exception occured during processing of request ({0!r}) from {1[0]}:{1[1]}\n'.format(request, client_address))
		traceback.print_exc()
		sys.stderr.write('-' * 40 + '\n')
		return

	def handler_error(self, request, client_address):
		sys.stderr.write('-' * 40 + '\n')
		sys.stderr.write('Handler exception occured during processing of request ({0!r}) from {1[0]}:{1[1]}\n'.format(request, client_address))
		traceback.print_exc()
		sys.stderr.write('-' * 40 + '\n')
		return

	def __del__(self):
		return

class TCPStreamHandler(object):
	disable_nagle_algorithm = False

	def __init__(self, socket, client_address, server):
		self.socket = socket
		self.client_address = client_address
		self.server = server
		self.request_init()
		self.request_intro()
		self.request_serve()
		self.request_outro()
		self.request_fini()
		return

	def fileno(self):
		return self.socket.fileno() if self.socket else None

	def request_init(self):
		if self.disable_nagle_algorithm:
			self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
		return

	def request_fini(self):
		return

	def request_intro(self):
		return

	def request_serve(self):
		return

	def request_outro(self):
		return

	def __del__(self):
		return

class TCPStreamClient(object):
	address_family = socket.AF_INET
	socket_type = socket.SOCK_STREAM
	disable_nagle_algorithm = False

	def __init__(self, server_address):
		self.server_address = server_address
		self.client_address = None
		self.socket = None
		return

	def fileno(self):
		return self.socket.fileno() if self.socket else None

	def client_error(self):
		sys.stderr.write('-' * 40 + '\n')
		traceback.print_exc()
		sys.stderr.write('-' * 40 + '\n')
		return

	def client_init(self):
		try:
			self.socket = socket.socket(self.address_family, self.socket_type)
			if self.disable_nagle_algorithm:
				self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
		except socket.error:
			self.client_error()
			return False
		return True

	def client_fini(self):
		try:
			self.socket = None
		except socket.error:
			self.client_error()
			return False
		return True

	def client_connect(self):
		try:
			self.socket.connect(self.server_address)
			self.client_address = self.socket.getsockname()
		except socket.error:
			self.client_error()
			self.client_cleanup()
			return False
		return True

	def client_disconnect(self):
		try:
			self.socket.shutdown(socket.SHUT_WR)
		except socket.error:
			pass
		finally:
			self.client_cleanup()
		return

	def client_cleanup(self):
		try:
			self.socket.close()
		except socket.error:
			pass
		return

	def __del__(self):
		return

class TCPStreamIO(object):
	def __init__(self, *args, **kwargs):
		self.rfile = None
		self.wfile = None
		return

	def stream_files_create(self):
		self.rfile = self.wfile = SocketFileIO(self.socket)
		return

	def stream_files_remove(self):
		try:
			self.rfile.close()
		except (socket.error, IOError):
			pass
		self.rfile = None
		try:
			self.wfile.close()
		except (socket.error, IOError):
			pass
		self.wfile = None
		return

class TCPFrameIO(object):
	frame_length_frmt = '=I'
	frame_length_size = struct.calcsize(frame_length_frmt)

	def send_frame(self, binary_data):
		try:
			if not binary_data:
				raise IOError('Sending empty frames is prohibited.')
			self.wfile.write(struct.pack(self.frame_length_frmt, len(binary_data)))
			self.wfile.write(binary_data)
		except (socket.error, IOError):
			return False
		return True

	def recv_frame(self):
		try:
			binary_data = self.rfile.read(self.frame_length_size)
			if not binary_data or len(binary_data) != self.frame_length_size:
				return None
			length = struct.unpack(self.frame_length_frmt, binary_data)[0]
			binary_data = self.rfile.read(length)
			if not binary_data or len(binary_data) != length:
				return None
			return binary_data
		except (socket.error, IOError):
			return None
		return
