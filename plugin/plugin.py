# *************************
# Python 3
# *************************
import io
import uuid
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
	terminal = ScriptTerminal(Settings('WoTScriptTerminal.sublime-settings', ScriptTerminal.defaults))
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
	@classmethod
	def load_settings(sclass, base_name):
		return sublime.load_settings(base_name)

	@classmethod
	def save_settings(sclass, base_name):
		return sublime.save_settings(base_name)

	def __init__(self, base_name, *args, **kwargs):
		self.base_name = base_name
		self.settings = self.load_settings(base_name)
		super(Settings, self).__init__(*args, **kwargs)
		return

	def save(self):
		self.save_settings(self.base_name)
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
		'save_locals': True,
		'fetch_logs': True,
		'show_output': True
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
		self.log_views = dict()
		self.log_thread = None
		self.log_event = Event()
		self.settings = settings
		self.uuid = str(uuid.uuid4())
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

	def connect(self, server_address):
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
		if self.settings['show_output']:
			self.create_log_output(sublime.active_window(), 'wot_python_log', True)
			sublime.active_window().run_command('show_panel', {'panel': 'output.' + 'wot_python_log'})
		for view_id in self.log_views.keys():
			sublime.View(view_id).run_command('script_terminal_update_log_view', {'string': string})
		return

	def log_start(self):
		self.log_thread = self.client.print_start(LogWriter(self.log_event))
		return

	def log_is_active(self):
		return self.log_thread is not None and self.log_thread.is_alive()

	def send_script(self, script):
		return self.client.send_script(script)

	def fetch_logs(self):
		return self.send_script('fetch_logs();')

	def save_locals(self):
		return self.send_script('update_locals({!r})'.format(self.uuid))

	def buffered_logs_get(self):
		return self.log_buffer.getvalue()

	def buffered_logs_clear(self):
		self.log_buffer = io.StringIO()
		return

	def create_log_file(self, window, name, scratch=False, read_only=False):
		view = self.create_file_view(window, name, scratch, read_only)
		self.log_views[view.id()] = None
		return view

	def create_log_output(self, window, name, read_only=False):
		for view_id, window_id in self.log_views.items():
			if window.id() == window_id != None:
				return sublime.View(view_id)
		view = window.create_output_panel(name)
		view.set_read_only(read_only)
		self.log_views[view.id()] = window.id()
		return view

# *************************
# Sublime Event Listeners
# *************************
class ScriptTerminalListener(sublime_plugin.EventListener):
	def on_pre_close(self, view):
		global terminal
		if terminal is not None:
			terminal.log_views.pop(view.id(), None)
		return

# *************************
# Sublime Commands
# *************************
class ScriptTerminalConnectCommand(sublime_plugin.ApplicationCommand):
	def run(self, server_address=None):
		global terminal
		if server_address is None:
			server_address = terminal.settings['server_host'], terminal.settings['server_port']
		result = terminal.connect(server_address)
		message = 'Connected to WoT client.' if result else 'Connect to WoT client failed.'
		sublime.status_message(message)
		if result and not terminal.log_is_active():
			terminal.log_start()
		if result and terminal.settings['fetch_logs']:
			terminal.fetch_logs()
		if result and terminal.settings['save_locals']:
			terminal.save_locals()
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

class ScriptTerminalUpdateLogViewCommand(sublime_plugin.TextCommand):
	def run(self, edit, string):
		global terminal
		terminal.view_append_string(self.view, edit, string)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and self.view.id() in terminal.log_views

class ScriptTerminalClearLogViewCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		terminal.view_clear(self.view, edit)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and self.view.id() in terminal.log_views

class ScriptTerminalNewLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_file(self.window, 'WoT Python Log', True, True)
		view.run_command('script_terminal_update_log_view', {'string': terminal.buffered_logs_get()})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalEmptyLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_file(self.window, 'WoT Python Log', True, True)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		view = self.window.active_view()
		view.run_command('script_terminal_clear_log_view')
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and self.window.active_view().id() in terminal.log_views

class ScriptTerminalShowLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_output(self.window, 'wot_python_log', True)
		self.window.run_command('show_panel', {'panel': 'output.' + 'wot_python_log'})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_output(self.window, 'wot_python_log', True)
		view.run_command('script_terminal_clear_log_view')
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogBufferCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.buffered_logs_clear()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

# *************************
# Sublime Settings Commands
# *************************
class ScriptTerminalToggleSaveLocalsCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.settings['save_locals'] = not terminal.settings['save_locals']
		terminal.settings.save()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

	def is_checked(self):
		global terminal
		return terminal is not None and terminal.settings['save_locals']

class ScriptTerminalToggleFetchLogsCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.settings['fetch_logs'] = not terminal.settings['fetch_logs']
		terminal.settings.save()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

	def is_checked(self):
		global terminal
		return terminal is not None and terminal.settings['fetch_logs']

class ScriptTerminalToggleShowOutputCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.settings['show_output'] = not terminal.settings['show_output']
		terminal.settings.save()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

	def is_checked(self):
		global terminal
		return terminal is not None and terminal.settings['show_output']
