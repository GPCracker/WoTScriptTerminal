# *************************
# Environment initialization
# *************************
target_globals = dict(globals())

# *************************
# Loader initialization
# *************************
import os, marshal

class WriteProtectedDict(dict):
	protected_keys = set(['_logLevel'])

	def __setitem__(self, key, value):
		if key not in self.protected_keys:
			super(WriteProtectedDict, self).__setitem__(key, value)
		return

target_globals.update({'_logLevel': 1})
target_globals = WriteProtectedDict(target_globals)

# *************************
# Loading original module
# *************************
original_file = os.path.normpath(os.path.join('res/', __file__)).replace(os.sep, '/')
if not os.path.isfile(original_file):
	raise IOError('Original file could not be found. Module loading impossible.')
with open(original_file, 'rb') as f:
	exec marshal.loads(f.read()[8:]) in target_globals

# *************************
# Replacing environment
# *************************
def replace_globals(source, target):
	source.clear()
	source.update(target)
	return

replace_globals(globals(), target_globals)
