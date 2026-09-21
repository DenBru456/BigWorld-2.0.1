#!/usr/bin/env python
"""
Module for checking versions, and determining and applying upgrade paths.
"""

import logging
from optparse import OptionParser
import os
import shutil
import sys
import tempfile
import time
import urllib
from xml.dom import minidom, Node
import zipfile


from patcherlib import md5_interface, patch_apply, utils
from patcherlib.command_line import DEFAULT_LOG_LEVEL, LOG_LEVELS

from versionslib.versions import VersionsXML
from versionslib.transfer import HTTPLogProgressListener, PatchTransferHandler
from versionslib.state import StateXML
from versionslib.simple_config import Config

log = logging.getLogger( "check_version" )

DEFAULT_DOWNLOAD_DIR = "downloads"


def checkVersion( versionsURL, state ):
	"""
	Check this version against the versions file on the remote server.

	Return a tuple of the remote current version, and a VersionInfo object if
	an upgrade path is available for the state's current version, otherwise
	returns None if no upgrade path is necessary.

	@param versionsURL		the versions file URL (urllib must be able to
							recognise the scheme).
	@param state			the local distribution state, an implementation of
							the versionslib.state.State interface.
	"""

	# retrieve the versions.xml file and parse it
	log.debug( "checkVersion: versions URL = '%s'", versionsURL )
	versionsConn = urllib.urlopen( versionsURL )
	versionsContents = versionsConn.read()
	versionsConn.close()

	doc = minidom.parseString( versionsContents )
	versions = VersionsXML( doc )

	localVersion = state.getCurrentVersion()
	remoteVersion = versions.getCurrentVersion()

	log.debug( "checkVersion: localVersion='%s', remoteVersion='%s'",
		localVersion, remoteVersion )

	if localVersion == remoteVersion:
		log.info( "checkVersion: no upgrade necessary" )
		return None

	upgradePath = versions.getUpgradePath( localVersion )
	if not upgradePath:
		raise ValueError, "no upgrade path, even though remote version %s " \
			"is different to local %s" % (remoteVersion, localVersion)


	log.debug( "checkVersion: upgrade path exists" )
	return remoteVersion, upgradePath


def retrievePatch( target, progressListener=None ):
	"""
	Retrieve a patch archive for a patch target.

	@param target 				A versions.Target object.
	@param progressListener		None, or a
								versionslib.transfer.ProgressListener object
								that will be called back on with progress
								updates.
	"""

	log.debug( "retrievePatch: patch target name=%s",
		target.name )

	if not os.path.isdir( DEFAULT_DOWNLOAD_DIR ):
		os.mkdir( DEFAULT_DOWNLOAD_DIR )

	destPath = os.path.join( DEFAULT_DOWNLOAD_DIR, target.patchName )

	properties = target.getProperties()

	log.debug( "retrievePatch: got properties: %s",
		["%s=%s" % (key, value) for key, value in properties.items() ] )

	handler = PatchTransferHandler.create( target.transferType,
		destPath, **properties )
	handler.addProgressListener( progressListener )
	handler.retrieve()

	md5sum = md5_interface.md5( utils.getFileContents( destPath ) ).hexdigest()

	if md5sum != properties.get( "md5sum" ):
		raise ValueError, "retrieved patch from %s for target %s " \
			"did not match MD5 sum" % (destPath, target.name)
	else:
		log.debug( "retrievePatch: md5sum for patch %s (for target %s) matches", 
			destPath, target.name )

def applyUpgradePath( destVersion, upgradePath, state,
		progressListener ):
	"""
	Apply an upgrade path.

	@param destVersion			The destination version name.
	@param upgradePath			The upgrade path to apply, in the form of a
								versionslib.versions.UpgradePath object.
	@param state				The state object.
	@param progressListener 	The transfer handler progress listener, or
								None.
	"""

	log.debug( "applyUpgradePath: got %d targets", len( upgradePath.targets ) )

	for target in upgradePath.targets:
		retrievePatch( target, progressListener )

		sourceVersion = state.getTargetVersion( target.name )

		if sourceVersion != target.destVersion:
			if sourceVersion != target.sourceVersion:
				raise ValueError, \
					"starting version of %s (%s) does not match " \
					"patch start version (%s) or end version (%s)" % \
						(target.name, sourceVersion,
							target.sourceVersion,
							target.destVersion)

			applyPatch( target, state )

		# otherwise we have already applied this patch
	state.setCurrentVersion( destVersion )


def applyPatch( target, state ):
	"""
	Apply a downloaded patch to the patch target. This handles patching
	against ZIP archives by extracting it to a temporary directory, then
	invoking the patcherlib.patch_apply module to apply the patch file
	archive. The state is updated for each successful patch target applied.

	@param target	The versionslib.versions.Target object.
	@param state	The state, as an object implementing
					versionslib.state.StateInterface.
	"""
	patchPath = os.path.join( DEFAULT_DOWNLOAD_DIR, target.patchName )

	# apply patch against the source tree
	patchApply = patch_apply.PatchApply(
		state.getTargetVersion( target.name ),
		target.path,
		patchPath )
	patchApply.run()

	# adjust the state
	state.setTargetVersion( target.name, target.destVersion )

def retrieveURL( url ):
	"""
	Retrieves the contents of the given URL, and returns it.

	@param url		The URL to read.
	@return			The contents of the URL.
	"""
	conn = urllib.urlopen( url )
	contents = conn.read()
	conn.close()
	return contents


def doMain( versionsURL, state, progressListener ):
	"""
	The bare minimum for checking a version.

	@params versionsURL			The URL of the versions file.
	@params state				The state object, representing the state of
								targets already installed on the end-user
								distribution.
	@params progressListener 	Transfer handler progress listener.
	"""
	res = checkVersion( versionsURL, state )
	if not res == None:
		destVersion, upgradePath = res

		updateInfoURL = upgradePath.getProperties().get( 'updateInfoURL' )

		if updateInfoURL:
			# print out the upgrade info URL contents to stdout
			# developers could do something else with the URL, e.g.
			# set contents of a wxHTML widget
			try:
				log.info( retrieveURL( updateInfoURL ) )
			except:
				pass

		applyUpgradePath( destVersion, upgradePath, state,
			progressListener )
	return 0

if __name__ == "__main__":

	op = OptionParser()
	op.add_option( '--config', '-c', dest="configPath",
		default="patcher_config.xml",
		help="The patcher configuration file that contains the "
			"versions.xml URL. Defaults to \"%default\"." )
	op.add_option( '--state', '-s', dest="statePath",
		default="state.xml",
		help="The state file. Defaults to \"%default\"." )
	op.add_option( '--debug-level', dest="debugLevel",
		default="INFO",
		help="The logging debug level. Defaults to \"%default\"." )

	options, args = op.parse_args()

	if not options.debugLevel in LOG_LEVELS:
		print "Debug level must be one of %s" % ", ".join( LOG_LEVELS.keys() )
		sys.exit( 1 )

	debugLogLevel = LOG_LEVELS[options.debugLevel]

	logging.basicConfig( stream=sys.stdout, level=debugLogLevel )
	progressListener = HTTPLogProgressListener()

	log.info( "check_version started" )

	config = Config( options.configPath )
	log.debug( "config: %s",
		", ".join( "%s=%s" % item for item in config._dict.items() ) )

	state = StateXML( options.statePath )
	versionsURL = config.get( "versionsURL" )
	try:
		res = doMain( versionsURL, state, progressListener )
	except:
		import traceback
		log.error( traceback.format_exc() )
		sys.exit( 1 )

	sys.exit( res )

# check_version.py
