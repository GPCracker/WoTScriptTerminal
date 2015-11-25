import os, marshal

class WriteProtectedDict(dict):
	protected_keys = set(['_logLevel'])

	def __setitem__(self, key, value):
		if key not in self.protected_keys:
			super(WriteProtectedDict, self).__setitem__(key, value)
		return

module_globals = WriteProtectedDict({'_logLevel': 1})

original_file = os.path.normpath(os.path.join('res/', __file__)).replace(os.sep, '/')
if not os.path.isfile(original_file):
	raise IOError('Original file could not be found. Module loading impossible.')
with open(original_file, 'rb') as f:
	exec marshal.loads(f.read()[8:]) in module_globals

(lambda module_globals: globals().clear() and globals.update(module_globals)).__call__(module_globals)
