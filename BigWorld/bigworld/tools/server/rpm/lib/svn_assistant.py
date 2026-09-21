#!/usr/bin/env python

import re
import subprocess
import sys


def _discoverLineStartingWith( prefix, pipe ):

	output = ""
	desiredLine = None

	while pipe.poll() is None:
		output += pipe.stdout.read()
		lines = output.split( "\n" )
		if len( lines ) > 1:
			results = [ line for line in lines if line.startswith( prefix ) ]
			if results:
				desiredLine = re.sub( "%s *" % prefix, "", results[ 0 ] )

	pipe.wait()

	return desiredLine


def latestRevision( mfRoot ):

	# Extract the URL and then run again, this is done
	# in case the current checkout is not up to date.
	cmd = [ "svn", "info", mfRoot ]

	try:
		pipe = subprocess.Popen( cmd,
				stdout = subprocess.PIPE, stderr = subprocess.STDOUT )
	except OSError:
		print "Failed to execute '%s'" % " ".join( cmd )
		sys.exit( 1 )

	repositoryURL = _discoverLineStartingWith( "URL:", pipe )


	# Now ask the repository what version it thinks it is.
	cmd = [ "svn", "info", repositoryURL ]

	try:
		pipe = subprocess.Popen( cmd,
				stdout = subprocess.PIPE, stderr = subprocess.STDOUT )
	except OSError:
		print "Failed to execute '%s'" % " ".join( cmd )
		sys.exit( 1 )

	revision = _discoverLineStartingWith( "Revision:", pipe )

	return revision


# svn_assistant.py
