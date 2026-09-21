"""
This module and it's one-size-fits-all 'get' provide an API of sorts for
exposing capabilities for various python objects.  In particular, this is useful
for classes in cluster.py, but since we don't want to pollute that module with
web specific stuff, it lives here.  Hurrah.
"""

import bwsetup; bwsetup.addPath( "../.." )
from pycommon import exposed
from pycommon import process
from web_console.common import util
import signal

def get( o ):

	options = util.ActionMenuOptions()
	labels = set()

	# Macro to add redirects
	def addRedirect( label, *args, **kw ):
		options.addRedirect( label, *args, **kw )
		labels.add( label )

	# Macro to add script calls
	def addScript( label, *args, **kw ):
		options.addScript( label, *args, **kw )
		labels.add( label )

	# Processes that can be manually stopped
	if isinstance( o, process.StoppableProcess ):

		if isinstance( o, process.CellAppProcess ):
			addRedirect( "Stop", "/cc/stopproc",
					 params = dict( machine = o.machine.name, pid = o.pid ),
					 help = "Ask the process to remove itself from the cluster." )

		addRedirect( "Soft Kill", "/cc/killproc",
					 params = dict( machine = o.machine.name, pid = o.pid,
									signal = signal.SIGINT ),
					 help = "Shut down this process cleanly (SIGINT)" )

		addRedirect( "Hard Kill", "/cc/killproc",
					 params = dict( machine = o.machine.name, pid = o.pid,
									signal = signal.SIGKILL ),
					 help = "Forcefully terminate this process (SIGKILL)" )

		# Note: This option has been temporarily removed. The intention is to
		#       re-add this when user levels are added to WebConsole. For
		#       example, this should be available for developers but not
		#       production server operators.
		#addRedirect( "Restart", "/cc/killproc",
		#			 params = dict( machine = o.machine.name, pid = o.pid,
		#							signal = signal.SIGINT,
		#							restart = True ),
		#			 help = "Restart this process after shutdown via SIGINT" )

		addRedirect( "Quit (Dump Core)", "/cc/killproc",
					 params = dict( machine = o.machine.name, pid = o.pid,
									signal = signal.SIGQUIT ),
					 help = "Terminate this process and dump core (SIGQUIT)" )


	# Processes that have logs
	if isinstance( o, process.Process ) and \
	   (o.isServerProc() or isinstance( o, process.BotProcess )):
		addScript( "View Log", "Caps.gotoProcessLog",
				   args = (o.user().name, o.componentName(),
						   o.machine.name, o.pid),
				   help = "View the log for this process" )


	# Processes that have python servers
	if isinstance( o, process.CellAppProcess ) or \
	   isinstance( o, process.BaseAppProcess ) or \
	   isinstance( o, process.BotProcess ):

		port = o.getWatcherValue( "pythonServerPort" )
		label = "%s on %s" % (o.label(), o.machine.name)

		if port:
			addRedirect( "Console", "/console/console",
						 params = dict( host = o.machine.ip,
										port = port, process = label ),
						 help = "Connect to the Python console on this process" )

	# Processes that can be retired gracefully
	if isinstance( o, process.BaseAppProcess ) or \
			isinstance( o, process.CellAppProcess ):
		addRedirect( 'Retire App', '/cc/retireApp',
			params = dict( machine = o.machine.name, pid = o.pid ) )

	# Add in any Exposed methods whose names haven't been used already
	if isinstance( o, exposed.Exposed ):
		for func, label, args in o.getExposedMethods():
			if label not in labels:

				# If the function call takes arguments, add the requisite '...'
				if args:
					label += "..."

				addScript(
					label, "Ajax.call",
					args = ("/callExposed",
							dict( method = func,
								  onSuccess = "%s() called successfully" % func,
								  **o.getExposedID() ),
							"", "", args) )

	return options
