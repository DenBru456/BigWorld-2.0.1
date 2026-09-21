#!/usr/bin/env python
"""   Restarts the server using the current server layout.

   If no arguments are passed, then the server is  restarted with the current
   layout of processes. If any essential server processes are missing from the
   current layout, one instance of each will be automatically included.

   Command Options:
    -b,--bots:      Allocate machines for and start bots processes
    -r,--revivers:  Start revivers on each machine used
    -t,--tags:      Restrict what processes can be started on each machine by
                    its [Components] tag list as specified in
                    /etc/bwmachined.conf."""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def getUsageStr():
	return "restart [...]"


def getHelpStr():
	return __doc__


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-b", "--bots", action = "store_true" )
	sopt.add_option( "-r", "--revivers", action = "store_true" )
	sopt.add_option( "-t", "--tags", action = "store_true", default = True )

	return sopt


def run( args, env ):
	sopt = _buildOptionsParser()

	(options, parsedArgs) = sopt.parse_args( args )

	return command_util.genericServerStart( env,
				machines = parsedArgs,
				restart = True,
				startBots = options.bots,
				startRevivers = options.revivers,
				obeyBWmachinedTags = options.tags,
		   		getUsageStr = getUsageStr )


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# restart.py
