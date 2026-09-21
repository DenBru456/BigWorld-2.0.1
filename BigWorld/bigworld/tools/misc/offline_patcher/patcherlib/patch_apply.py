"""
Module for applying patches.
"""
import logging
import os
import shutil
import stat
import tarfile
import tempfile
import xml.sax
import zipfile

import bsdiff
import manifest
from manifest import Manifest, FileAddition, FileModification, FileChecksum
import md5_interface
import utils

from temp_dir_list import TempDirList

log = logging.getLogger( "patcherlib.patch_apply" )

CHECK_CHECKSUMS = True

class PatchApplyCallbackInterface( object ):
	def onStart( self, numOperations ):
		pass
	def onFileAddStart( self, path ):
		pass
	def onFileAddFinish( self, path ):
		pass
	def onFileModStart( self, path ):
		pass
	def onFileModFinish( self, path ):
		pass
	def onFileDelStart( self, path ):
		pass
	def onFileDelFinish( self, path ):
		pass

	def onDirAddStart( self, path ):
		pass
	def onDirAddFinish( self, path ):
		pass
	def onDirDelStart( self, path ):
		pass
	def onDirDelFinish( self, path ):
		pass

	def onFinish( self ):
		pass

class DelegatingContentHandler( object ):

	def __init__( self, callback, userArgs = None ):
		self._callback = callback
		self._userArgs = userArgs
		self._delegate = None

	def notify( self, *args ):
		try:
			self._callback( *(args + (self._userArgs,)) )
		except:
			log.error( "DelegatingContentHandler.notify: %r failed", 
				self._callback )
			raise

	def delegate( self, delegateObj ):
		self._delegate = delegateObj

	def setDocumentLocator( self, locator ):
		"""
		Called by the parser to give the application a locator for locating the
		origin of document events.

		SAX parsers are strongly encouraged (though not absolutely required) to
		supply a locator: if it does so, it must supply the locator to the
		application by invoking this method before invoking any of the other
		methods in the DocumentHandler interface.

		The locator allows the application to determine the end position of any
		document-related event, even if the parser is not reporting an error.
		Typically, the application will use this information for reporting its
		own errors (such as character content that does not match an
		application's business rules). The information returned by the locator
		is probably not sufficient for use with a search engine.

		Note that the locator will return correct information only during the
		invocation of the events in this interface. The application should not
		attempt to use it at any other time.
		"""
		if self._delegate and hasattr( self._delegate, "setDocumentLocator" ):
			self._delegate.setDocumentLocator( locator )
		elif hasattr( self, "doSetDocumentLocator" ):
			self.doSetDocumentLocator( locator )

	def startDocument( self ):
		"""
		Receive notification of the beginning of a document.

		The SAX parser will invoke this method only once, before any other
		methods in this interface or in DTDHandler (except for
		setDocumentLocator()).
		"""
		if self._delegate and hasattr( self._delegate, "startDocument" ):
			self._delegate.startDocument()
		elif hasattr( self, "doStartDocument" ):
			self.doStartDocument()


	def endDocument( self ):
		"""
		Receive notification of the end of a document.

		The SAX parser will invoke this method only once, and it will be the
		last method invoked during the parse. The parser shall not invoke this
		method until it has either abandoned parsing (because of an
		unrecoverable error) or reached the end of input.
		"""
		if self._delegate and hasattr( self._delegate, "endDocument" ):
			self._delegate.endDocument()
		elif hasattr( self, "doEndDocument" ):
			self.doEndDocument()


	def startPrefixMapping( self, prefix, uri ):
		"""
		Begin the scope of a prefix-URI Namespace mapping.

		The information from this event is not necessary for normal Namespace
		processing: the SAX XML reader will automatically replace prefixes for
		element and attribute names when the feature_namespaces feature is
		enabled (the default).

		There are cases, however, when applications need to use prefixes in
		character data or in attribute values, where they cannot safely be
		expanded automatically; the startPrefixMapping() and endPrefixMapping()
		events supply the information to the application to expand prefixes in
		those contexts itself, if necessary.

		Note that startPrefixMapping() and endPrefixMapping() events are not
		guaranteed to be properly nested relative to each-other: all
		startPrefixMapping() events will occur before the corresponding
		startElement() event, and all endPrefixMapping() events will occur
		after the corresponding endElement() event, but their order is not
		guaranteed.
		"""
		if self._delegate and hasattr( self._delegate, "startPrefixMapping" ):
			self._delegate.startPrefixMapping( prefix, uri )
		elif hasattr( self, "doStartPrefixMapping" ):
			self.doStartPrefixMapping( prefix, uri )

	def endPrefixMapping( self, prefix ):
		"""
		End the scope of a prefix-URI mapping.

		See startPrefixMapping() for details. This event will always occur
		after the corresponding endElement() event, but the order of
		endPrefixMapping() events is not otherwise guaranteed.
		"""
		if self._delegate and hasattr( self._delegate, "endPrefixMapping" ):
			self._delegate.endPrefixMapping( prefix )
		elif hasattr( self, "doEndPrefixMapping" ):
			self.doEndPrefixMapping( prefix )

	def startElement( self, name, attrs ):
		"""
		Signals the start of an element in non-namespace mode.

		The name parameter contains the raw XML 1.0 name of the element type as
		a string and the attrs parameter holds an object of the Attributes
		interface containing the attributes of the element. The object passed
		as attrs may be re-used by the parser; holding on to a reference to it
		is not a reliable way to keep a copy of the attributes. To keep a copy
		of the attributes, use the copy() method of the attrs object.
		"""
		if self._delegate and hasattr( self._delegate, "startElement" ):
			self._delegate.startElement( name, attrs )
		elif hasattr( self, "doStartElement" ):
			self.doStartElement( name, attrs )

	def endElement( self, name ):
		"""
		Signals the end of an element in non-namespace mode.

		The name parameter contains the name of the element type, just as with
		the startElement() event.
		"""
		if self._delegate and hasattr( self._delegate, "endElement" ):
			self._delegate.endElement( name )
		elif hasattr( self, "doEndElement" ):
			self.doEndElement( name )

	def startElementNS( name, qname, attrs ):
		"""
		Signals the start of an element in namespace mode.

		The name parameter contains the name of the element type as a (uri,
		localname) tuple, the qname parameter contains the raw XML 1.0 name
		used in the source document, and the attrs parameter holds an instance
		of the AttributesNS interface containing the attributes of the element.
		If no namespace is associated with the element, the uri component of
		name will be None. The object passed as attrs may be re-used by the
		parser; holding on to a reference to it is not a reliable way to keep a
		copy of the attributes. To keep a copy of the attributes, use the
		copy() method of the attrs object.

		Parsers may set the qname parameter to None, unless the
		feature_namespace_prefixes feature is activated.
		"""
		if self._delegate and hasattr( self._delegate, "startElementNS" ):
			self._delegate.startElementNS( name, qname, attrs )
		elif hasattr( self, "doStartElementNS" ):
			self.doStartElementNS( name, qname, attrs )

	def endElementNS( self, name, qname ):
		"""
		Signals the end of an element in namespace mode.

		The name parameter contains the name of the element type, just as with
		the startElementNS() method, likewise the qname parameter.
		"""
		if self._delegate and hasattr( self._delegate, "endElementNS" ):
			self._delegate.endElementNS( name, qname )
		elif hasattr( self, "doEndElementNS" ):
			self.doEndElementNS( name, qname )


	def characters( self, content ):
		"""
		Receive notification of character data.

		The Parser will call this method to report each chunk of character
		data. SAX parsers may return all contiguous character data in a single
		chunk, or they may split it into several chunks; however, all of the
		characters in any single event must come from the same external entity
		so that the Locator provides useful information.

		content may be a Unicode string or a byte string; the expat reader
		module produces always Unicode strings.

		Note: The earlier SAX 1 interface provided by the Python XML Special
		Interest Group used a more Java-like interface for this method. Since
		most parsers used from Python did not take advantage of the older
		interface, the simpler signature was chosen to replace it. To convert
		old code to the new interface, use content instead of slicing content
		with the old offset and length parameters.
		"""
		if self._delegate and hasattr( self._delegate, "characters" ):
			self._delegate.characters( content )
		elif hasattr( self, "doCharacters" ):
			self.doCharacters( content )

	def ignorableWhitespace( self, whitespace ):
		"""
		Receive notification of ignorable whitespace in element content.

		Validating Parsers must use this method to report each chunk of
		ignorable whitespace (see the W3C XML 1.0 recommendation, section
		2.10): non-validating parsers may also use this method if they are
		capable of parsing and using content models.

		SAX parsers may return all contiguous whitespace in a single chunk, or
		they may split it into several chunks; however, all of the characters
		in any single event must come from the same external entity, so that
		the Locator provides useful information.
		"""
		if self._delegate and hasattr( self._delegate, "ignorableWhitespace" ):
			self._delegate.ignorableWhitespace( whitespace )
		elif hasattr( self, "doIgnorableWhitespace " ):
			self.doIgnorableWhitespace( whitespace )

	def processingInstruction( self, target, data ):
		"""
		Receive notification of a processing instruction.

		The Parser will invoke this method once for each processing instruction
		found: note that processing instructions may occur before or after the
		main document element.

		A SAX parser should never report an XML declaration (XML 1.0, section
		2.8) or a text declaration (XML 1.0, section 4.3.1) using this method.
		"""
		if self._delegate and hasattr( self._delegate,
				"processingInstruction" ):
			self._delegate.processingInstruction( target, data )
		elif hasattr( self, "doProcessingInstruction" ):
			self.doProcessingInstruction( target, data )

	def skippedEntity( self, name ):
		"""
		Receive notification of a skipped entity.

		The Parser will invoke this method once for each entity skipped.
		Non-validating processors may skip entities if they have not seen the
		declarations (because, for example, the entity was declared in an
		external DTD subset). All processors may skip external entities,
		depending on the values of the feature_external_ges and the
		feature_external_pes properties.
		"""
		if self._delegate and hasattr( self._delegate, "skippedEntity" ):
			self._delegate.skippedEntity( name )


