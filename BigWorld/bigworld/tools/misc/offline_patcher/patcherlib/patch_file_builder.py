"""
Module for building patch file archives.
"""
import tarfile
import tempfile
import os
import stat
import logging
import shutil
from xml.dom import minidom

import md5_interface
from treediff import TreeDiff, TreeDiffCallbackInterface, \
	DEFAULT_IGNORE_PATTERNS
import bsdiff
import manifest
import utils
from temp_dir_list import TempDirList

log = logging.getLogger( "patcherlib.patch_file_builder" )


class TreeDiffCallback( TreeDiffCallbackInterface ):
	"""
	Callback for treediff.TreeDiff.  Used for building the patch file archive
	and the manifest.
	"""
	def __init__( self, manifest, patchDirList, sourcePath, destPath,
			sourceVersion, useChecksumsIfUnmod = False ):
		self._manifest = manifest
		self._sourcePath = sourcePath
		self._destPath = destPath
		self._sourceVersion = sourceVersion
		self._patchDirList = patchDirList
		self._useChecksumsIfUnmod = useChecksumsIfUnmod
		self._nextFileChangeID = 0

	def nextFileChangeID( self ):
		nextFileChangeID = self._nextFileChangeID
		self._nextFileChangeID += 1
		return "%08x" % nextFileChangeID

	def _archivePath( self, fileChangeID ):
		return os.path.join( "changes", self._sourceVersion, fileChangeID )

	def onDirCreated( self, filePath ):
		log.info( "Ad %s", filePath )
		self._manifest.addDirAddition( self._sourceVersion, filePath )

	def onDirDeleted( self, filePath ):
		log.info( "Dd %s", filePath )
		self._manifest.addDirDeletion( self._sourceVersion, filePath )

	def onFileCreated( self, filePath ):
		log.info( "Af %s", filePath )
		fileChangeID = self.nextFileChangeID()
		self._manifest.addFileAddition( self._sourceVersion, filePath,
			fileChangeID )
		archivePath = self._archivePath( fileChangeID )
		utils.bzipCompressFile( os.path.join( self._destPath, filePath ),
			os.path.join( self._patchDirList.path, archivePath ) )
		self._patchDirList.addPath( archivePath )

	def onFileDeleted( self, filePath ):
		log.info( "Df %s", filePath )
		self._addChecksum( filePath )
		self._manifest.addFileDeletion( self._sourceVersion, filePath )

	def onFileModified( self, filePath, beforeSum, afterSum ):
		log.info( "Mf %s", filePath )
		fileChangeID = self.nextFileChangeID()
		self._manifest.addFileModification( self._sourceVersion, filePath,
			fileChangeID,
			beforeSum, afterSum, manifest.MOD_TYPE_BINARY_BSDIFF )
		archivePath = self._archivePath( fileChangeID )
		self._patchDirList.addPath( archivePath )
		bsdiff.diffFilesToFile( os.path.join( self._sourcePath, filePath ),
			os.path.join( self._destPath, filePath ),
			os.path.join( self._patchDirList.path, archivePath ) )

	def onFileCommon( self, filePath ):
		log.info( "Cf %s", filePath )
		if self._useChecksumsIfUnmod:
			self._addChecksum( filePath )

	def _addChecksum( self, filePath ):
		h = md5_interface.md5()
		h.update( utils.getFileContents(
			os.path.join( self._sourcePath, filePath ) ) )
		log.info( "%s %s", filePath, h.hexdigest() )
		self._manifest.addChecksum( self._sourceVersion,
			filePath, h.hexdigest() )


class PatchFileBuilder( object ):
	"""
	Class for building a patch file archive.
	"""
	def __init__( self, sourcePath, destPath, outFilePath,
			sourceVersion,
			useChecksumsIfUnmod=False,
			ignorePatterns=DEFAULT_IGNORE_PATTERNS ):
		"""
		@param sourcePath			The source path.
		@param destPath 			The destination path.
		@param outFilePath			The output file path.
		@param sourceVersion		The source version label.
		@param useChecksumsIfUnmod	Use checksums for verification even if
									files are unmodified.
		@param ignorePatterns		Ignore files whose names match at least
									one of these patterns.
		"""
		self._sourcePath = sourcePath
		self._sourceVersion = sourceVersion

		self._destPath = destPath
		self._useChecksumsIfUnmod = useChecksumsIfUnmod
		self._ignorePatterns = ignorePatterns

		self._tempPatchDir = tempfile.mkdtemp( prefix="bw-patch-" )
		self._patchDirList = TempDirList( self._tempPatchDir )

		self._manifest = None

		if os.path.exists( outFilePath ):
			# Extract all contents of the existing tar file, so we can add to
			# it.
			tarFile = tarfile.open( outFilePath, "r" )
			for member in tarFile.getmembers():
				tarFile.extract( member, self._tempPatchDir )

				if member.name == "manifest":
					# existing manifest
					manifestFile = open(
						os.path.join( self._tempPatchDir, "manifest" ), "r" )
					manifestContents = manifestFile.read()
					manifestFile.close()
					self._manifest = manifest.Manifest.fromXML(
						minidom.parseString( manifestContents ) )
					log.info( "loaded existing manifest: sourceVersions = %s",
						", ".join( self._manifest.sourceVersions.keys() ) )
					if self._sourceVersion in self._manifest.sourceVersions:
						tarFile.close()
						raise ValueError, "Archive already has a source "\
							"version labelled '%s'" % self._sourceVersion
			tarFile.close()

		self._outFile = tarfile.open( outFilePath, "w" )

		if not self._manifest: # didn't load from existing archive
			self._manifest = manifest.Manifest()

		self._done = False


	def run( self ):
		if self._done:
			raise ValueError, "Already run"

		self._patchDirList.addDirIfNotExist( "changes" )
		self._patchDirList.addDirIfNotExist( os.path.join( "changes",
			 self._sourceVersion ) )

		self._manifest.addSourceVersion( self._sourceVersion )

		# do the diffs
		log.info( "%s: doing diffs", self._sourceVersion )
		callback = TreeDiffCallback( self._manifest, self._patchDirList,
			self._sourcePath, self._destPath, self._sourceVersion,
			self._useChecksumsIfUnmod )
		treeDiff = TreeDiff( self._sourcePath, self._destPath, callback,
			ignorePatterns=self._ignorePatterns )
		treeDiff.run()


		# finalise the archive with manifest
		doc = self._manifest.toXML()
		self._patchDirList.writeFile( "manifest", doc.toxml() )


		for filename in os.listdir( self._tempPatchDir ):
			log.info( "add to archive: %s", filename )
			self._outFile.add( os.path.join( self._tempPatchDir, filename ),
				filename,
				recursive=True )

		self._outFile.close()

		self._patchDirList.remove()


# patch_file_builder.py

