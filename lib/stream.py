import io
import errno
import socket

class SocketFileIO(object):
	recv_chunk_size = 8192
	send_chunk_size = 8192

	@staticmethod
	def eintr_retry_call(func, *args, **kwargs):
		while True:
			try:
				return func(*args, **kwargs)
			except (OSError, socket.error) as error:
				if error.args[0] != errno.EINTR:
					raise
		return

	def __init__(self, socket):
		self._socket = socket
		self._recv_buffer = io.BytesIO()
		return

	def close(self):
		self._sock = None
		return

	@property
	def closed(self):
		return self._socket is None

	def fileno(self):
		return self._socket.fileno()

	def flush(self):
		return

	def isatty(self):
		return False

	def readable(self):
		return True

	def writable(self):
		return True

	def seek(self, offset, whence=None):
		raise IOError('Socket does not support random access')
		return

	def seekable(self):
		return False

	def tell(self):
		raise IOError('Socket does not support random access')
		return

	def truncate(self, size=None):
		raise IOError('Socket does not support random access')
		return

	def __iter__(self):
		return self

	def next(self):
		line = self.readline()
		if not line:
			raise StopIteration
		return line

	def readall(self):
		return self.read()

	def readlines(self, hint=-1):
		lines = list()
		total = 0
		while True:
			line = self.readline()
			if not line:
				break
			lines.append(line)
			total += len(line)
			if total >= hint >= 0:
				break
		return lines

	def read(self, size=-1):
		rbuffer = self._recv_buffer
		self._recv_buffer = io.BytesIO()
		if size < 0:
			while True:
				data = self.eintr_retry_call(self._socket.recv, self.recv_chunk_size)
				if not data:
					break
				rbuffer.write(data)
			return rbuffer.getvalue()
		rbuffer_len = rbuffer.tell()
		if rbuffer_len >= size:
			rbuffer.seek(0)
			data = rbuffer.read(size)
			self._recv_buffer.write(rbuffer.read())
			return data
		data = self.eintr_retry_call(self._socket.recv, size - rbuffer_len)
		if not rbuffer_len:
			return data
		rbuffer.write(data)
		return rbuffer.getvalue()

	def readinto(self, b):
		rbuffer = self._recv_buffer
		self._recv_buffer = io.BytesIO()
		rbuffer_len = rbuffer.tell()
		size = len(b)
		if rbuffer_len >= size:
			rbuffer.seek(0)
			b[0:size] = rbuffer.read(size)
			self._recv_buffer.write(rbuffer.read())
			return size
		data = self.eintr_retry_call(self._socket.recv, size - rbuffer_len)
		size = min(size, len(data) + rbuffer_len)
		if not rbuffer_len:
			b[0:size] = data
			return size
		rbuffer.write(data)
		b[0:size] = rbuffer.getvalue()
		return size

	def readline(self, size=-1):
		rbuffer = self._recv_buffer
		self._recv_buffer = io.BytesIO()
		rbuffer_len = rbuffer.tell()
		if rbuffer_len > 0:
			rbuffer.seek(0)
			line = rbuffer.readline(size)
			if line.endswith(b'\n') and len(line) == size:
				self._recv_buffer.write(rbuffer.read())
				return line
			rbuffer.seek(0, 2)
		if size < 0:
			while True:
				data = self.eintr_retry_call(self._socket.recv, self.recv_chunk_size)
				if not data:
					break
				new_line = data.find(b'\n')
				if new_line >= 0:
					new_line += 1
					self._recv_buffer.write(data[new_line:])
					if not rbuffer_len:
						return data[:new_line]
					rbuffer.write(data[:new_line])
					break
				rbuffer.write(data)
				rbuffer_len += len(data)
			return rbuffer.getvalue()
		left = size - rbuffer_len
		data = self.eintr_retry_call(self._socket.recv, left)
		new_line = data.find(b'\n', 0, left)
		if new_line >= 0:
			new_line += 1
			self._recv_buffer.write(data[new_line:])
			if not rbuffer_len:
				return data[:new_line]
			rbuffer.write(data[:new_line])
		if not rbuffer_len:
			return data
		rbuffer.write(data)
		return rbuffer.getvalue()

	def write(self, data):
		data_len = len(data)
		wbuffer = io.BytesIO(data)
		wbuffer.seek(0)
		while wbuffer.tell() < data_len:
			self._socket.sendall(wbuffer.read(self.send_chunk_size))
		return data_len

	def writelines(self, lines):
		return self.write(b''.join(lines))

	def __del__(self):
		try:
			self.close()
		except:
			pass
		return