class LeafElementHandler( object ):
	def __init__( self, name, callback, userArgs = None ):
		self._characters = ""
		self._name = name
		self._callback = callback
		self._userArgs = userArgs

	def startElement( self, name, attrs ):
		raise ValueError, "Not a leaf element"

	def endElement( self, name ):
		if name != self._name:
			raise ValueError, "Wrong end element"
		#log.debug( "LeafElementHandler: '%s': '%s'", self._name,
		#	self._characters )
		self._callback( self._name, self._characters, self._userArgs )

	def characters( self, content ):
		#log.debug( "LeafElementHandler: characters = '%s'", content )
		self._characters += content

	def ignorableWhitespace( self, whitespace ):
		#log.debug( "LeafElementHandler: whitespace = '%s'", whitespace )
		self._characters += whitespace

class SkipToElementEndHandler( object ):
	def __init__( self, name, callback, userArgs = None ):
		log.debug( "SkipToElementEndHandler" )
		self._name = name
		self._callback = callback
		self._userArgs = userArgs
		self._nestLevel = 1

	def startElement( self, name, attr ):
		self._nestLevel += 1

	def endElement( self, name ):
		self._nestLevel -= 1
		if self._nestLevel == 0:
			if name != self._name:
				raise ValueError, "Unexpected name: '%s', expecting '%s'" %\
					(name, self._name)
			self._callback( self._userArgs )

