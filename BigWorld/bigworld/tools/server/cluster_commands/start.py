#!/usr/bin/env python
"""   Start the server on the specified set of machines.  To start the server on
   all machines, you must explicitly pass 'all' for machine selection.

   Command Options:
    -b,--bots:      Allocate machines for and start bots processes
    -r,--revivers:  Start revivers on each machine used
    -s,--simple:    Only start a single CellApp and BaseApp
    -t,--tags:      Restrict what processes can be started on each machine by
                    its [Components] tag list as specified in
                    /etc/bwmachined.conf."""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def getUsageStr():
	return """start <machines>"""


def getHelpStr():
	return __doc__


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-b", "--bots", action = "store_true" )
	sopt.add_option( "-r", "--revivers", action = "store_true" )
	sopt.add_option( "-s", "--simple", action = "store_true" )
	sopt.add_option( "-t", "--tags", action = "store_true", default = True )

	return sopt


def run( args, env ):
	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	return command_util.genericServerStart( env,
				machines = parsedArgs,
				startBots = options.bots,
				startRevivers = options.revivers,
				obeyBWmachinedTags = options.tags,
				useSimpleLayout = options.simple,
				getUsageStr = getUsageStr )


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# start.py
