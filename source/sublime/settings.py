# *************************
# Python 3
# *************************
# Nothing

# *************************
# SublimeText
# *************************
import sublime
import sublime_plugin

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

	def setdefault(self, key):
		if not self.settings.has(key):
			self.settings.set(key, self[key])
		return self.settings.get(key)

	def __getitem__(self, key):
		return self.settings.get(key, super(Settings, self).__getitem__(key))

	def __setitem__(self, key, value):
		return self.settings.set(key, value)

	def __repr__(self):
		return repr({key: self[key] for key in self})
