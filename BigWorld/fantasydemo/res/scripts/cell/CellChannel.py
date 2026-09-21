import BigWorld

# ------------------------------------------------------------------------------
# Section: class CellChannel
# ------------------------------------------------------------------------------

class CellChannel( BigWorld.Entity ):
	def __init__( self ):
		BigWorld.Entity.__init__( self )

		self.members = []
		print "New channel", self.label

	def __del__( self ):
		print "Channel", self.label, "is dying."

	def register( self, id ):
		self.members.append( id )

		print "Adding", id, "to channel"

	def deregister( self, id ):
		self.members.remove( id )

	def tellOthers( self, source, message ):
		print 'Telling other "%s".' % (message, )

		for id in self.members:
			if id != source:
				# TODO: May want to add a type to chat so that the client can
				# tell the different types. E.g. Shouts, directed chat,
				# whispers, table chat etc.
				BigWorld.entities[ id ].directedChat( source, message )

	def broadcast( self, message ):
		# TODO:
		for id in self.members:
			BigWorld.entities[ id ].directedChat( 0, message )

# CellChannel.py
