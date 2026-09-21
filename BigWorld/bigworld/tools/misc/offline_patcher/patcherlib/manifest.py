"""
Module for patch archive manifests.
"""

from xml.dom import minidom
import logging
import tempfile

import utils

log = logging.getLogger( "patcherlib.manifest" )

OP_ADDFILE 		= 1
OP_DELFILE 		= 2
OP_MODFILE 		= 3
OP_ADDDIR		= 4
OP_DELDIR		= 5

OPS_ALL = frozenset(
	(OP_ADDFILE, OP_DELFILE, OP_MODFILE, OP_ADDDIR, OP_DELDIR)
)

# You can define other methods of diffing/patching here. You'll also want to
# change FileModification.modTypeFromString() and
# FileModification.modtypeToString().

MOD_TYPE_BINARY_BSDIFF 		= 0 	# Use bsdiff to diff and patch.

class ManifestFileBuilder( object ):
	def __init__( self ):
		self._supportedVersions = {}

		self._document = minidom.Document()

		rootElement = self._document.createElement( "root" )
		self._document.appendChild( rootElement )

		self._sourceVersionsElement = \
			self._document.createElement( "sourceVersions" )
		rootElement.appendChild( self._sourceVersionsElement )

	def addManifest( self, manifest ):
		for versionName, sourceVersion in manifest.sourceVersions.iteritems():
			log.info( "builder adding version: %s", versionName )
			if versionName not in self._supportedVersions:
				self.addSupportedVersion( versionName )

			sourceVersionElement = self._supportedVersions[versionName]

			checksumsElement = \
				sourceVersionElement.getElementsByTagName( "checksums" )[0]
			addElement = \
				sourceVersionElement.getElementsByTagName( "added" )[0]
			delElement = \
				sourceVersionElement.getElementsByTagName( "deleted" )[0]
			modElement = \
				sourceVersionElement.getElementsByTagName( "modified" )[0]

			self.setNumOperations( versionName,
				manifest.getNumOperations( versionName ) )

			for fileChecksum in sourceVersion.fileChecksums:
				log.info( "builder adding checksum: %s", fileChecksum.path )
				self._addChecksum( checksumsElement,
					fileChecksum.path, fileChecksum.checksum )

			for path in sourceVersion.dirAdditions:
				log.info( "builder adding dir addition: %s", path )
				self._addOperation( addElement, OP_ADDDIR, path )

			for path in sourceVersion.dirDeletions:
				log.info( "builder adding dir deletion: %s", path )
				self._addOperation( delElement,	OP_DELDIR, path )

			for fileAddition in sourceVersion.fileAdditions:
				log.info( "builder adding file addition: %s", fileAddition.path )
				self._addOperation( addElement,	OP_ADDFILE, 
					fileAddition.path, fileAddition.fileChangeID )

			for path in sourceVersion.fileDeletions:
				log.info( "builder adding file deletion: %s", path )
				self._addOperation( delElement,	OP_DELFILE, path )

			for fileMod in sourceVersion.fileModifications:
				log.info( "builder adding file mod: %s", fileMod.path )
				self._addOperation( modElement,
					OP_MODFILE,
					fileMod.path,
					fileMod.fileChangeID,
					dict( 	beforeSum=fileMod.beforeSum,
							afterSum=fileMod.afterSum,
							modType=fileMod.modTypeToString() ) )



	def addSupportedVersion( self, versionName ):
		if not versionName in self._supportedVersions:
			sourceVersionElement = self._document.createElement( "version" )
			self._sourceVersionsElement.appendChild( sourceVersionElement )
			self._supportedVersions[versionName] = sourceVersionElement

			nameElement = self._document.createElement( "name" )
			nameElement.appendChild(
				self._document.createTextNode( versionName ) )
			sourceVersionElement.appendChild( nameElement )
			numOperationsElement = \
				self._document.createElement( "numOperations" )
			sourceVersionElement.appendChild( numOperationsElement )
			checksumsElement = self._document.createElement( "checksums" )
			sourceVersionElement.appendChild( checksumsElement )
			modElement = self._document.createElement( "modified" )
			sourceVersionElement.appendChild( modElement )
			addElement = self._document.createElement( "added" )
			sourceVersionElement.appendChild( addElement )
			delElement = self._document.createElement( "deleted" )
			sourceVersionElement.appendChild( delElement )

			self._supportedVersions[versionName] = sourceVersionElement

		else:
			raise ValueError( "version is already supported" )


	def setNumOperations( self, version, numOperations ):
		sourceVersionElement = self._supportedVersions[version]
		numOperationsElement = sourceVersionElement.getElementsByTagName(
			"numOperations" )[0]
		if numOperationsElement.childNodes:
			numOperationsElement.firstChild.nodeValue = str( numOperations )
		else:
			numElement = self._document.createTextNode( str( numOperations ) )
			numOperationsElement.appendChild( numElement )

	def addChecksum( self, version, path, checksum ):
		if version not in self._supportedVersions:
			raise ValueError, "version %s is not supported" % (version)
		sourceVersionElement = self._supportedVersions[version]
		checksumsElement = sourceVersionElement.getElementsByTagName(
			"checksums" )[0]
		self._addChecksum( checksumsElement, path, checksum )

	def _addChecksum( self, checksumsElement, path, checksum ):
		fileElement = self._document.createElement( "file" )

		pathElement = self._document.createElement( "path" )
		pathElement.appendChild( self._document.createTextNode( path ) )

		checksumElement = self._document.createElement( "checksum" )
		checksumElement.appendChild( self._document.createTextNode( checksum ) )

		fileElement.appendChild( pathElement )
		fileElement.appendChild( checksumElement )
		checksumsElement.appendChild( fileElement )


	def addOperation( self, version, code, path, fileChangeID=None, 
			additional={} ):
		if version not in self._supportedVersions:
			raise ValueError, "version %s is not supported" % (version)
		if not code in OPS_ALL:
			raise ValueError, "code does not specify a valid operation"

		sourceVersionElement = self._supportedVersions[version]
		if code == OP_ADDFILE:
			opElement = sourceVersionElement.getElementsByTagName( "added" )[0]
			fileNode = self._document.createElement( "file" )
		elif code == OP_DELFILE:
			opElement = \
				sourceVersionElement.getElementsByTagName( "deleted" )[0]
			fileNode = self._document.createElement( "file" )
		elif code == OP_MODFILE:
			opElement = \
				sourceVersionElement.getElementsByTagName( "modified" )[0]
			fileNode = self._document.createElement( "file" )
		elif code == OP_ADDDIR:
			opElement = sourceVersionElement.getElementsByTagName( "added" )[0]
			fileNode = self._document.createElement( "dir" )
		elif code == OP_DELDIR:
			opElement = \
				sourceVersionElement.getElementsByTagName( "deleted" )[0]
			fileNode = self._document.createElement( "dir" )
		else:
			raise ValueError, "code is not implemented"

		self._addOperation( opElement, path, fileChangeID, additional )

	def _addOperation( self, opListElement, code, path, fileChangeID = None, 
			additional = {} ):
		if code == OP_ADDDIR or code == OP_DELDIR:
			fileNode = self._document.createElement( "dir" )
		else:
			fileNode = self._document.createElement( "file" )

		opListElement.appendChild( fileNode )

		pathNode = self._document.createElement( "path" )
		canonicalPath = utils.hostToCanonicalPathSep( path )
		pathNode.appendChild( self._document.createTextNode( canonicalPath ) )
		fileNode.appendChild( pathNode )

		if not fileChangeID is None:
			fileChangeIDNode = self._document.createElement( "fileChangeID" )
			fileChangeIDNode.appendChild( self._document.createTextNode( 
				fileChangeID ) )
			fileNode.appendChild( fileChangeIDNode )

		for tagName, tagValue in additional.iteritems():
			additionalElement = self._document.createElement( tagName )
			additionalElement.appendChild(
				self._document.createTextNode( tagValue ) )
			fileNode.appendChild( additionalElement )

	def document( self ):
		return self._document


