#!/usr/bin/env python
"""   Send a once-off message to MessageLogger processes in the cluster.

   The severity of the log message can be passed as any of the standard
   severity levels (TRACE, DEBUG, INFO, etc) and defaults to INFO.

   Command Options:
    -s,--severity <SEVERITY>    Set log message severity level.
                                The default is 'INFO'."""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util
from pycommon import log
import operator

def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-s", "--severity", default = "INFO" )

	return sopt


def getUsageStr():
	return "log  <message>  [<machines>]"


def getHelpStr():
	return __doc__


def run( args, env ):
	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	status = True

	if not parsedArgs:
		return env.usageError( "You must supply a log message", getUsageStr )

	# machines = command_util.selectMachines( self.cluster, parsedArgs[1:] )
	machines = env.getSelectedMachines( parsedArgs[1:] )
	loggers = reduce( operator.concat,
					  [m.getProcs( "message_logger" ) for m in machines], [] )

	if not loggers:
		env.warning( "No MessageLogger processes appear to be running" )
		status = False
	else:
		for logger in loggers:
			logger.sendMessage( parsedArgs[0], env.getUser(), options.severity )
			env.info( "Sent to %s", logger )

	return status


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# log.py
