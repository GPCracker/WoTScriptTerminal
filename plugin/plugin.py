# *************************
# Python 3
# *************************
import io
import functools

# *************************
# SublimeText
# *************************
import sublime
import sublime_plugin

# *************************
# WoTScriptTerminal
# *************************
from WoTScriptTerminal.helpers import Event
from WoTScriptTerminal.client import TerminalClient

# *************************
# Globals
# *************************
terminal = None

# *************************
# Sublime API
# *************************
def plugin_loaded():
	global terminal
	terminal = ScriptTerminal(Settings(sublime.load_settings('WoTScriptTerminal.sublime-settings'), ScriptTerminal.defaults))
	terminal.register_events()
	return

def plugin_unloaded():
	global terminal
	if terminal.is_connected():
		terminal.disconnect()
	terminal.unregister_events()
	terminal = None
	return

# *************************
# Plug-in Classes
# *************************
class LogWriter(object):
	def __init__(self, write_func):
		self.write_func = write_func
		return

	def write(self, string):
		return self.write_func(string)

class Settings(dict):
	def __init__(self, settings, *args, **kwargs):
		self.settings = settings
		super(Settings, self).__init__(*args, **kwargs)
		return

	def __getitem__(self, key):
		return self.settings.get(key, super(Settings, self).__getitem__(key))

	def __setitem__(self, key, value):
		return self.settings.set(key, value)

	def __repr__(self):
		return repr({key: self[key] for key in self})

class ScriptTerminal(object):
	defaults = {
		'server_host': 'localhost',
		'server_port': 9000,
		'new_logs_only': True,
		'logs_clear_buffer': True,
		'logs_clear_files': False,
		'logs_clear_output': True,
		'auto_show_output_panel': True
	}

	@staticmethod
	def create_file_view(window, name, scratch=False, read_only=False):
		view = window.new_file()
		view.set_name(name)
		view.set_scratch(scratch)
		view.set_read_only(read_only)
		return view

	@staticmethod
	def view_append_string(view, edit, string):
		read_only = view.is_read_only()
		view.set_read_only(False)
		view.insert(edit, view.size(), string)
		view.set_read_only(read_only)
		return

	@staticmethod
	def view_clear(view, edit):
		read_only = view.is_read_only()
		view.set_read_only(False)
		view.erase(edit, sublime.Region(0, view.size()))
		view.set_read_only(read_only)
		return

	def __init__(self, settings):
		self.client = None
		self.log_views = set()
		self.log_event = Event()
		self.settings = settings
		self.log_thread = None
		self.log_buffer = io.StringIO()
		return

	def register_events(self):
		self.log_event += self.log_buffer_write
		self.log_event += self.log_update_views
		return

	def unregister_events(self):
		self.log_event -= self.log_buffer_write
		self.log_event -= self.log_update_views
		return

	def connect(self, server_address=None):
		server_address = server_address if server_address is not None else (self.settings['server_host'], self.settings['server_port'])
		if isinstance(server_address, str):
			try:
				host, port = server_address.split(':')
				port = int(port)
				server_address = host, port
			except:
				return False
		self.client = TerminalClient(server_address)
		if self.client.client_init():
			if self.client.client_connect():
				self.client.stream_files_create()
				self.client.io_create()
				return True
			try:
				self.client.client_disconnect()
			except:
				pass
		try:
			self.client.client_fini()
		except:
			pass
		self.client = None
		return False

	def disconnect(self):
		try:
			self.client.io_remove()
		except:
			pass
		try:
			self.client.stream_files_remove()
		except:
			pass
		try:
			self.client.client_disconnect()
		except:
			pass
		try:
			self.client.client_fini()
		except:
			pass
		self.client = None
		return

	def is_connected(self):
		return self.client is not None

	def log_buffer_write(self, string):
		return self.log_buffer.write(string)

	def log_update_views(self, string):
		if self.settings['auto_show_output_panel']:
			self.create_log_output(sublime.active_window(), 'wot_python_log', True)
			sublime.active_window().run_command("show_panel", {"panel": 'output.' + 'wot_python_log'})
		for window_id, view_id, is_file in self.log_views:
			sublime.View(view_id).run_command('script_terminal_log_message', {'string': string})
		return

	def log_start(self):
		self.log_thread = self.client.print_start(LogWriter(self.log_event))
		return

	def log_is_active(self):
		return self.log_thread is not None and self.log_thread.is_alive()

	def send_script(self, script):
		return self.client.send_script(script)

	def get_logs(self):
		return self.log_buffer.getvalue()

	def clear_logs(self):
		self.log_buffer = io.StringIO()
		return

	def create_log_file(self, window, name, scratch=False, read_only=False):
		view = self.create_file_view(window, name, scratch, read_only)
		self.log_views.add((window.id(), view.id(), True))
		if not self.settings['new_logs_only'] and view.size() == 0:
			view.run_command('script_terminal_log_message', {'string': self.get_logs()})
		return view

	def create_log_output(self, window, name, read_only=False):
		for window_id, view_id, is_file in self.log_views:
			if window.id() == window_id and not is_file:
				return sublime.View(view_id)
		view = window.create_output_panel(name)
		view.set_read_only(read_only)
		self.log_views.add((window.id(), view.id(), False))
		if not self.settings['new_logs_only'] and view.size() == 0:
			view.run_command('script_terminal_log_message', {'string': self.get_logs()})
		return view

