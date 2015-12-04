# *************************
# Environment initialization
# *************************
target_globals = dict(globals())

# *************************
# Loading WoTScriptTerminal
# *************************
import WoTScriptTerminalLoader

# *************************
# Loading original module
# *************************
import os, marshal
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
