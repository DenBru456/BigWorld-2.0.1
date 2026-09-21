#!/usr/bin/env python
"""   Do a forced shutdown of the server using SIGINT.

   This method of server shutdown will forcefully tell the server processes to
   terminate regardless of what they are currently doing. While no data loss
   should occur using this method of shutdown, a connected client's user
   experience will be suddenly stopped and the database will have a sudden
   influx of incoming data.

   See also: 'stop' and 'nuke'"""


if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )


def getUsageStr():
	return "kill"


def getHelpStr():
	return __doc__


def run( args, env ):
	if args:
		env.warning( "Extra arguments given - %s", ', '.join( args ) )

	return env.getUser().stop()


if __name__ == "__main__":
	import sys
	from pycommon import command_util
	sys.exit( command_util.runCommand( run ) )

# kill.py