class FileHandler( DelegatingContentHandler ):
	def __init__( self, callback, userArgs = None ):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._path = None
		self._fileChangeID = None
		self._extras = {}
		self._nestLevel = 1

	def doStartElement( self, name, attrs ):
		if name == "path":
			if not self._path is None:
				raise ValueError, "duplicate path"
			self.delegate( LeafElementHandler( name, self.onPath ) )
		elif name == "fileChangeID":
			if not self._fileChangeID is None:
				raise ValueError, "duplicate file change ID"
			self.delegate( LeafElementHandler( name, self.onFileChangeID ) )
		else:
			if name in self._extras:
				raise ValueError, "duplicate extra '%s'" % name
			self.delegate( LeafElementHandler( name, self.onExtra ) )

	def doEndElement( self, name ):
		if name != "dir" and name != "file":
			raise ValueError, "unexpected end: '%s'" % name
		self.notify( self._path, self._fileChangeID, self._extras )

	def onPath( self, elementName, path, userArgs ):
		log.debug( "FileHandler.onPath: '%s'", path )
		self.delegate( None )
		self._path = path

	def onFileChangeID( self, elementName, fileChangeID, userArgs ):
		log.debug( "FileHandler.onFileChangeID: '%s'", fileChangeID )
		self.delegate( None )
		self._fileChangeID = fileChangeID

	def onExtra( self, elementName, contents, userArgs ):
		log.debug( "FileHandler.onExtra:'%s' -> '%s'", elementName, contents )
		self.delegate( None )
		self._extras[elementName] = contents


