from exposed import Exposed

import messages
import os
from cluster_constants import TIMEOUT

from watcher_data_type import WDTRegistry
from watcher_data_message import WatcherDataMessage

#------------------------------------------------------------------------------
# Section: WatcherData
#------------------------------------------------------------------------------

class WatcherData( Exposed ):

	def __init__( self, process, path, value=None, watcherType=None, watcherMode=None ):
		Exposed.__init__( self )

		if not process.hasWatchers():
			raise TypeError( "Watchers are not supported on this process type "
				"(%s)" % process.name )

		self.process = process
		self.path = path
		self.name = os.path.basename( path )
		self.value = value
		self.type = watcherType
		self.mode = watcherMode

		# Special case for the root directory
		if path == "":
			self.value = "<DIR>"

		if self.value == None:
			self.refresh()


	def refresh( self ):
		"""Updates the value by asking the machine."""

		if self.value == "<DIR>":
			return

		newvalue = None
		queryType = None
		queryMode = None
		for path, value, queryType, queryMode in messages.WatcherDataMessage.query(
			os.path.dirname( self.path ), self.process, TIMEOUT ):

			if path == os.path.basename(self.path):
				newvalue = value
				newtype = queryType
				newmode = queryMode
				break

		if newvalue == None:
			self.process.mute = True
			self.value = None
		else:
			self.value = newvalue
			self.type = newtype
			self.mode = newmode

	def isDir( self ):
		return self.value == "<DIR>"

	def isCallable( self ):
		return self.mode == WatcherDataMessage.WATCHER_MODE_CALLABLE

	def isReadOnly( self ):
		return self.mode == WatcherDataMessage.WATCHER_MODE_READ_ONLY

	def __str__( self ):
		return "%s = %s" % (self.name, self.value)


	def valueAsStr( self ):
		return WDTRegistry.getClass( self.type ).asStr( self.value )

	def __cmp__( self, other ):
		"""Directories first, then sort by name"""

		if (other == None):
			return -1

		if (self.isDir() and other.isDir()) or \
		   (not self.isDir() and not other.isDir()):
			return cmp( self.name, other.name )
		elif self.isDir():
			return -1
		else:
			return 1


	def __iter__( self ):
		return iter( self.getChildren() )


	def getChildren( self ):
		"""Retrieve next level of Watcher tree."""

		if self.value != "<DIR>": return

		self.children = []
		for path, value, queryType, queryMode in messages.WatcherDataMessage.query(
			self.path, self.process, TIMEOUT ):

			# Reform the basename that has been returned into a complete
			# watcher path
			if self.path and len(self.path):
				path = "%s/%s" % (self.path, path)

			self.children.append( WatcherData( self.process, path, value,
				queryType, queryMode ) )

		self.children.sort()
		return self.children


	def getChild( self, name ):
		return WatcherData( self.process, os.path.join( self.path, name ) )


	@Exposed.expose( precond = lambda self: not self.isDir() )
	def set( self, value ):
		"""Set this watcher value."""
		return self.process.setWatcherValue( self.path, value )

# watcher_data.py
