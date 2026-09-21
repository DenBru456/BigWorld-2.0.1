#!/usr/bin/env python
"""   Force the specified processes to shutdown causing a core dump.

   Similar in behaviour to the 'nuke' server command, this will send a SIGQUIT
   signal to the specified server processes causing the process to terminate
   in its current state and generate a core dump for process state analysis.

   See also: 'stopproc' and 'killproc'"""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )


def getUsageStr():
	return "nukeproc <processes>"


def getHelpStr():
	return __doc__


def run( args, env ):
	from pycommon import messages

	processFilters = args
	processes = env.getSelectedProcesses( processFilters )

	if not processes:
		return env.usageError( "No processes specified", getUsageStr )

	for process in processes:
		process.machine.killProc( process, messages.SignalMessage.SIGQUIT )

	return True


if __name__ == "__main__":
	import sys
	from pycommon import command_util
	sys.exit( command_util.runCommand( run ) )

# nukeproc.py
