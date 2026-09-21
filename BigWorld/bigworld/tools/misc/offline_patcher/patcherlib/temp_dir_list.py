import shutil
import atexit
import os
import os.path
import logging

log = logging.getLogger( "patcherlib.temp_dir_list" )

import utils

class TempDirList( object ):
	"""
	Keeps track of files added to the temporary patch archive directory when
	constructing the contents of the patch archive. This list is then used when
	removing those temporary files.

	This class also handles adding files from an existing file, adding files
	from a string in memory, and also adding directories.
	"""
	def __init__( self, path ):
		"""
		Sets up the
		"""
		self.path = path
		self._removeCalled = False
		self._filePaths = []
		atexit.register( self.remove )

	def addFile( self, path, sourcePath ):
		"""
		Add a file to the patch directory by copying it from sourcePath.
		"""
		self.addPath( path )
		patchPath = os.path.join( self.path, path )
		shutil.copyfile( sourcePath, patchPath )

	def addPath( self, path ):
		"""
		Add a path to an existing file in the patch directory.
		"""
		self.addDirIfNotExist( os.path.dirname( path ) )
		self._filePaths.append( path )

	def writeFile( self, path, contents ):
		"""
		Write contents to a file.
		"""
		self.addPath( path )
		patchPath = os.path.join( self.path, path )
		utils.writeToFile( patchPath, contents )

	def _addDirIfNotExist( self, path ):
		if not os.path.exists( path ):
			os.makedirs( path )

	def addDirIfNotExist( self, path ):
		pathComponents = path.split( os.sep )
		parentPath = ''
		parentPaths = []

		# make sure the paths are in the right order for deletion
		for pathComponent in pathComponents:
			if parentPath:
				parentPath += os.sep
			parentPath += pathComponent
			parentPaths.insert( 0, parentPath )

		for parentPath in parentPaths:
			if not parentPath in self._filePaths:
				self._filePaths.append( parentPath )

			patchPath = os.path.join( self.path, parentPath )
			self._addDirIfNotExist( patchPath )

	def remove( self ):
		if self._removeCalled:
			return

		self._removeCalled = True
		for path in self._filePaths:
			absPath = os.path.join( self.path, path )
			if os.path.isfile( absPath ):
				os.remove( absPath )

		for path in self._filePaths:
			absPath = os.path.join( self.path, path )
			# at least one of these will be a leaf directory
			if os.path.exists( absPath ):
				if os.path.isdir( absPath ):
					try:
						os.removedirs( absPath )
					except:
						pass

# temp_dir_list.py

