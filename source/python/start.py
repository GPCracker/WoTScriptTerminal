from terminal.server import TerminalHandler, TerminalController

host, port = 'localhost', 9999
controller = TerminalController((host, port), TerminalHandler)
