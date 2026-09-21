"""
Module containing a simple configuration class.
"""
import bwsetup
bwsetup.addPath( "..", 0 )

from xml.dom import minidom, Node

class Config( object ):
	"""
	A simple config class which stores config keys in an XML document. Keys are
	hierarchical and paths to leaf elements are separated by a period ('.'),
	and a referenced from the root element of the XML document.

	For example, "versionsURL" matches
		<root>...<versionsURL>http://...</versionsURL>...</root>.
	and "a.b.c.d" matches
		<root>...<a>...<b>...<c>...<d>value</d>...</c>...</b>...</a>...</root>

	"""
	def __init__( self, configPath ):
		self._path = configPath
		self._doc = minidom.parse( configPath )
		self._dict = {}
		for child in self._doc.documentElement.childNodes:
			if child.nodeType == Node.ELEMENT_NODE:
				self._traverseConfigTree( child )

	def _traverseConfigTree( self, element, parent = '' ):

		if len( element.childNodes ) == 1 and \
				element.firstChild.nodeType == Node.TEXT_NODE:
			if parent != "":
				key = parent + "." + element.nodeName
			else:
				key = element.nodeName
			self._dict[key] = element.firstChild.nodeValue.strip()

		else:
			for child in element.childNodes:
				if child.nodeType != Node.ELEMENT_NODE:
					continue
				if not parent:
					elementPath = element.nodeName
				else:
					elementPath = parent + "." + element.nodeName
				self._traverseConfigTree( child, elementPath )

	def get( self, name, default='' ):
		if name in self._dict:
			return self._dict[name]
		return default

# simple_config.py
