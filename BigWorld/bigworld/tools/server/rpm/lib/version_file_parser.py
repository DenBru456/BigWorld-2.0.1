import xml.sax

class VersionFileParser( object, xml.sax.ContentHandler ):
	"""
	Class to parse the versions file in bigworld/res/server/versions.xml.
	"""
	def __init__( self, versionFilePath ):
		"""
		Constructor.

		@param versionFilePath 	The path to the versions file.
		"""
		self._target = None
		self._buffer = ''
		
		self.major = None
		self.minor = None
		self.reserved = None
		self.patch = None

		self.locator = None

		# We need to preprocess versions.xml to remove the comments around the
		# major, minor and reserved elements.
		fileContents = self._preprocess( versionFilePath )

		xml.sax.parseString( fileContents, self )

	def _preprocess( self, versionFilePath ):
		out = []
		for line in open( versionFilePath ):
			# remove the XML comments markers, so we can parse major, minor and
			# reserved
			line = line.replace( '<!--', '', )
			line = line.replace( '-->', '' )
			out.append( line )
		return "".join( out )

	def setDocumentLocator( self, locator ):
		self.locator = locator

	def startElement( self, name, attrs ):
		if name == "root":
			return

		if not self._target is None:
			if self.locator:
				location = " (line %d, column %d)" % \
					(self.locator.getLineNumber(), 
						self.locator.getColumnNumber())
			else:
				location = ""
			raise ValueError, \
				"started new element while processing %s%s" % \
					(self._target, location)
		self._target = name

	def endElement( self, name ):
		if not self._target in ("major", "minor", "reserved", "patch"):
			return
		
		contents = self._buffer.strip()

		if self._target == "major":
			self.major = contents.encode( 'utf-8' )
		elif self._target == "minor":
			self.minor = contents.encode( 'utf-8' )
		elif self._target == "patch":
			self.patch = contents.encode( 'utf-8' )
		elif self._target == "reserved":
			self.reserved = contents.encode( 'utf-8' )

		self._target = None
		self._buffer = ''

	def characters( self, content ):
		if not self._target is None:
			self._buffer += content
		
	def endDocument( self ):
		if self.major is None:
			raise ValueError, "Missing element for major version"
		elif self.minor is None:
			raise ValueError, "Missing element for minor version"
		elif self.patch is None:
			raise ValueError, "Missing element for patch version"

# version_file_parser.py