# *************************
# Sublime Event Listeners
# *************************
class ScriptTerminalListener(sublime_plugin.EventListener):
	def on_pre_close(self, view):
		global terminal
		if terminal is not None:
			terminal.log_views.discard((view.window().id(), view.id(), True))
			terminal.log_views.discard((view.window().id(), view.id(), False))
		return

# *************************
# Sublime Commands
# *************************
class ScriptTerminalConnectToCommand(sublime_plugin.WindowCommand):
	def run(self):
		on_input_done = lambda server_address: sublime.run_command('script_terminal_connect', {'server_address': server_address})
		self.window.show_input_panel('WoT client address (HOST:PORT)', '', on_input_done, None, None)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and not terminal.is_connected()

class ScriptTerminalConnectCommand(sublime_plugin.ApplicationCommand):
	def run(self, server_address=None):
		global terminal
		result = terminal.connect(server_address)
		message = 'Connected to WoT client.' if result else 'Connect to WoT client failed.'
		sublime.status_message(message)
		if result and not terminal.log_is_active():
			terminal.log_start()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and not terminal.is_connected()

class ScriptTerminalDisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.disconnect()
		message = 'Disconnected from WoT client.'
		sublime.status_message(message)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalExecuteScriptCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		script = self.view.substr(sublime.Region(0, self.view.size()))
		if not script:
			return
		result = terminal.send_script(script)
		message = 'Script sending to WoT client successful.' if result else 'Script sending to WoT client failed.'
		sublime.status_message(message)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalExecuteSelectedCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		script = ''.join(map(self.view.substr, self.view.sel()))
		if not script:
			return
		result = terminal.send_script(script)
		message = 'Script sending to WoT client successful.' if result else 'Script sending to WoT client failed.'
		sublime.status_message(message)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalLogMessageCommand(sublime_plugin.TextCommand):
	def run(self, edit, string, clear=False):
		global terminal
		if clear:
			terminal.view_clear(self.view, edit)
		terminal.view_append_string(self.view, edit, string)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and bool(terminal.log_views)

class ScriptTerminalNewLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_file(self.window, 'WoT Python Log', True, True)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalShowLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_output(self.window, 'wot_python_log', True)
		self.window.run_command("show_panel", {"panel": 'output.' + 'wot_python_log'})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogsCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		if terminal.settings['logs_clear_buffer']:
			terminal.clear_logs()
		for window_id, view_id, is_file in terminal.log_views:
			if is_file and terminal.settings['logs_clear_files'] or not is_file and terminal.settings['logs_clear_output']:
				sublime.View(view_id).run_command('script_terminal_log_message', {'string': '', 'clear': True})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None
