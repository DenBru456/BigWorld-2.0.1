"""
Module for handling command line invocations for patcher.
"""

from optparse import OptionParser
import logging
import sys
import os.path
import re
import time
import zipfile
import tempfile
import shutil

import utils

log = logging.getLogger( "patcherlib.command_line" )

DEFAULT_LOG_LEVEL = logging.getLevelName( logging.INFO )

LOG_LEVELS = dict( (logging.getLevelName( lvl ), lvl) for lvl in (
	logging.DEBUG,
	logging.INFO,
	logging.WARNING,
	logging.ERROR,
	logging.CRITICAL
) )
LOG_FORMAT = "%(created)f %(levelname)s %(name)s %(message)s"

def echoErr( msg, *args ):
	if args:
		print >> sys.stderr, msg % args
	else:
		print >> sys.stderr, msg

def buildPatch( args ):
	from treediff import DEFAULT_IGNORE_PATTERNS
	from patch_file_builder import PatchFileBuilder

	start = time.time()
	parser = OptionParser(usage=
"""usage: %prog [options] <source-path> <dest-path> <patch-output-path>
    where   <source-paths>          comma delimited list of source tree
                                    paths
            <dest-path>             the destination tree path
            <patch-output-path>     the patch output path
""" )
	parser.add_option( "--debug-level",
		action="store",
		type="string",
		dest="logLevel",
		help="one of %s" % ", ".join( LOG_LEVELS.keys() ),
		default="INFO")

	parser.add_option( "--source-version",
		action="store",
		type="string",
		dest="sourceVersion",
		help="a label for the source version (default the basename of " \
			"<source-path>)" )

	parser.add_option( "--use-checksums-if-unmodified",
		action="store_true",
		dest="useChecksumsIfUnmod",
		default=False,
		help="use checksums for unmodified files as well as modified files "\
			"(default is to not use checksums for unmodified files)" )

	parser.add_option( "--ignore-patterns",
		action="store",
		dest="ignorePatterns",
		default=None,
		help="ignore patterns when traversing the directory hierarchy "
				"(default %s). Use commas to delimit the patterns, "
				"use '\,' to use comma in a pattern." %
			"|".join( DEFAULT_IGNORE_PATTERNS ) )

	options, posArgs = parser.parse_args( args )

	if len( posArgs ) < 4:
		parser.print_help()
		return 1

	sourcePath, destPath, outPath = posArgs[1:4]

	# set up logging
	if options.logLevel and not options.logLevel in LOG_LEVELS:
		echoErr( "error: invalid log level '%s', must be one of '%s'",
			options.logLevel, "', '".join( LOG_LEVELS.keys() ) )
		return 1

	logging.basicConfig( stream=sys.stdout,
		level=LOG_LEVELS[options.logLevel],
		format=LOG_FORMAT )

	if not destPath or \
			not os.path.exists( destPath ) or \
			not os.path.isdir( destPath ):
		echoErr( "error: dest path invalid or not a dir: '%s'",
			destPath )
		return 1

	if not os.path.exists( sourcePath ) or \
				not os.path.isdir( sourcePath ):
		echoErr( "error: source path '%s' is invalid or not a dir",
			sourcePath )
		return 1

	if sourcePath[len( sourcePath ) - 1] == '/':
		sourcePath = sourcePath[0:len( sourcePath ) - 1]
	sourceVersion = os.path.basename( sourcePath )
	if options.sourceVersion:
		sourceVersion = options.sourceVersion

	ignorePatterns = DEFAULT_IGNORE_PATTERNS
	if not options.ignorePatterns is None:

		ignorePatterns = []

		patterns = options.ignorePatterns.split( "," )
		i = 0
		while i < len( patterns ):
			pattern = patterns[i]
			# double escaped backslashes for regexp as well as py string
			# i.e. "\\\\" for a regexp matches a single backslash

			# match start of line or anything that doesn't end in a backslash
			# followed by an odd number of backslashes
			matches = re.match( '((?:^|.*[^\\\\])(?:\\\\{2})*)\\\\$', pattern )
			if matches and \
					i < len( patterns ) - 1:
				# literal comma, coalesce with the next pattern, and redo
				patterns[i] = matches.group( 1 ) + "," + patterns[i + 1]
				del patterns[i + 1]
				continue
			else:
				# substitute double backslashes with single backslash
				pattern = re.sub( "\\\\\\\\", "\\\\", pattern )
				if pattern != "":
					ignorePatterns.append( pattern )
				i = i + 1

	log.debug( "ignorePatterns: [%s]",
		", ".join( "%r" % pattern for pattern in ignorePatterns ) )

	builder = PatchFileBuilder( sourcePath, destPath, outPath,
		sourceVersion=sourceVersion,
		useChecksumsIfUnmod=options.useChecksumsIfUnmod,
		ignorePatterns=ignorePatterns)
	builder.run()
	finish = time.time()
	log.info( "build took %.3fs", (finish - start) )
	return 0

def applyPatch( args ):
	from patch_apply import PatchApply

	parser = OptionParser(usage=
"""usage: %prog [options] <patch-path> <target-path> <target-version>
    where   <patch-path>            path to the patch archive
            <target-path>           destination tree path
            <target-version>        target version before patching
""" )

	parser.add_option( "--debug-level",
		action="store",
		type="string",
		dest="logLevel",
		help="one of %s" % ", ".join( LOG_LEVELS.keys() ),
		default="INFO")

	options, posArgs = parser.parse_args( args )
	if len( posArgs ) < 4:
		parser.print_help()
		return 1

	patchFilePath, sourcePath, sourceVersion = posArgs[1:4]

	logging.basicConfig( stream=sys.stdout,
		level=LOG_LEVELS[options.logLevel],
		format=LOG_FORMAT )

	start = time.time()
	pa = PatchApply( sourceVersion, sourcePath, patchFilePath )
	pa.run()
	finish = time.time()

	log.info( "patch took %.3fs", finish - start )

	return 0

# command_line.py

