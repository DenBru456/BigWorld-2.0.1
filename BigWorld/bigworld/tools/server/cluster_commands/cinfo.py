#!/usr/bin/env python
"""   Show information about machines in a server cluster.

   If no machines are specified, information from all machines in the server
   cluster will be displayed."""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def getUsageStr():
	return "cinfo [<machines>]"


def getHelpStr():
	return __doc__


def run( args, env ):
	machineList = args
	if machineList:
		machines = env.getSelectedMachines( machineList )
		if not machines:
			return False

		for machine in machines:
			env.info( machine )

	else:
		env.info( env.getCluster() )

	return True


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# cinfo.py
