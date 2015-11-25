# *************************
# Python
# *************************
import functools

# *************************
# BigWorld
# *************************
import BigWorld
import ResMgr

# *************************
# WoT Client
# *************************
import debug_utils

# *************************
# WoT Client Hooks
# *************************
# Nothing

# *************************
# ScriptTerminal Library
# *************************
from WoTScriptTerminal.server import TerminalHandler, TerminalController

# *************************
# Globals
# *************************
host, port = 'localhost', 9999
controller = TerminalController((host, port), TerminalHandler)

# *************************
# BigWorld log hooks
# *************************
def bwLogHook(origin, prefix, msg, *args, **kwargs):
	global controller
	if controller is not None:
		controller.server.errtee.write('[{0}] {1}\n'.format(prefix, msg), skipTarget = True)
	return origin(prefix, msg, *args, **kwargs)

BigWorld.logTrace = functools.partial(bwLogHook, BigWorld.logTrace)
BigWorld.logDebug = functools.partial(bwLogHook, BigWorld.logDebug)
BigWorld.logInfo = functools.partial(bwLogHook, BigWorld.logInfo)
BigWorld.logNotice = functools.partial(bwLogHook, BigWorld.logNotice)
BigWorld.logWarning = functools.partial(bwLogHook, BigWorld.logWarning)
BigWorld.logError = functools.partial(bwLogHook, BigWorld.logError)
BigWorld.logCritical = functools.partial(bwLogHook, BigWorld.logCritical)
BigWorld.logHack = functools.partial(bwLogHook, BigWorld.logHack)

# *************************
# debug_utils log hooks
# *************************
def new_init():
	result = old_init()
	debug_utils._g_logMapping.update({
		'TRACE': BigWorld.logTrace,
		'DEBUG': BigWorld.logDebug,
		'INFO': BigWorld.logInfo,
		'NOTE': BigWorld.logNotice,
		'NOTICE': BigWorld.logNotice,
		'WARNING': BigWorld.logWarning,
		'ERROR': BigWorld.logError,
		'CRITICAL': BigWorld.logCritical,
		'HACK': BigWorld.logHack
	})
	return result

old_init = debug_utils.init
debug_utils.init = new_init
