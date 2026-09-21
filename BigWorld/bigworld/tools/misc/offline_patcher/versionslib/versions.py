"""
Module pertaining to the versions file.
"""

import bwsetup
bwsetup.addPath( "..", 0 )

from xml.dom import minidom, Node

class UpgradePath( object ):
	"""
	This class contains the patch targets for a named version.
	"""
	def __init__( self, versions ):
		"""
		Constructor.

		@param versions 		The Versions object this upgrade path belongs
								to.
		@param name				The name of the upgrade path's source version.
		@param targets			A list of Target objects.
		"""
		self._versions = versions
		self.name = None
		self.targets = [] # list of Target objects
		self._properties = {}

	def setUpgradePathProperties( self, properties ):
		"""
		Set an upgrade-path level properties.

		@param properties 	The properties dictionary.
		"""
		self._properties = properties

	def getProperties( self ):
		"""
		Get the aggregated properties for the upgrade path.

		@return 	A dict object containing the property names and values of
					the upgrade-path level and the global level properties.
		"""
		out = dict( self._versions.getGlobalProperties() )
		out.update( self._properties )
		return out

class Target( object ):
	"""
	This class consists of a target in the form of a path to a directory
	hierarchy (either in ZIP archive or directories) and a description of a
	patch against that target that specifies how to retrieve that patch.
	"""
	def __init__( self, upgradePath, name, path, sourceVersion, destVersion,
			transferType, patchName, **patchProperties ):
		"""
		Constructor.

		@param upgradePath		The UpgradePath object this target is
								associated with.
		@param name				The name of the target.
		@param path				The path to the target from the current
								working directory of the patcher.
		@param sourceVersion	The source version of the target.
		@param destVersion		The destination version of the target.
		@param transferType		The transfer type. This must be a type that
								is registered with
								versionslib.transfer.PatchTransferHandler.
		@param patchName		The file name of the patch file.
		@param patchProperties	A mapping of patch transfer properties. These
								are generally passed as a keyworld argument
								dictionary to the appropriate transfer
								handler.

		"""
		self._upgradePath = upgradePath
		self.name = name
		self.path = path
		self.sourceVersion = sourceVersion
		self.destVersion = destVersion
		self.transferType = transferType
		self.patchName = patchName

		self._patchProperties = patchProperties

	def getProperties( self ):
		out = dict( self._upgradePath.getProperties() )
		out.update( self._patchProperties )
		return out


class VersionsInterface( object ):
	"""
	Interface for Versions objects used by the checkVersion() module method.
	"""
	def getVersionUpgradePath( self, versionName ):
		"""
		Return the version upgrade path for a named version in the form of a
		UpgradePath object.

		@param versionName	The source version name.
		@return 			An upgrade path for the specified named version, or
							None if no upgrade path exists.
		"""
		raise NotImplementedError

	def getCurrentVersion( self ):
		"""
		Return the remote current version.

		@return The remote current version.
		"""
		raise NotImplementedError

	def getGlobalProperties( self ):
		"""
		Return the global level key-value properties.

		@return 	The global level key-value properties as a dict object.
		"""
		raise NotImplementedError