class FileAddition( object ):
	"""
	Class for representing a file addition.
	"""
	def __init__( self, path, fileChangeID ):
		self.path = path
		self.fileChangeID = fileChangeID


class FileModification( object ):
	"""
	Class for representing a file modification with MD5 checksum checking.
	"""
	def __init__( self, path, fileChangeID, beforeSum, afterSum, modType ):
		self.path = path
		self.fileChangeID = fileChangeID
		self.beforeSum = beforeSum
		self.afterSum = afterSum
		self.modType = modType

	def modTypeToString( self ):
		if self.modType == MOD_TYPE_BINARY_BSDIFF:
			return "binary/bsdiff"
		else:
			raise ValueError, "invalid modification type"

	@staticmethod
	def modTypeFromString( modTypeString ):
		modTypeString = modTypeString.strip()
		if modTypeString == "binary/bsdiff":
			return MOD_TYPE_BINARY_BSDIFF
		else:
			raise ValueError, "no such modification type \"%s\"" % modTypeString

class FileChecksum( object ):
	"""
	Class for representing a file and its MD5sum for pre-patch checks.
	"""
	def __init__( self, path, checksum ):
		self.path = path
		self.checksum = checksum

class VersionPatchManifest( object ):
	"""
	Version-specific manifest.
	"""
	def __init__( self, versionName ):
		# the version for this version-specific manifest
		self.versionName = versionName

		# list of FileChecksum instances
		self.fileChecksums = []

		# lists of paths
		self.dirAdditions = []
		self.dirDeletions = []
		self.fileAdditions = []
		self.fileDeletions = []

		# list of FileModification instances
		self.fileModifications = []

	def addDirAddition( self, path ):
		self.dirAdditions.append( path )

	def addDirDeletion( self, path ):
		self.dirDeletions.append( path )

	def addFileAddition( self, path, fileChangeID ):
		self.fileAdditions.append( FileAddition( path, fileChangeID ) )

	def addFileDeletion( self, path ):
		self.fileDeletions.append( path )

	def addFileModification( self, path, fileChangeID, 
			beforeSum, afterSum, modType ):
		self.fileModifications.append(
			FileModification( path, fileChangeID, beforeSum, afterSum, modType ) )

	def addFileChecksum( self, path, checksum ):
		self.fileChecksums.append( FileChecksum( path, checksum ) )



