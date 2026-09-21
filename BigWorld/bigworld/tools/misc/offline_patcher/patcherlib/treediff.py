#!/usr/bin/env python

"""
treediff module with class for TreeDiff
"""
import os
import stat
import logging
import md5_interface
import re

import utils

log = logging.getLogger( "patcherlib.treediff" )

DEFAULT_IGNORE_PATTERNS = [ r'CVS$', r'\.svn$', r'\.#[^/]+$' ]

class TreeDiffCallbackInterface:
	"""
	Interface class for callbacks used for TreeDiff instances.
	"""
	def onFileCreated( self, filePath ):
		"""
		Called when a new file in the destination directory is detected. The
		relative filePath is supplied.
		"""
		pass

	def onDirCreated( self, dirPath ):
		"""
		Called when a new directory in the destination directory is detected.
		The relative filePath is supplied.
		"""
		pass

	def onFileDeleted( self, filePath ):
		"""
		Called when a file in the source directory is missing from the
		destination directory. The relative filePath is supplied.
		"""
		pass

	def onDirDeleted( self, dirPath ):
		"""
		Called when a directory in the source tree is not present in the
		destination tree.
		"""
		pass


	def onFileModified( self, filePath, beforeSum, afterSum ):
		"""
		Called when a file in the destination directory contains binary
		differences to the corresponding file in the source directory. The
		relative filePath is supplied.

		If the TreeDiff instance was created with doMD5s=True, then MD5sums for
		the source and destination's versions are supplied, otherwise, they are
		set to None.
		"""
		pass

	def onFileCommon( self, filePath ):
		"""
		Called when a file is common to both the source directory and the
		destination directory. The relative filePath is supplied.
		"""
		pass

	def onDirCommon( self, dirPath ):
		"""
		Called when a directory is common to both the source directory and the
		destination directory. The relative dirPath is supplied.
		"""
		pass

class TreeDiff( object ):
	"""
	Class for diffing directories.
	"""
	def __init__( self, sourcePath, destPath, callback,
			ignorePatterns = DEFAULT_IGNORE_PATTERNS,
			doFileMD5s=True ):

		"""
		Constructor.

		@param sourcePath			The source hierarchy path.
		@param destPath				The destination hierarchy path.
		@param callback				An instance of TreeDiffCallbackInterface.
		@param ignorePatterns		A list of regular expression pattern of
									files to ignore.
		@param doFileMD5s			If True, calculate file MD5sums as well,
									otherwise, onFileModified will be passed
									None for its beforeSum and afterSum
									parameters.
		"""
		self._sourcePath = sourcePath
		self._destPath = destPath
		self._callback = callback
		self._ignorePatterns = ignorePatterns
		self._doFileMD5s = doFileMD5s

		log.info( "TreeDiff.__init__: %s %s", sourcePath, destPath )

	def run( self ):
		self._traverseTree( '' )

	def _traverseTree( self, relPath ):
		dirsLeft = [ relPath ]
		while dirsLeft:
			newPath = dirsLeft.pop( 0 )
			newOutDirs = self._traverseDir( newPath )
			# depth-first
			dirsLeft = newOutDirs + dirsLeft

	def _amIgnoring( self, relPath ):
		for pattern in self._ignorePatterns:
			if re.search( pattern, relPath ):
				return True
		return False

	def _traverseDir( self, relPath ):
		sourceRelPath = os.path.normpath(
			os.path.join( self._sourcePath, relPath ) )
		destRelPath = os.path.normpath(
			os.path.join( self._destPath, relPath ) )

		# get files in the current relPath in source tree
		sourceList = []
		if os.path.exists( sourceRelPath ):
			sourceList = [os.path.join( relPath, relFilePath )
				for relFilePath in os.listdir( sourceRelPath )
				if not self._amIgnoring( relFilePath ) ]

		# get files in the current relPath in destination tree
		destList = []
		if os.path.exists( destRelPath ):
			destList = [os.path.join( relPath, relFilePath )
				for relFilePath in os.listdir( destRelPath )
				if not self._amIgnoring( relFilePath ) ]

		# other dirs to traverse through to pass back to _traverseTree
		outDirs = []

		# get the files present in source tree not in dest tree
		for srcPath in sourceList:
			if not srcPath in destList:
				log.debug( "deleted: %s", srcPath )
				if os.path.isdir( os.path.join( self._sourcePath, srcPath ) ):
					self._callback.onDirDeleted( srcPath )

					# no need to traverse through this path as it's already
					# marked as being deleted

				else:
					self._callback.onFileDeleted( srcPath )

		# get the files present in dest tree but not in source tree
		for dstPath in destList:
			if not dstPath in sourceList:
				log.debug( "added: %s", dstPath )
				if os.path.isdir( os.path.join( self._destPath, dstPath ) ):
					self._callback.onDirCreated( dstPath )

					# traverse through this path now too
					outDirs.append( dstPath )
				else:
					self._callback.onFileCreated( dstPath )

		# check common files
		commonList = set( commonPath for commonPath in sourceList + destList
			if commonPath in sourceList and commonPath in destList )
		for commonPath in commonList:
			log.debug( "common: %s", commonPath )
			sourceCommonPath = os.path.join( self._sourcePath, commonPath )
			destCommonPath = os.path.join( self._destPath, commonPath )

			# check both are of the same type (dir, file)
			if os.path.isdir( sourceCommonPath ) != \
					os.path.isdir( destCommonPath ):
				if os.path.isdir( sourceCommonPath ):
					# deleting a directory !!
					self._callback.onDirDeleted( commonPath )
					self._callback.onFileCreated( commonPath )
				else:
					self._callback.onFileDeleted( commonPath )
					self._callback.onDirCreated( commonPath )
					outDirs.append( commonPath )
				continue

			if not os.path.isdir( sourceCommonPath ):
				# both paths are files
				# check for differences within the file itself
				if utils.filesHaveDiff( sourceCommonPath, destCommonPath ):
					beforeSum = None
					afterSum = None
					if self._doFileMD5s:
						# get digests
						h1 = TreeDiff._getMD5( sourceCommonPath )
						h2 = TreeDiff._getMD5( destCommonPath )
						beforeSum = h1.hexdigest()
						afterSum = h2.hexdigest()

					self._callback.onFileModified( commonPath,
						beforeSum, afterSum )
				else:
					# no diffs found
					self._callback.onFileCommon( commonPath )

			else:
				# both are dirs
				self._callback.onDirCommon( commonPath )
				# add to list of more dirs to check
				outDirs.append( commonPath )
		# end for path in commonList
		return outDirs


	@staticmethod
	def _getMD5( path ):
		h = md5_interface.md5()
		h.update( utils.getFileContents( path ) )
		return h

# treediff.py

