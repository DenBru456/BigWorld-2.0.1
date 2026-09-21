#!/usr/bin/env python
"""   Start an instance of the given process each machine specified.

   More than one process of the specified type may be started on each
   specified machine using the '-n' option."""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def getUsageStr():
	return "startproc <process name> <machines> [-n|--number <number>]"


def getHelpStr():
	return	__doc__


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-n", "--number", type = "int", default = 1 )

	return sopt


def run( args, env ):
	status = True

	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	if len( parsedArgs ) < 2:
		return env.usageError(
					"You must pass a process type and the machine to start on.",
					getUsageStr )
	else:
		processName = parsedArgs[0]
		machineNames = parsedArgs[1:]

		status = command_util.startProcess( env.getCluster(), env.getUser(),
								processName, machineNames, options.number )
		if status:
			env.getUser().ls()

	return status


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# startproc.py
