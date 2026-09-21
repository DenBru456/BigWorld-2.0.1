import encodings

import xmpp.Connection as XMPPConnection
import xmpp.Service as XMPPService


# -------------------------------------------------------------------------
# Section: class Client
# -------------------------------------------------------------------------

class Client( object ):

	# Concrete XMMPClients should override these methods
	def onXmppMessage( self, sender, message ): pass
	def onXmppPresence( self, sender, isOnline ): pass
	def onXmppListFriends( self, online, offline ): pass
	def onXmppError( self, message ): pass
	def onXmppStateChange( self, oldState, newState ): pass


	def __init__( self ):
		self.xmppConnection = None


	def xmppConnect( self, user, passwd, connectionHandler ):
		print "Attempting to connect to XMPP server: %s, %s" % (user, passwd)

		if not XMPPService.isEnabled():
			print "xmpp.Client::xmppConnect: Unable to connect to XMPP " \
					"server, service is not enabled."
			return

		if self.xmppConnection:
			print "xmpp.Client::xmppConnect: An existing connection exists"
			return

		self.xmppConnection = XMPPConnection.Connection( connectionHandler )
		self.xmppConnection.connect( user, passwd )


	def xmppDisconnect( self ):
		if self.xmppConnection:
			self.xmppConnection.disconnect()
			self.xmppConnection = None


	def xmppAddFriend( self, friendID, transport ):

		if not self.xmppConnection:
			self.onXmppConnectionError( "Not connected to XMPP server" )
			return

		self.xmppConnection.friendAdd( friendID, transport )


	def xmppDelFriend( self, friendID, transport ):

		if not self.xmppConnection:
			self.onXmppConnectionError( "Not connected to XMPP server" )
			return

		if transport == "xmpp":
			# NB: Current logic is to remove this friend from all resource
			#     locations they may exist at
			friendID = friendID.split( "/" )[0]


		self.xmppConnection.friendDelete( friendID, transport )


	def xmppMsgFriend( self, friendID, transport, message ):

		if not self.xmppConnection:
			self.onXmppConnectionError( "Not connected to XMPP server" )
			return

		self.xmppConnection.friendMessage( friendID, transport, message )
