# *************************
# Python 3
# *************************
# Nothing

# *************************
# SublimeText
# *************************
import sublime
import sublime_plugin

class ViewController(object):
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

	def __init__(self):
		super(ViewController, self).__init__()
		self.views = dict()
		return

	def create_file(self, window, name, scratch=False, read_only=False):
		view = self.create_file_view(window, name, scratch, read_only)
		self.views[view.id()] = None
		return view

	def create_output(self, window, name, read_only=False):
		for view_id, window_id in self.views.items():
			if window.id() == window_id != None:
				return sublime.View(view_id)
		view = window.create_output_panel(name)
		view.set_read_only(read_only)
		self.views[view.id()] = window.id()
		return view

	def on_view_close(self, view):
		self.views.pop(view.id(), None)
		return

	def update_views(self, update_command, string, output_name=None):
		if output_name is not None:
			self.create_output(sublime.active_window(), output_name, True)
			sublime.active_window().run_command('show_panel', {'panel': 'output.' + output_name})
		for view_id in self.views.keys():
			sublime.View(view_id).run_command(update_command, {'string': string})
		return