class Manifest( object ):
	"""
	Manifest for a multi-version patch archive.
	"""
	def __init__( self ):
		# dict of version names to VersionPatchManifest instances
		self.sourceVersions = {}

	def addSourceVersion( self, versionName ):
		self.sourceVersions[versionName] = VersionPatchManifest( versionName )

	def addDirAddition( self, version, path ):
		sourceVersion = self._getVersion( version )
		log.info( "add version %s dir %s", version, path )
		sourceVersion.addDirAddition( path )

	def addDirDeletion( self, version, path ):
		sourceVersion = self._getVersion( version )
		log.info( "del version %s dir %s", version, path )
		sourceVersion.addDirDeletion( path )

	def addFileAddition( self, version, path, fileChangeID ):
		sourceVersion = self._getVersion( version )
		log.info( "add version %s file %s [%s]", version, path, fileChangeID )
		sourceVersion.addFileAddition( path, fileChangeID )

	def addFileDeletion( self, version, path ):
		sourceVersion = self._getVersion( version )
		log.info( "del version %s file %s", version, path )
		sourceVersion.addFileDeletion( path )

	def addFileModification( self, version, path, fileChangeID,
			beforeSum, afterSum, modType ):

		sourceVersion = self._getVersion( version )
		log.info( "mod version %s file %s [%s] (%s => %s)", version, path, 
			fileChangeID, beforeSum, afterSum )
		sourceVersion.addFileModification( path, fileChangeID, 
			beforeSum, afterSum, modType )

	def addChecksum( self, version, path, checksum ):
		sourceVersion = self._getVersion( version )
		log.info( "add checksum %s file %s (%s)", version, path, checksum )
		sourceVersion.addFileChecksum( path, checksum )

	def _getVersion( self, version ):
		if not version in self.sourceVersions:
			raise ValueError, "unknown source version '%s'" % (version)
		return self.sourceVersions[version]

	@staticmethod
	def _getChildValue( elt, childName ):
		"""
		Get an element's child's text, and return a stripped version of it.
		"""
		child = elt.getElementsByTagName( childName )[0]
		return child.firstChild.nodeValue.strip()

	@staticmethod
	def fromXML( document ):
		root = document.documentElement

		totalOps = int( Manifest._getChildValue( root, "numOperations" ) )
		out = Manifest()

		sourceVersionsElement = root.getElementsByTagName( "sourceVersions" )[0]

		for srcVersionElt in \
				sourceVersionsElement.getElementsByTagName( "version" ):

			sourceVersion = Manifest._getChildValue( 
				srcVersionElt, "name" )

			out.addSourceVersion( sourceVersion )

			# read the additions
			for addElement in srcVersionElt.getElementsByTagName( "added" ):
				for dirElement in addElement.getElementsByTagName( "dir" ):
					out.addDirAddition( sourceVersion,
						Manifest._getChildValue( dirElement, "path" ) )
				for fileElement in addElement.getElementsByTagName( "file" ):
					out.addFileAddition( sourceVersion,
						Manifest._getChildValue( fileElement, "path" ),
						Manifest._getChildValue( fileElement, 
							"fileChangeID" ) )

			# read the deletions
			for delElement in \
					srcVersionElt.getElementsByTagName( "deleted" ):
				for dirElement in delElement.getElementsByTagName( "dir" ):
					out.addDirDeletion( sourceVersion,
						Manifest._getChildValue( dirElement, "path" ) )
				for fileElement in delElement.getElementsByTagName( "file" ):
					out.addFileDeletion( sourceVersion,
						Manifest._getChildValue( fileElement, "path" ) )

			# read the modifications
			for modElement in \
					srcVersionElt.getElementsByTagName( "modified" ):
				for element in modElement.childNodes:
					if element.nodeName == "file":
						path = Manifest._getChildValue( element, "path" )
						fileChangeID = Manifest._getChildValue( element, 
							"fileChangeID" )
						beforeSum = Manifest._getChildValue( element, 
							"beforeSum" )
						afterSum = Manifest._getChildValue( element, 
							"afterSum" )
						modTypeString = Manifest._getChildValue( element,
							"modType" )
						out.addFileModification( sourceVersion,
							path, fileChangeID, beforeSum, afterSum,
							FileModification.modTypeFromString( 
								modTypeString ) )

			# read the unmodified files' checksums
			for checkElement in \
					srcVersionElt.getElementsByTagName( "checksums" ):
				for element in checkElement.childNodes:
					if element.nodeName == "file":
						out.addChecksum( sourceVersion,
							Manifest._getChildValue( element, "path" ),
							Manifest._getChildValue( element, 
								"checksum" ) )
		return out


	def getNumOperations( self, sourceVersion ):
		sourceVersion = self.sourceVersions[sourceVersion]
		return len( sourceVersion.fileChecksums ) + \
			len( sourceVersion.dirAdditions ) + \
			len( sourceVersion.dirDeletions ) + \
			len( sourceVersion.fileAdditions ) + \
			len( sourceVersion.fileDeletions ) + \
			len( sourceVersion.fileModifications )

	def toXML( self ):
		builder = ManifestFileBuilder()
		builder.addManifest( self )
		return builder.document()

# manifest.py

