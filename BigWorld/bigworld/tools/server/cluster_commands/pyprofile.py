#!/usr/bin/env python
"""   Profile Python scripts from server processes.

   Activate Python profiling on the specified set of machines for a short
   amount of time.  Profiles are written to /tmp/<user>-<appname>-<time>.prof
   on each machine, and are copied back to the local machine when done using
   'scp'. As scp will attempt prompt for passwords by default it is recommended
   to install a ssh keypair into the user's home directory to allow scp to
   automatically connect to each machine required.

   Once all profiles are collected, a readable summary is written to
   /tmp/prof-summary-<time>.  This can be overriden with the '-o' option.

   If --cleanup is specified, raw profile data will be deleted automatically
   after the profile summary is displayed.  The summary itself is never
   deleted.

   Number of profiles to show can be limited with the --limit switch.

   Tables of caller and callee functions can be enabled with the --callers and
   --callees switches.

   By default, scp commands are executed as the logged in user, as opposed to
   the user specified with control_cluster.py's -u switch.  If you want to
   execute scp commands as the server user, pass --login-as-server-user.

   Command Options:
    -t|--time <secs>
    --callees                Enable display of a list of functions showing
                             what functions are being called.
    --callers                Enable display of a list of functions showing
                             where functions have been called from.
    --cleanup                Remove the raw profiling data gathered from each
                             server machine.
    --limit <n>
    --login-as-server-user
    -o|--output <summary>
    --port <ssh port>"""

if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

import os
import sys
import time

# Enable importing from pycommon
sys.path.append( os.path.dirname( __file__ ) + "/../.." )

from pycommon import log


def pyprofile( user, procs, secs, limit, cleanup, output, callers, callees,
			   switchLogin, sshPort ):
	"""
	Implements the 'pyprofile' command.
	"""

	# How many profiles we want to generate
	numProfs = len( procs )

	# Generate profile filename template
	now = time.strftime( "%Y-%m-%d-%H:%M:%S" )
	fname = "/tmp/%s-%%s-%s.prof" % (user.name, now )

	# Mapping of process to profile filename
	fnames = dict( [(p, fname % p.label()) for p in procs] )

	for p in procs[:]:

		# Make sure this process supports profiling
		if not p.getWatcherData( "pythonProfile" ):

			log.warning( "%s doesn't support Python profiling, skipping",
						 p.label() )

			procs.remove( p )
			continue


		# Set the filename
		if not p.setWatcherValue( "pythonProfile/filename", fnames[ p ] ):

			log.error( "Couldn't set profile filename on %s, skipping",
					   p.label() )

			procs.remove( p )
			continue

		# Enable profiling
		if not p.setWatcherValue( "pythonProfile/running", "true" ):

			log.error( "Couldn't enable profiling on %s, skipping", p.label() )
			procs.remove( p )
			continue

	# Let the profiles run
	log.info( "Letting profiles run for %.1f seconds ...", secs )
	aborted = False
	try:
		time.sleep( secs )
	except KeyboardInterrupt:
		log.info( "Aborted. Disabling profiling on all processes." )
		aborted = True

	# Disable profiling on all procs
	for p in procs[:]:

		if not p.setWatcherValue( "pythonProfile/running", "false" ):
			log.error( "Couldn't disable profiling on %s, skipping", p.label() )
			procs.remove( p )
			continue

	if aborted:
		return False

	# Copy profiles back to the local machine
	for p in procs:
		if switchLogin:
			os.system( "scp -P %s %s@%s:%s %s" %
					   (sshPort, user.name, p.machine.name,
					   fnames[ p ], fnames[ p ]) )
		else:
			os.system( "scp -P %s %s:%s %s" %
					   (sshPort, p.machine.name, fnames[ p ], fnames[ p ]) )


	# Because hotshot sucks and doesn't expose the full pstats API, I have
	# to hack stdout to avoid dumping straight to stdout
	summaryfname = output or "/tmp/prof-summary-%s" % now
	stdout = os.dup( 1 )
	fd = os.open( summaryfname, os.O_WRONLY | os.O_CREAT, 0644 )
	os.dup2( fd, 1 )

	# Read profile data and write summary
	import hotshot.stats
	for p in procs:

		print "\n*** %s ***\n" % p.label()
		prof = hotshot.stats.load( fnames[ p ] )
		prof.strip_dirs()

		prof.sort_stats( "time" )
		prof.print_stats( limit )

		prof.sort_stats( "cumulative" )
		prof.print_stats( limit )

		if callers:
			prof.sort_stats( "time" )
			prof.print_callers( limit )

		if callees:
			prof.sort_stats( "cumulative" )
			prof.print_callees( limit )

	# Restore stdout
	os.close( fd )
	os.dup2( stdout, 1 )

	# Dump summary to stdout
	sys.stdout.write( open( summaryfname ).read() )

	# Cleanup profile data if necessary
	if cleanup:
		for p in procs:
			os.unlink( fnames[ p ] )

	return len( procs ) == numProfs


def getUsageStr():
	return \
"""   pyprofile  <processes>  [-t|--time <secs>] [--cleanup] [--limit <n>]
                        [--callers] [--callees] [--login-as-server-user]
                        [-o <summary>] [--port <ssh port>]"""


def getHelpStr():
	return __doc__


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-t", "--time", type = "float", default = 10.0 )
	sopt.add_option( "--callees", action = "store_true",
     help = "Enable display of a list of functions showing what functions are "
	 			"being called." )
	sopt.add_option( "--callers", action = "store_true" )
	sopt.add_option( "--cleanup", action = "store_true" )
	sopt.add_option( "-l", "--limit", type = "int", default = 10 )
	sopt.add_option( "--login-as-server-user", action = "store_true" )
	sopt.add_option( "-o", "--output" )
	sopt.add_option( "-p", "--port", type = "int", default = 22 )

	return sopt


def run( args, env ):
	from pycommon import command_util

	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	user = env.getUser()

	processFilters = parsedArgs[:1]
	processes = env.getSelectedProcesses( processFilters )

	if not processes:
		return env.usageError(
			"You must specify at least one process to profile", getUsageStr	)

	return pyprofile( user, processes,
						options.time, options.limit, options.cleanup,
						options.output, options.callers, options.callees,
						options.login_as_server_user, options.port )


if __name__ == "__main__":
	from pycommon.command_util import runCommand
	sys.exit( runCommand( run ) )

# pyprofile.py
