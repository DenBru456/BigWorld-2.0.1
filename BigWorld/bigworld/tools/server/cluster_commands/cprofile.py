#!/usr/bin/env python
"""   Fetches all C++ profiles from the specified server processes (these must
   be CellApp or BaseApp processes) and display them in a tabular format.

   Command Options:
    -l,--limit <limit>   Limit the generated output to the top <limit> entries
                         after sorting. The default limit is 20.

    -s,--sort <sortkey>  Sort output according to a particular column of output.
                         Supported values for <col> are:
                          'count'
                          'cumTime'
                          'cumTimePerCall'
                          'intTime'
                          'intTimePerCall'
                         The default is 'intTime'.

    -t,--time <secs>     Total time (in seconds) in which sampling will occur
                         to generate profile output. Defaults to 10 seconds."""


if __name__ == "__main__":
	import bwsetup
	bwsetup.addPath( ".." )

from pycommon import command_util
import time

class Profile( object ):
	"""Class to read a single profile detail directory."""

	def __init__( self, wd, stamps ):

		self.name = wd.name
		self.count = int( wd.getChild( "count" ).value )

		self.cumTime = int( wd.getChild( "sumTime" ).value ) / stamps
		self.intTime = int( wd.getChild( "sumIntTime" ).value ) / stamps

		self.cumTimePerCall = 0
		self.intTimePerCall = 0

		self.calcTimePerCall()


	def calcTimePerCall( self ):

		if self.count:
			self.cumTimePerCall = int( self.cumTime / self.count * 1000000 )
			self.intTimePerCall = int( self.intTime / self.count * 1000000 )
		else:
			self.cumTimePerCall = 0
			self.intTimePerCall = 0


	def delta( self, prev ):

		self.count -= prev.count
		self.cumTime -= prev.cumTime
		self.intTime -= prev.intTime
		self.calcTimePerCall()


class Sample( object ):
	"""Class to sample all profiles at a specific point in time."""

	def __init__( self, proc ):
		# Check that the proc supports the required watchers
		stampsPerSecond = 	proc.getWatcherValue( 'stats/stampsPerSecond' )		
		totalSpareTime = 	proc.getWatcherValue( 'nub/timing/totalSpareTime' )
		runningTime = 		proc.getWatcherValue( 'stats/runningTime' )
		profiles = 			proc.getWatcherData( "profiles/details" )

		if stampsPerSecond is None or \
				totalSpareTime is None or \
				runningTime is None or \
				profiles.type is None:
			raise ValueError, \
				"cprofile not supported for %s processes" % \
					proc.name

		self.proc = proc
		self.profiles = {}

		self.stampsPerSec = float( stampsPerSecond )

		# Iterate over all profiles
		for prof in profiles:
			self.profiles[ prof.name.lower() ] = \
						   Profile( prof, self.stampsPerSec )

		# Calculate total running time
		self.spareTime = float( totalSpareTime ) / self.stampsPerSec

		self.runningTime = (int( runningTime ) / self.stampsPerSec) - \
			self.spareTime

	# Subtract profile data from a previous sample to turn this sample into
	# a delta.
	def delta( self, prev ):

		for name in self.profiles:
			self.profiles[ name ].delta( prev.profiles[ name ] )

		self.runningTime -= prev.runningTime
		self.spareTime -= prev.spareTime



def cprofile( procs, secs, sortkey, limit ):
	"""Implements the 'cprofile' command."""

	# Take the initial samples, then wait.
	samples = dict( [(p, Sample( p )) for p in procs] )

	print "Waiting %.1f secs for sample data ..." % secs
	time.sleep( secs )

	# Take deltas against the initial samples.
	for proc in samples:
		newSample = Sample( proc )
		newSample.delta( samples[ proc ] )
		samples[ proc ] = newSample

	# Display profiles over the intervening period for each process
	for proc, sample in sorted( samples.items() ):

		# Calculate max width of profile name
		width = reduce( lambda x, y: max( x, y ),
						[len( s ) for s in sample.profiles] )

		template = "%%-%ds " % width
		template += "%8d | %6.3fs %6dus %5.1f%% | %6.3fs %6dus %5.1f%%"

		header = "%%-%ds " % width
		header += "%8s   %-23s   %-23s"

		print "\n*** %s ***\n" % proc.label()
		print header % ("Profile", "Count", "Cumulative Times", "Internal Times")

		# Display profiles
		numDisplayed = 0

		for name, profile in \
			sorted( sample.profiles.items(),
					key = lambda (n,p): -getattr( p, sortkey ) ):

			if profile.name != "runningTime":

				print template % (profile.name, profile.count,
								  profile.cumTime, profile.cumTimePerCall,
								  100 * profile.cumTime / sample.runningTime,
								  profile.intTime, profile.intTimePerCall,
								  100 * profile.intTime / sample.runningTime)

				numDisplayed += 1
				if numDisplayed >= limit:
					break

		print "\nTotal running time: %.3fs (%.3fs spare)" % \
			  (sample.runningTime, sample.spareTime)

	return True


def getUsageStr():
	return \
"""cprofile <processes> [-l <limit>] [-s|--sort <sortkey>] [-t|--time <secs>]
   Profile C++ method calls on server processes (must be BaseApp or CellApp)."""


def getHelpStr():
	return __doc__


def _buildOptionsParser():
	import optparse

	sopt = optparse.OptionParser( add_help_option = False )
	sopt.add_option( "-l", "--limit", default = 20, type = "int" )
	sopt.add_option( "-s", "--sort",  default = "intTime" )
	sopt.add_option( "-t", "--time",  default = 10.0, type = "float" )

	return sopt


def run( args, env ):
	sopt = _buildOptionsParser()
	(options, parsedArgs) = sopt.parse_args( args )

	processFilters = parsedArgs[:1]
	processes = env.getSelectedProcesses( processFilters )

	if not processes:
		return env.usageError(
			"You must specify at least one process to profile", getUsageStr )

	return cprofile( processes, options.time, options.sort, options.limit )


if __name__ == "__main__":
	import sys
	sys.exit( command_util.runCommand( run ) )

# cprofile.py