class FileListHandler( DelegatingContentHandler ):
	LIST_FILE = 0
	LIST_DIR = 1
	LIST_END = 2
	def __init__( self, name, callback, userArgs = None ):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._name = name
		self._nestLevel = 1

	def doStartElement( self, name, attrs ):
		if name == "file":
			self.delegate( FileHandler( self.onFile ) )

		if name == "dir":
			self.delegate( FileHandler( self.onDir ) )

	def doEndElement( self, name ):
		if name != self._name:
			raise ValueError, "unexpected: '%s' expecting '%s'" % \
				(name, self._name)
		self.notify( FileListHandler.LIST_END, None, None, None )

	def onFile( self, path, fileChangeID, extras, userArgs ):
		self.delegate( None )
		self.notify( FileListHandler.LIST_FILE, path, fileChangeID, extras )

	def onDir( self, path, fileChangeID, extras, userArgs ):
		self.delegate( None )
		self.notify( FileListHandler.LIST_DIR, path, fileChangeID, extras )

class ChecksumsHandler( DelegatingContentHandler ):
	def __init__( self, patchApply, callback, userArgs = None):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._patchApply = patchApply
		self.delegate( FileListHandler( "checksums", self.onFile ) )

	def onFile( self, type, path, fileChangeID, extras, userArgs ):
		log.debug( "onFile: type = %d, path = %s", type, path )
		if type == FileListHandler.LIST_FILE:
			if not 'checksum' in extras:
				raise ValueError, "No checksum element for '%s'" % path
			checksum = extras['checksum']
			self._patchApply.checkFile( FileChecksum( path, checksum ) )
		elif type == FileListHandler.LIST_DIR:
			raise ValueError, "Checksums list element contains dir"
		elif type == FileListHandler.LIST_END:
			self.delegate( None )
			self.notify()


class AdditionsHandler( DelegatingContentHandler ):
	def __init__( self, patchApply, callback, userArgs = None):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._patchApply = patchApply
		self.delegate( FileListHandler( "added", self.onFile ) )

	def onFile( self, type, path, fileChangeID, extras, userArgs ):
		if type == FileListHandler.LIST_FILE:
			self._patchApply.addFile( FileAddition( path, fileChangeID ) )
		elif type == FileListHandler.LIST_DIR:
			self._patchApply.addDirectory( path )
		elif type == FileListHandler.LIST_END:
			self.delegate( None )
			self.notify()

class DeletionsHandler( DelegatingContentHandler ):
	def __init__( self, patchApply, callback, userArgs = None):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._patchApply = patchApply
		self.delegate( FileListHandler( "deleted", self.onFile ) )

	def onFile( self, type, path, fileChangeID, extras, userArgs ):
		if type == FileListHandler.LIST_FILE:
			self._patchApply.deleteFile( path )
		elif type == FileListHandler.LIST_DIR:
			self._patchApply.deleteDirectory( path )
		elif type == FileListHandler.LIST_END:
			self.delegate( None )
			self.notify()

