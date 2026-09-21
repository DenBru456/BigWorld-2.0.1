#!/usr/bin/env python

REMOVE_TEMP_DIR = True

from lib.rpm_builder import RPMBuilder

import logging
import os

log = logging.getLogger( 'generate' )

def main( args ):
	mfRoot = os.path.abspath( os.path.dirname( __file__ ) + "/../../../.." )

	if len( args ) < 2:
		raise ValueError, "Invalid command line arguments"

	packageDir = args[1]

	print '-' * 80
	print "Starting RPM build for %s" % packageDir
	print '-' * 80

	builder = RPMBuilder( mfRoot, packageDir )

	if not builder.build( "binary_rpms", REMOVE_TEMP_DIR ):
		sys.exit( 1 )


if __name__ == "__main__":
	import sys

	logging.basicConfig( level=logging.INFO )

	if os.getuid() == 0:
		log.critical( "This script must not be executed by the root user." )
		sys.exit( 1 )
	main( sys.argv )

# generate.py
