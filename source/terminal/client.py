# *************************
# Python
# *************************
import io
import sys

# *************************
# Package
# *************************
from .sockets import ThreadCaller, TCPStreamClient, TCPStreamIO, TCPFrameIO

class TerminalClient(TCPStreamClient, TCPStreamIO, TCPFrameIO, ThreadCaller):
	encoding = 'utf-8'

	@staticmethod
	def print_loop(reader, writer = None):
		if writer is None:
			writer = sys.stdout
		while True:
			try:
				line = reader.readline()
				if not line:
					break
				writer.write(line)
			except:
				break
		return

	def print_start(self, writer = None):
		return self.call_in_thread(target=self.print_loop, args=(self.reader, writer), kwargs={}, daemon=True)

	def io_create(self):
		self.reader = io.TextIOWrapper(io.BufferedReader(self.rfile, buffer_size=1), encoding=self.encoding, line_buffering=True)
		return

	def io_remove(self):
		self.reader = None
		return

	def send_script(self, script):
		return self.send_frame(script.encode(self.encoding))