class ModificationsHandler( DelegatingContentHandler ):
	def __init__( self, patchApply, callback, userArgs = None ):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._patchApply = patchApply

		# Accumulate modified files so we can run a checksum check first before
		# we modify anything.
		self._modifiedFiles = []
		self.delegate( FileListHandler( "modified", self.onFile ) )

	def onFile( self, type, path, fileChangeID, extras, userArgs ):
		if type == FileListHandler.LIST_FILE:
			if not 'modType' in extras or \
					not 'beforeSum' in extras or \
					not 'afterSum' in extras:
				raise ValueError, "Missing extras for file modification"
			self._modifiedFiles.append( FileModification(
				path, fileChangeID, extras['beforeSum'],
				extras['afterSum'],
				FileModification.modTypeFromString( extras['modType'] ) ) )
		elif type == FileListHandler.LIST_DIR:
			raise ValueError, "modification includes a dir"
		elif type == FileListHandler.LIST_END:
			self.delegate( None )
			self.notify()
			for modifiedFile in self._modifiedFiles:
				self._patchApply.checkFile( 
					FileChecksum( modifiedFile.path, 
						modifiedFile.beforeSum ) )

			# OK, we're good to start modifying things.
			for modifiedFile in self._modifiedFiles:
				self._patchApply.patchFile( modifiedFile )

class SourceVersionHandler( DelegatingContentHandler ):
	SECTION_NAME		= 0x00
	SECTION_NUMOPS 		= 0x01
	SECTION_CHECKSUMS 	= 0x02
	SECTION_ADDED 		= 0x04
	SECTION_DELETED 	= 0x08
	SECTION_MODIFIED	= 0x10
	SECTIONS_ALL		= 0x1F

	def __init__( self, patchApply, desiredVersion, callback, userArgs = None ):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		log.debug( "SourceVersionHandler: desiredVersion = '%s'",
			desiredVersion )
		self._versionName = None
		self._patchApply = patchApply
		self._desiredVersion = desiredVersion
		self._doneSections = 0x00

	def doStartElement( self, name, attrs ):
		log.debug( "SourceVersionHandler.startElement: %s", name )
		if name == "name":
			self._doneSections |= self.SECTION_NAME
			self.delegate( LeafElementHandler( name, self.onVersionName ) )
		elif name == "numOperations":
			self._doneSections |= self.SECTION_NUMOPS
			self.delegate( LeafElementHandler( name, self.onNumOperations ) )
		elif name == "checksums":
			self._doneSections |= self.SECTION_CHECKSUMS
			if CHECK_CHECKSUMS:
				self.delegate( ChecksumsHandler( self._patchApply,
					self.onOperationFinish ) )
			else:
				self.delegate( SkipToElementEndHandler( "checksums",
					self.onOperationFinish ) )
		elif name == "added":
			self._doneSections |= self.SECTION_ADDED
			self.delegate( AdditionsHandler( self._patchApply,
				self.onOperationFinish ) )
		elif name == "deleted":
			self._doneSections |= self.SECTION_DELETED
			self.delegate( DeletionsHandler( self._patchApply,
				self.onOperationFinish ) )
		elif name == "modified":
			self._doneSections |= self.SECTION_MODIFIED
			self.delegate( ModificationsHandler( self._patchApply,
				self.onOperationFinish ) )

	def doEndElement( self, name ):
		if name != "version":
			raise ValueError, "unknown end tag '%s'" % name
		if self._doneSections != self.SECTIONS_ALL:
			raise ValueError, "some elements were missing"
		self.notify( self._versionName )

	def onVersionName( self, elementName, version, userArgs ):
		log.debug( "onVersionName: '%s'", version )
		self.delegate( None )
		self._versionName = version
		if version != self._desiredVersion:
			self.delegate( SkipToElementEndHandler(
				"version", self.onVersion ) )

	def onNumOperations( self, elementName, numOperations, userArgs ):
		self.delegate( None )
		self._patchApply.notifyNumOperations( int( numOperations ) )

	def onVersion( self, userArgs ):
		self.delegate( None )
		self.notify( self._versionName )

	def onOperationFinish( self, userArgs ):
		self.delegate( None )


