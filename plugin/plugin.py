# *************************
# Python 3
# *************************
import functools

# *************************
# SublimeText
# *************************
import sublime
import sublime_plugin

# *************************
# WoTScriptTerminal
# *************************
from WoTScriptTerminal.client import TerminalClient

# *************************
# Globals
# *************************
client = None
defaults = None
settings = None
log_loop = None
log_view = None
log_writer = None

# *************************
# Settings
# *************************
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

# *************************
# Default settings
# *************************
defaults = {
	'host': 'localhost',
	'port': 9000
}

# *************************
# Sublime API
# *************************
def plugin_loaded():
	global settings, defaults
	settings = Settings(sublime.load_settings('WoTScriptTerminal.sublime-settings'), defaults)
	return

def plugin_unloaded():
	global client
	if client is not None:
		client.terminate()
		client = None
	return

# *************************
# Log Writer
# *************************
def log_write_func(string):
	if not log_view:
		return False
	log_view.run_command('script_terminal_log_message', {'string':string})
	return True

class LogWriter(object):
	def __init__(self, write_func):
		self.write_func = write_func
		return

	def write(self, string):
		return self.write_func(string)

# *************************
# Sublime Event Listeners
# *************************
class ScriptTerminalListener(sublime_plugin.EventListener):
	def on_close(self, view):
		global log_view, log_writer
		if log_view is not None and log_writer is not None and log_view.id() == view.id():
			log_view = None
			log_writer = None
			print('log_closed')
		return

# *************************
# Sublime Commands
# *************************
class ScriptTerminalLogCreateCommand(sublime_plugin.WindowCommand):
	def run(self):
		global client, log_loop, log_view, log_writer
		if log_view is None and log_writer is None:
			log_view = self.window.new_file()
			log_view.set_name('WoT Python Log')
			log_view.set_scratch(True)
			log_view.set_read_only(True)
			log_writer = LogWriter(log_write_func)
		if log_loop is None or not log_loop.is_alive():
			log_loop = client.print_start(log_writer)
		print('log_created')
		return

	def is_enabled(self):
		global client, log_loop, log_view, log_writer
		return client is not None and (log_loop is None or not log_loop.is_alive() or log_view is None and log_writer is None)

class ScriptTerminalLogMessageCommand(sublime_plugin.TextCommand):
	def run(self, edit, string):
		self.view.set_read_only(False)
		self.view.insert(edit, self.view.size(), string)
		self.view.set_read_only(True)
		return

class ScriptTerminalConnectCommand(sublime_plugin.WindowCommand):
	def run(self):
		global client, log_writer
		client = TerminalClient((settings['host'], settings['port']))
		if not client.launch():
			client = None
			sublime.status_message('Connect to {0}:{1} failed.'.format(settings['host'], settings['port']))
			print('failed')
			return
		self.window.run_command('script_terminal_log_create')
		sublime.status_message('Connected to {0}:{1}.'.format(settings['host'], settings['port']))
		print('connected')
		return

	def is_enabled(self):
		global client
		return client is None

class ScriptTerminalDisconnectCommand(sublime_plugin.WindowCommand):
	def run(self):
		global client
		client.terminate()
		client = None
		sublime.status_message('Disconnected from {0}:{1}.'.format(settings['host'], settings['port']))
		print('disconnected')
		return

	def is_enabled(self):
		global client
		return client is not None

class ScriptTerminalExecuteAllCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global client
		script = self.view.substr(sublime.Region(0, self.view.size()))
		if not client.send_script(script):
			sublime.status_message('Script sending to {0}:{1} failed.'.format(settings['host'], settings['port']))
			print('send_f')
			return
		sublime.status_message('Script sending to {0}:{1} successful.'.format(settings['host'], settings['port']))
		print('send_s')
		return

	def is_enabled(self):
		global client
		return client is not None

class ScriptTerminalExecuteSelectedCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global client
		script = ''.join(map(self.view.substr, self.view.sel()))
		if not client.send_script(script):
			sublime.status_message('Script sending to {0}:{1} failed.'.format(settings['host'], settings['port']))
			print('send_f')
			return
		sublime.status_message('Script sending to {0}:{1} successful.'.format(settings['host'], settings['port']))
		print('send_s')
		return

	def is_enabled(self):
		global client
		return client is not None
