from lib.package_list_parser import PackageListParser
from lib.macro_expander import MacroExpander
from lib.version_file_parser import VersionFileParser
from lib.spec_template import SpecTemplate
import lib.svn_assistant as SVNAssistant

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

CLEANUP_TMP_FILE = "cleanup.tmp"
BINARY_RPM_TMP_FILE = "binary_rpm.tmp"

VERSION_FILE_PATH = "bigworld/res/version.xml"

log = logging.getLogger( 'rpm_builder' )


class RPMBuilder( object ):
	"""
	This class builds an RPM from a RPM spec file template, and a file list. It
	gathers the files specified by the file list, and creates a temporary build
	root directory, populated by those specified files. It then creates the RPM
	spec file from the template, and runs rpmbuild to create the RPM file,
	which is then copied to the given output directory.

	Once an object is initialised, use the build() method to actually trigger
	the build.
	"""

	def __init__( self, mfRoot, packageDir ):
		"""
		@param mfRoot 		The top-level directory for the BigWorld source
							distribution.
		@param packageDir 	The package name. This must be a directory under
							the current working directory, and it must also
							contain the file list (expected to be
							<PACKAGENAME>.lst) and template specification file
							(expected to be <PACKAGENAME>_template.spec).
		"""
		self.mfRoot = mfRoot
		self.packageDir = packageDir

		specTemplateFilePath = packageDir + "/" + packageDir + "_template.spec"

		self.specTemplate = SpecTemplate( specTemplateFilePath )
		self.macroExpander = self.specTemplate.macroExpander()

		fileListPath = packageDir + "/" + packageDir + ".lst"
		self.packageListParser = PackageListParser( fileListPath )

		versionFilePath = os.path.join( mfRoot, VERSION_FILE_PATH )
		version = VersionFileParser( versionFilePath )

		versionStrings = [version.major, version.minor]
		if not version.reserved is None:
			# 1.9 used additional reserved field to specify minor version,
			# 2.0 won't have this.
			versionStrings.append( version.reserved )

		versionString = ".".join( versionStrings )
		self.macroExpander['bw_version'] = versionString
		self.macroExpander['bw_patch'] = version.patch

		svnRevision = "r" + SVNAssistant.latestRevision( mfRoot )
		self.macroExpander['bw_svn_rev'] = svnRevision

		arch = MacroExpander.rpmExpand( '%{_arch}' )
		if arch == 'x86_64':
			self.macroExpander['mf_config'] = "Hybrid64"
		else:
			self.macroExpander['mf_config'] = "Hybrid"

		log.info( "Version: %s.%s (%s)", versionString, version.patch, arch )

		rpmsDir = MacroExpander.rpmExpand( '%{_rpmdir}' )
		name = self.macroExpander.expand( '%{name}' )

		# The expected output path from rpmbuild, unfortunately, this can't be
		# changed other than setting .rpmmacros.
		self.outputPath = os.path.join( rpmsDir, arch,
			"%(name)s-%(version)s.%(patch)s-%(patch)s.%(svnrev)s.%(arch)s.rpm" % \
				dict( name = name,
					version = versionString,
					patch = version.patch,
					svnrev = svnRevision,
					arch = arch ) )

		self.destFile = \
			"%(name)s-%(version)s.%(patch)s.%(arch)s.rpm" % \
				dict( name = name,
					version = versionString,
					patch = version.patch,
					arch = arch )


	def _rpmFiles( self ):
		return self.packageListParser.fileList( self.mfRoot, 
			self.macroExpander )

	def _populateBuildRoot( self, buildRoot ):
		for file in self._rpmFiles():
			file.apply( buildRoot, self.macroExpander,
				   self.packageListParser.filters.get( file.destination ) )

	def _createBuildRoot( self ):
		return tempfile.mkdtemp( "", "rpm_build_" + self.packageDir + "_", 
			"/tmp" )


	def _tearDownBuildRoot( self, buildRoot ):
		shutil.rmtree( buildRoot, ignore_errors=True )


	def _createSpecFile( self, buildRoot ):
		specFilePath = os.path.join( self.packageDir, 
			self.packageDir + ".spec" )

		self.specTemplate.writeSpecFile( specFilePath, buildRoot, 
			self._rpmFiles(), self.macroExpander )

		return specFilePath


	@staticmethod
	def _createRPM( specFilePath ):
		"""
		Use the rpmbuild command to build the RPM from a RPM spec file. This
		will output to a directory of rpmbuild's choosing.
		"""
		cmd = ['rpmbuild', '-bb', '-v', specFilePath]

		try:
			pipe = subprocess.Popen( cmd, 
				stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
		except OSError:
			print "Failed to execute %s. Make sure rpm-build is installed." % \
				cmd[0]
			sys.exit( 1 )

		output = ''

		# translate each output line into a log entry
		while pipe.poll() is None:
			output += pipe.stdout.read( 32 )
			lines = output.split( "\n" )
			if len( lines ) > 1:
				for line in lines[:-1]:
					log.info( "rpmbuild: %s", line )
				output = lines[-1]

		returnCode = pipe.wait()

		if not os.WIFEXITED( returnCode ) or os.WEXITSTATUS( returnCode ) != 0:
			raise ValueError, "rpmbuild returned code: %d" % returnCode


	def build( self, outputDir, tearDownRoot = True ):
		"""
		Build an RPM.

		@param outputDir 	The output directory where the RPM will be placed.
		"""

		buildRoot = self._createBuildRoot()
		specFilePath = None

		result = True

		try:
			log.info( "Populating build root" )
			self._populateBuildRoot( buildRoot )

			log.info( "Creating spec file" )
			specFilePath = self._createSpecFile( buildRoot )

			if not tearDownRoot:
				backupPath = "/tmp/" + os.path.basename( specFilePath )
				log.info( "Backing up spec file %s to %s" %
						( specFilePath, backupPath ) )
				shutil.copyfile( specFilePath, backupPath )

			log.info( "Creating RPM" )
			self._createRPM( specFilePath )

			if not os.path.exists( self.outputPath ):
				raise ValueError, \
					"Could not find built RPM at %s" % self.outputPath 

			shutil.move( self.outputPath, 
				os.path.join( outputDir, self.destFile ) )
			log.info( "Moved %s to %s", self.outputPath, outputDir )

			result = True
		except ValueError, e:
			print "Build failure:", str( e )
			result = False

		if tearDownRoot:
			log.info( "Tearing down build root" )
			self._tearDownBuildRoot( buildRoot )
			if not specFilePath is None:
				os.remove( specFilePath )
		else:
			log.info( "Not tearing down %s" % buildRoot )

		return result

# rpm_builder.py