class SourceVersionsHandler( DelegatingContentHandler ):
	def __init__( self, patchApply, version, callback, userArgs = None):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._patchApply = patchApply
		self._version = version
		self._sourceVersions = []

	def doStartElement( self, name, attrs ):
		if name != "version":
			raise ValueError, "unknown tag in sourceVersions: %s" % name
		log.debug( "SourceVersionsHandler.startElement: %s", name )
		self.delegate( SourceVersionHandler( self._patchApply, self._version,
			self.onSourceVersion ) )

	def doEndElement( self, name ):
		if name == "sourceVersions":
			self.notify( self._sourceVersions )

	def onSourceVersion( self, version, userArgs ):
		self._sourceVersions.append( version )
		self.delegate( None )

class ManifestRootHandler( DelegatingContentHandler ):
	def __init__( self, version, patchApply, callback, userArgs = None):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._version = version
		self._patchApply = patchApply

	def doStartElement( self, name, attrs ):
		if name == "sourceVersions":
			self.delegate(
				SourceVersionsHandler( self._patchApply, self._version,
					self.onSourceVersions ) )

	def onSourceVersions( self, sourceVersions, userArgs ):
		self.delegate( None )
		if self._version not in sourceVersions:
			raise ValueError, "version '%s' is not supported in this patch " \
				"(supported versions: '%s'" % (self._version,
					"', '".join( sourceVersions ) )

class ManifestHandler( DelegatingContentHandler ):
	def __init__( self, version, patchApply, callback, userArgs = None ):
		DelegatingContentHandler.__init__( self, callback, userArgs )
		self._version = version
		self._patchApply = patchApply

	def doStartElement( self, name, attrs ):
		if name != "root":
			raise ValueError, "Expecting root node, got '%s'" % name
		self.delegate( ManifestRootHandler( self._version, self._patchApply,
			self.onRootDone ) )

	def onRootDone( self ):
		self.delegate( None )
		self.notify()


