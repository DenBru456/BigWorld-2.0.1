#!/usr/bin/env python
"""   Non-interactively run a Python script on server processes.

   Note: This option should generally only be used in a development environment
         and be used with EXTREME caution in a production environment due to
         the potential for a bad script to shut down or crash an active server.

   If no script file is provided, script input will be read from stdin.

   Command Options:
    -P,--no-prefix    Disable prefixing script input lines with ">>> "
    -l,--lock-cells   Prevent cells offloading entities during script execution
"""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-P", "--no-prefix", action = "store_true" )
	sopt.add_option( "-l", "--lock-cells", action = "store_true",
					default = False )

	return sopt


def getUsageStr():
	return "runscript <processes> [<filename>] [-l|--lock-cells] [-P|--no-prefix]"


def getHelpStr():
	return __doc__


def run( args, env ):
	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	shouldLockCells = options.lock_cells
	shouldPrefix = not options.no_prefix

	# If a .py file is in the arg list, it is the python script
	scriptContents = None
	for arg in parsedArgs:
		if arg.endswith( ".py" ):
			scriptContents = open( arg ).read()
			parsedArgs.remove( arg )
			break

	processFilters = parsedArgs
	if not processFilters:
		return env.usageError( "No processes specified", getUsageStr )

	processes = env.getSelectedProcesses( processFilters )

	if not processes:
		env.error( "No processes selected" )
		return False

	from pycommon import run_script
	return run_script.runscript( processes, scriptContents,
							   lockCells = shouldLockCells,
							   prefix = shouldPrefix )


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# runscript.py
