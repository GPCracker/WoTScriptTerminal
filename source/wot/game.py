exec '''
# *************************
# Loading WoTScriptTerminal
# *************************
import WoTScriptTerminal

# *************************
# Loading original module
# *************************
import os, marshal
original_file = os.path.normpath(os.path.join('res/', __file__)).replace(os.sep, '/')
if not os.path.isfile(original_file):
	raise IOError('Original file could not be found. Module loading impossible.')
with open(original_file, 'rb') as f:
	exec marshal.loads(f.read()[8:]) in target_globals
''' in dict(globals(), **{'target_globals': globals()})
