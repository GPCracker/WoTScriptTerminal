# *************************
# Python 3
# *************************
import os
import uuid

# *************************
# SublimeText
# *************************
import sublime
import sublime_plugin

# *************************
# Modules
# *************************
import WoTScriptTerminal.sublime.views
import WoTScriptTerminal.sublime.settings
import WoTScriptTerminal.terminal.terminal

# *************************
# Globals
# *************************
terminal = None

# *************************
# Sublime API
# *************************
def plugin_loaded():
	global terminal
	terminal = ScriptTerminal(TerminalSettings('WoTScriptTerminal.sublime-settings'))
	terminal.log_buffer_enable()
	terminal.views_update_enable()
	return

def plugin_unloaded():
	global terminal
	terminal.settings.save()
	if terminal.is_connected():
		terminal.disconnect()
	terminal.views_update_disable()
	terminal.log_buffer_disable()
	terminal = None
	return

# *************************
# Plug-in Classes
# *************************
class TerminalSettings(WoTScriptTerminal.sublime.settings.Settings):
	defaults = {
		'server_host': 'localhost',
		'server_port': 9000,
		'save_locals': True,
		'fetch_logs': True,
		'show_output': True,
		'client_uuid': str(uuid.uuid4())
	}

	def __init__(self, base_name):
		return super(TerminalSettings, self).__init__(base_name, self.defaults)

class ScriptTerminal(WoTScriptTerminal.sublime.views.ViewController, WoTScriptTerminal.terminal.terminal.ScriptTerminal):
	def __init__(self, settings):
		super(ScriptTerminal, self).__init__()
		self.settings = settings
		self.uuid = self.settings.setdefault('client_uuid')
		self.settings.save()
		return

	def log_update_views(self, string):
		return self.update_views('script_terminal_update_log_view', string, 'wot_python_log' if self.settings['show_output'] else None)

	def views_update_enable(self):
		return self.register_event(self.log_update_views)

	def views_update_disable(self):
		return self.unregister_event(self.log_update_views)

# *************************
# Sublime Event Listeners
# *************************
class ScriptTerminalListener(sublime_plugin.EventListener):
	def on_pre_close(self, view):
		global terminal
		if terminal is not None:
			terminal.on_view_close(view)
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
		filename = os.path.basename(self.view.file_name() or self.view.name()) or '<untitled>'
		script = self.view.substr(sublime.Region(0, self.view.size()))
		if not script:
			return
		result = terminal.send_script(filename, script)
		message = 'Script sending to WoT client successful.' if result else 'Script sending to WoT client failed.'
		sublime.status_message(message)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and terminal.is_connected()

class ScriptTerminalExecuteSelectedCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		filename = os.path.basename(self.view.file_name() or self.view.name()) or '<untitled>'
		script = ''.join(map(self.view.substr, self.view.sel()))
		if not script:
			return
		result = terminal.send_script(filename, script)
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
		return terminal is not None and self.view.id() in terminal.views

class ScriptTerminalClearLogViewCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global terminal
		terminal.view_clear(self.view, edit)
		return

	def is_enabled(self):
		global terminal
		return terminal is not None and self.view.id() in terminal.views

class ScriptTerminalNewLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_file(self.window, 'WoT Python Log', True, True)
		view.run_command('script_terminal_update_log_view', {'string': terminal.buffered_logs_get()})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalEmptyLogFileCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_file(self.window, 'WoT Python Log', True, True)
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
		return terminal is not None and self.window.active_view().id() in terminal.views

class ScriptTerminalShowLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_output(self.window, 'wot_python_log', True)
		self.window.run_command('show_panel', {'panel': 'output.' + 'wot_python_log'})
		return

	def is_enabled(self):
		global terminal
		return terminal is not None

class ScriptTerminalClearLogOutputCommand(sublime_plugin.WindowCommand):
	def run(self):
		global terminal
		view = terminal.create_output(self.window, 'wot_python_log', True)
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
