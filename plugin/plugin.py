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
defaults = None
settings = None
terminal = None

# *************************
# Default settings
# *************************
defaults = {
	'server_host': 'localhost',
	'server_port': 9000,
	'save_locals': True,
	'new_logs_only': True,
	'auto_show_output_panel': True
}

# *************************
# Sublime API
# *************************
def plugin_loaded():
	global defaults, settings, terminal
	settings = Settings(sublime.load_settings('WoTScriptTerminal.sublime-settings'), defaults)
	terminal = ScriptTerminal()
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
	@staticmethod
	def create_file_view(window, name, scratch=False, read_only=False):
		view = window.new_file()
		view.set_name(name)
		view.set_scratch(scratch)
		view.set_read_only(read_only)
		return view

	@staticmethod
	def create_output_panel(window, name, read_only=False):
		view = window.create_output_panel(name)
		view.set_read_only(read_only)
		return view

	@staticmethod
	def show_output_panel(window, name):
		window.run_command("show_panel", {"panel": 'output.' + name})
		return

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

	def __init__(self):
		self.client = None
		self.log_views = set()
		self.log_thread = None
		self.log_outputs = dict()
		self.log_buffer = io.StringIO()
		self.log_event = Event()
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
		if not self.client.launch():
			self.disconnect()
			return False
		return True

	def disconnect(self):
		self.client.terminate()
		self.client = None
		return

	def is_connected(self):
		return self.client is not None

	def log_buffer_write(self, string):
		return self.log_buffer.write(string)

	def log_update_views(self, string):
		if settings['auto_show_output_panel']:
			self.create_log_output(sublime.active_window(), 'wot_python_log', True)
			self.show_output_panel(sublime.active_window(), 'wot_python_log')
		for view_id in self.log_views:
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
		self.log_views.add(view.id())
		if view.size() == 0 and not settings['new_logs_only']:
			view.run_command('script_terminal_log_message', {'string': self.get_logs()})
		return view

	def create_log_output(self, window, name, read_only=False):
		if window.id() in self.log_outputs:
			return sublime.View(self.log_outputs[window.id()])
		view = self.create_output_panel(window, name, read_only)
		self.log_views.add(view.id())
		self.log_outputs[window.id()] = view.id()
		if view.size() == 0 and not settings['new_logs_only']:
			view.run_command('script_terminal_log_message', {'string': self.get_logs()})
		return view

# *************************
# Sublime Event Listeners
# *************************
class ScriptTerminalListener(sublime_plugin.EventListener):
	def on_close(self, view):
		global terminal
		if terminal is not None and view.id() in terminal.log_views:
			terminal.log_views.discard(view.id())
			print('log_closed')
		return

# *************************
# Sublime Commands
# *************************
class ScriptTerminalConnectCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		result = terminal.connect((settings['server_host'], settings['server_port']))
		message = 'Connected to {0}:{1}.' if result else 'Connect to {0}:{1} failed.'
		sublime.status_message(message.format(settings['server_host'], settings['server_port']))
		if result and not terminal.log_is_active():
			terminal.log_start()
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and not terminal.is_connected()

class ScriptTerminalDisconnectCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		terminal.disconnect()
		message = 'Disconnected from {0}:{1}.'
		sublime.status_message(message.format(settings['server_host'], settings['server_port']))
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalExecuteScriptCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		script = self.view.substr(sublime.Region(0, self.view.size()))
		result = terminal.send_script(script)
		message = 'Script sending to {0}:{1} successful.' if result else 'Script sending to {0}:{1} failed.'
		sublime.status_message(message.format(settings['server_host'], settings['server_port']))
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalExecuteSelectedCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		script = ''.join(map(self.view.substr, self.view.sel()))
		result = terminal.send_script(script)
		message = 'Script sending to {0}:{1} successful.' if result else 'Script sending to {0}:{1} failed.'
		sublime.status_message(message.format(settings['server_host'], settings['server_port']))
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
		print('new_file')
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalShowLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_log_output(self.window, 'wot_python_log', True)
		terminal.show_output_panel(self.window, 'wot_python_log')
		print('new_output')
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogsCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		global terminal
		terminal.clear_logs()
		if True:
			for view_id in terminal.log_views:
				sublime.View(view_id).run_command('script_terminal_log_message', {'string': terminal.get_logs(), 'clear': True})
		print('logs_clear')
		return

	def is_enabled(self):
		global terminal
		return terminal is not None
