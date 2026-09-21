#!/usr/bin/env python
"""   Kill the specified processes.

   Similar in behaviour to the 'kill' server command, this will send a SIGINT
   signal to the specified server processes causing the main loop to finish its
   current processing and then shutdown the process.

   See also: 'stopproc' and 'nukeproc'"""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def getUsageStr():
	return "killproc <processes>"


def getHelpStr():
	return __doc__


def run( args, env ):
	processFilters = args

	if not processFilters:
		return env.usageError( "No processes specified", getUsageStr )

	processes = env.getSelectedProcesses( processFilters )

	if not processes:
		env.error( "No processes selected" )
		return False

	for process in processes:
		process.kill()

	return True


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# killproc.py
