# *************************
# Python
# *************************
import io
import uuid

# *************************
# Package
# *************************
from .helpers import Event
from .client import TerminalClient

class LogWriter(object):
	def __init__(self, write_func):
		super(LogWriter, self).__init__()
		self.write_func = write_func
		return

	def write(self, string):
		return self.write_func(string)

class ScriptTerminal(object):
	uuid = str(uuid.uuid4())

	def __init__(self):
		super(ScriptTerminal, self).__init__()
		self.client = None
		self.log_thread = None
		self.log_event = Event()
		self.log_buffer = io.StringIO()
		return

	def register_event(self, delegate):
		self.log_event += delegate
		return

	def unregister_event(self, delegate):
		self.log_event -= delegate
		return

	def log_buffer_enable(self):
		return self.register_event(self.log_buffer_write)

	def log_buffer_disable(self):
		return self.unregister_event(self.log_buffer_write)

	def connect(self, server_address):
		self.client = TerminalClient(server_address)
		result = self.client.connect()
		if result and not self.log_is_active():
			self.log_thread = self.client.print_start(LogWriter(self.log_event))
		return result

	def disconnect(self):
		self.client.disconnect()
		self.client = None
		return

	def is_connected(self):
		return self.client is not None and self.client.connected

	def log_buffer_write(self, string):
		return self.log_buffer.write(string)

	def log_is_active(self):
		return self.log_thread is not None and self.log_thread.is_alive()

	def buffered_logs_get(self):
		return self.log_buffer.getvalue()

	def buffered_logs_clear(self):
		self.log_buffer = io.StringIO()
		return

	def send_script(self, filename, script):
		return self.client.send_script(filename, script)

	def fetch_logs(self):
		return self.client.fetch_logs()

	def save_locals(self):
		return self.client.update_locals(self.uuid)