class VersionsXML( VersionsInterface ):
	"""
	This class is the parsed object of the versions XML document.
	"""
	REQ_CURRENT_VERSION 		= 0x01
	REQ_SUPPORTED_VERSIONS 		= 0x02
	REQS_ALL					= 0x03

	def __init__( self, versionsDoc ):
		"""
		Constructor.

		@param versionsDoc	the versions XML DOM document
		"""

		self._doc = versionsDoc
		self._requiredLeft = VersionsXML.REQS_ALL
		self._currentVersion = None
		self._versions = {}
		self._globalProperties = {}

		self._parseDoc()

	def getUpgradePath( self, versionName ):
		"""
		Get an upgrade path for a given named version. If the version is not a
		supported version, None is returned.

		@param versionName 	the name of the version
		@return the upgrade path in the form of a UpgradePath object
		"""
		return self._versions.get( versionName, None )

	def getCurrentVersion( self ):
		"""
		Get the current version represented in the version file.
		"""
		return self._currentVersion


	def getGlobalProperties( self ):
		return self._globalProperties

	def _parseDoc( self ):
		"""
		Parse the given document.
		"""
		for node in self._doc.documentElement.childNodes:
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			if node.nodeName == "currentVersion":
				self._parseCurrentVersion( node )
			elif node.nodeName == "supportedVersions":
				self._parseSupportedVersions( node )
			elif node.nodeName == "property":
				self._parseProperty( node, self._globalProperties )

		if self._requiredLeft:
			if VersionsXML.REQ_CURRENT_VERSION & self._requiredLeft:
				raise ValueError, "versions document missing current version"
			elif VersionsXML.REQ_SUPPORTED_VERSIONS & self._requiredLeft:
				raise ValueError, "versions document missing "\
					"supported versions list"

	def _parseCurrentVersion( self, node ):
		"""
		Parse the current version element.
		"""
		if len( node.childNodes ) == 1 and \
				node.firstChild.nodeType == Node.TEXT_NODE:
			self._requiredLeft &= ~VersionsXML.REQ_CURRENT_VERSION
			self._currentVersion = node.firstChild.nodeValue.strip()

	def _parseSupportedVersions( self, supportedVersionsNode ):
		"""
		Parse a list of supported version's upgrade paths.
		"""
		for child in supportedVersionsNode.childNodes:
			if child.nodeType != Node.ELEMENT_NODE:
				continue

			if child.nodeName == "version":
				upgradePath = self._parseSupportedVersion( child )
				self._versions[upgradePath.name] = upgradePath
				self._requiredLeft &= ~VersionsXML.REQ_SUPPORTED_VERSIONS
			elif child.nodeName == "property":
				self._parseProperty( child, self._globalProperties )

	def _parseSupportedVersion( self, versionNode ):
		"""
		Parse an a supported version element that contains an upgrade path.
		"""

		# optional
		updateInfoURL = None
		versionProperties = {}

		upgradePath = UpgradePath( self )

		for child in versionNode.childNodes:
			if child.nodeType != Node.ELEMENT_NODE:
				continue
			if child.nodeName == "name":
				if len( child.childNodes ) != 1 or \
						child.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid name element"
				upgradePath.name = child.firstChild.nodeValue.strip()
			elif child.nodeName == "property":
				self._parseProperty( child, versionProperties )
			elif child.nodeName == "targets":
				upgradePath.targets = self._parseTargets( child, upgradePath )

		if upgradePath.name is None or \
				not upgradePath.targets:
			raise ValueError, "incomplete version element, need " \
					"name element and at least one target in targets element"

		upgradePath.setUpgradePathProperties( versionProperties )

		return upgradePath

	def _parseProperty( self, targetNode, properties ):
		if targetNode.nodeName != "property" or \
				len( targetNode.childNodes ) != 1 or \
				targetNode.firstChild.nodeType != Node.TEXT_NODE or \
				not targetNode.hasAttribute( "name" ):
			raise ValueError, "invalid property element"
		propertyName = str( targetNode.getAttribute( "name" ) )
		propertyValue = targetNode.firstChild.nodeValue.strip()
		properties[propertyName] = propertyValue


	def _parseTargets( self, targetsNode, upgradePath ):
		targets = []
		for child in targetsNode.childNodes:
			if child.nodeType != Node.ELEMENT_NODE:
				continue

			target = self._parseTarget( child, upgradePath )
			targets.append( target )
		return targets


	def _parseTarget( self, targetNode, upgradePath ):
		"""
		Parses a patch target element.
		"""
		targetPath = None
		targetName = None
		sourceVersion = None
		destVersion = None
		transferType = None
		patchProperties = {}
		for child in targetNode.childNodes:
			if child.nodeType != Node.ELEMENT_NODE:
				continue

			if child.nodeName == "path":
				if len( child.childNodes ) != 1 or \
						child.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid target node"
				if not targetPath is None:
					raise ValueError, "duplicate target specified"
				targetPath = child.firstChild.nodeValue.strip()

			elif child.nodeName == "name":
				if len( child.childNodes ) != 1 or \
						child.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid target node"
				if not targetName is None:
					raise ValueError, "duplicate target specified"
				targetName = child.firstChild.nodeValue.strip()

			elif child.nodeName == "sourceVersion":
				if len( child.childNodes ) != 1 or \
						child.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid target source version"
				if not sourceVersion is None:
					raise ValueError, "duplicate target source version "\
						"specified"
				sourceVersion = child.firstChild.nodeValue.strip()
			elif child.nodeName == "destVersion":
				if len( child.childNodes ) != 1 or \
						child.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid target destination version"
				if not destVersion is None:
					raise ValueError, "duplicate target destination version "\
						"specified"
				destVersion = child.firstChild.nodeValue.strip()

			elif child.nodeName == "patch":
				if not transferType is None:
					raise ValueError, "duplicate patch transfer type specified"
				transferType, patchName, patchProperties = \
					self._parsePatch( child )

		if targetName is None or \
				targetPath is None or sourceVersion is None or \
				destVersion is None or transferType is None:
			raise ValueError, "target info is incomplete"

		return Target( upgradePath, targetName, targetPath,
			sourceVersion, destVersion,
			transferType, patchName, **patchProperties )


	def _parsePatch( self, patchNode ):
		transferType = None
		patchName = None
		patchProperties = {}
		for child in patchNode.childNodes:
			if child.nodeType != Node.ELEMENT_NODE:
				continue
			if len( child.childNodes ) != 1 or \
					child.firstChild.nodeType != Node.TEXT_NODE:
				raise ValueError, "invalid patch child element"
			value = child.firstChild.nodeValue.strip()
			if child.nodeName == "transferType":
				transferType = value
			elif child.nodeName == "name":
				patchName = value
			elif child.nodeName == "property":
				self._parseProperty( child, patchProperties )

		if not transferType:
			raise ValueError, "no transfer type specified"
		if not patchName:
			raise ValueError, "no patch archive name specified"

		return transferType, patchName, patchProperties


# versions.py