class PatchApply( object ):
	"""
	PatchApply class, that implements functionality to patch a tree with a
	given patch file.
	"""
	def __init__( self, sourceVersion, sourcePath, patchFilePath,
			callback=PatchApplyCallbackInterface() ):
		"""
		Constructor.

		@param sourceVersion		The expected source version of the source
									tree path.
		@param sourcePath			The source tree path, which can be a path 
									to a directory, or a ZIP archive. 
		@param patchFilePath		The path to the patch file archive.
		@param callback				The patch progress callback.
		"""
		self._sourceVersion = sourceVersion
		self._sourcePath = sourcePath
		self._patchFilePath = patchFilePath
		self._callback = callback
		self._patchPath = None
		self._patchArchive = None
		self._patchDirList = None

	def _extractPatchArchive( self ):
		self._patchArchive = tarfile.open( self._patchFilePath, 'r' )

		if not "manifest" in self._patchArchive.getnames():
			raise ValueError, "patch file has no manifest"

		self._patchPath = tempfile.mkdtemp( prefix="bw-patch-" )
		self._patchDirList = TempDirList( self._patchPath )

		foundSourceVersion = False
		for name in self._patchArchive.getnames():
			# only extract out the files we're interested in
			if name.startswith(
					"changes/" + self._sourceVersion + "/" ):
				foundSourceVersion = True
				self._patchArchive.extract( name, self._patchPath )
				self._patchDirList.addPath( name )
		if not foundSourceVersion:
			log.warning( "source version not in changes dir: '%s'",
				self._sourceVersion )

		self._patchArchive.extract( "manifest", self._patchPath )
		self._patchDirList.addPath( "manifest" )


	def run( self ):
		"""
		Apply the patch.
		"""
		log.info( "srcVer = %s, srcPath = %s, patchFilePath = %s",
			self._sourceVersion, self._sourcePath, self._patchFilePath )

		isZipFile = zipfile.is_zipfile( self._sourcePath )
		if not isZipFile and not os.path.isdir( self._sourcePath ):
			raise ValueError, "Patch source path is neither directory " \
				"nor ZIP archive: %s" % self._sourcePath

		if isZipFile:
			zipFilePath = self._sourcePath
			log.debug( "unzipping %s", zipFilePath )
			self._sourcePath = tempfile.mkdtemp( prefix="bw-patch-" )
			utils.zipExtractAll( zipFilePath, self._sourcePath )

		self._extractPatchArchive()

		handler = ManifestHandler( self._sourceVersion, self, self.onParse )
		xml.sax.parse( os.path.join( self._patchPath, "manifest" ), handler )

		if isZipFile:
			log.debug( "re-zipping up patched dir to %s", zipFilePath )
			tempFD, tempPath = tempfile.mkstemp( prefix="bw-patch-" )
			os.close( tempFD )

			utils.zipCreateFromDir( self._sourcePath, tempPath, removeDir=True )

			os.remove( zipFilePath )
			shutil.move( tempPath, zipFilePath )

		self._patchDirList.remove()
		self._patchDirList = None


	def addDirectory( self, path ):
		log.info( "creating dir %s", path )
		self._callback.onDirAddStart( path )
		if not os.path.exists( os.path.join( self._sourcePath, path ) ):
			os.makedirs( os.path.join( self._sourcePath, path ) )
		self._callback.onDirAddFinish( path )

	def deleteDirectory( self, path ):
		log.info( "deleting dir %s", path )
		self._callback.onDirDelStart( path )
		for dirPath, dirNames, fileNames in os.walk(
				os.path.join( self._sourcePath, path ),
				topdown=False ):
			for fileName in fileNames:
				log.info( "deleting file %s",
					os.path.join( dirPath, fileName ) )
				os.remove( os.path.join( dirPath, fileName ) )
			for dirName in dirNames:
				log.info( "deleting dir %s", os.path.join( dirPath, dirName ) )
				os.rmdir( os.path.join( dirPath, dirName ) )
		os.rmdir( os.path.join( self._sourcePath, path ) )
		self._callback.onDirDelFinish( path )

	def addFile( self, fileAdd ):
		log.info( "creating file %s", fileAdd.path )
		self._callback.onFileAddStart( fileAdd.path )

		utils.bzipDecompressFile( self._convertPath( fileAdd.fileChangeID ),
			os.path.join( self._sourcePath, fileAdd.path ) )

		self._callback.onFileAddFinish( fileAdd.path )

	def deleteFile( self, path ):
		log.info( "deleting file %s", path )
		self._callback.onFileDelStart( path )
		os.unlink( os.path.join( self._sourcePath, path ) )
		self._callback.onFileDelStart( path )

	def _convertPath( self, fileChangeID ):
		return os.path.join( self._patchPath,
			"changes", self._sourceVersion, fileChangeID )

	def patchFile( self, fileMod ):
		self._callback.onFileModStart( fileMod.path )

		sourceFilePath = os.path.join( self._sourcePath, fileMod.path )
		log.info( "patching file %s (%s, %s, %s)",
			sourceFilePath,
			fileMod.beforeSum,
			fileMod.afterSum,
			fileMod.modTypeToString() )

		if fileMod.modType == manifest.MOD_TYPE_BINARY_BSDIFF:
			patchPath = self._convertPath( fileMod.fileChangeID )
			# patch it in-place
			bsdiff.patchFilesFromFile( sourceFilePath, sourceFilePath, 
				patchPath )
		else:
			raise NotImplementedError, "mod type %d is not supported" % \
				fileMod.modType

		if not utils.verifyMD5( sourceFilePath, fileMod.afterSum ):
			raise ValueError, "digest mismatch after patching for %s" % \
				(fileMod.path)

		self._callback.onFileModFinish( fileMod.path )

	def checkFile( self, fileChecksum ):
		log.info( "checking checksum for %s", fileChecksum.path )
		sourceFilePath = os.path.join( self._sourcePath, fileChecksum.path )
		if not utils.verifyMD5( sourceFilePath, fileChecksum.checksum ):
			raise ValueError, "digest mismatch for %s" % fileChecksum.path

	def notifyNumOperations( self, numOperations ):
		log.debug( "Got num ops: %d", numOperations )
		self._callback.onStart( numOperations )

	def onParse( self ):
		self._callback.onFinish()

# patch_apply.py

