"""
Module pertaining to the state file.
"""
import bwsetup
bwsetup.addPath( "..", 0 )

from xml.dom import minidom, Node

class StateInterface( object ):
	"""
	Interface for maintaining target state.
	"""
	def getCurrentVersion( self ):
		raise NotImplementedError
	def getTargetVersion( self, targetName ):
		raise NotImplementedError
	def setCurrentVersion( self, version ):
		raise NotImplementedError
	def setTargetVersion( self, targetName, targetVersion ):
		raise NotImplementedError

class StateXML( StateInterface ):
	"""
	This class encapsulates the parsed contents of the state file.
	"""
	REQ_CURRENT_VERSION 	= 0x1
	REQ_TARGETS 			= 0x2
	REQS_ALL 				= 0x3

	def __init__( self, path ):
		self._path = path
		self._doc = minidom.parse( path )

		self._targetStateNodes = {}
		self._currentVersionNode = None
		self._reqsLeft = StateXML.REQS_ALL

		self._parseDoc()

	def _parseDoc( self ):
		for node in self._doc.documentElement.childNodes:
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			if node.nodeName == "currentVersion":
				if len( node.childNodes ) != 1 or \
						node.firstChild.nodeType != Node.TEXT_NODE:
					raise ValueError, "invalid currentVersion node"
				if not self._currentVersionNode is None:
					raise ValueError, "duplicate currentVersion specified"
				self._currentVersionNode = node.firstChild
				self._reqsLeft &= ~StateXML.REQ_CURRENT_VERSION
			elif node.nodeName == "targets":
				if node.nodeType != Node.ELEMENT_NODE:
					raise ValueError, "invalid targets node"
				self._reqsLeft &= ~StateXML.REQ_TARGETS
				self._parseTargets( node )

		if self._reqsLeft:
			raise ValueError, "incomplete state file"

	def _parseTargets( self, targetsNode ):
		for node in targetsNode.childNodes:
			if node.nodeType != Node.ELEMENT_NODE:
				continue
			tests = [node.nodeName == "target",
					len( node.childNodes ) == 1,
					node.hasAttribute( "name" ),
					node.firstChild.nodeType == Node.TEXT_NODE]
			if not reduce( lambda x, y: x and y, tests ):
				log.error( "target: %r", tests )
				raise ValueError, "invalid target node"

			targetName = node.getAttribute( "name" )
			if targetName in self._targetStateNodes:
				raise ValueError, "duplicate target '%s'" % targetName

			self._targetStateNodes[targetName] = node.firstChild

	def getCurrentVersion( self ):
		return self._currentVersionNode.nodeValue.strip()

	def getTargetVersion( self, targetName ):
		# unknown targets return None for the target version
		node = self._targetStateNodes.get( targetName, None )
		if node is None:
			return None
		else:
			return node.nodeValue.strip()

	def save( self ):
		f = open( self._path, "w" )
		f.write( self._doc.toxml() )
		f.close()

	def setCurrentVersion( self, currentVersion ):
		self._currentVersionNode.nodeValue = currentVersion
		self.save()

	def setTargetVersion( self, targetName, targetVersion ):
		self._targetStateNodes[targetName].nodeValue = targetVersion
		self.save()

# state.py

