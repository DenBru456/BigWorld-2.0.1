import BigWorld
import util
import traceback

import XMPPEventNotifier

# Add Guards
# -----------------------------------------------------------------------------
def addGuardReturnMessage( numGuards ):
	try:
		type = util.addGuards( numGuards )
		return "Added %s guards of type '%s'." % ( numGuards, type )
	except:
		traceback.print_exc()
		return "Failed to add guards."



# Remove Guards
# -----------------------------------------------------------------------------
def delGuardReturnMessage( numGuards ):
	try:
		count = util.removeGuards( numGuards )
		return "Removed %s guards." % count
	except:
		traceback.print_exc()
		return "Failed to remove guards."



# System Message
# -----------------------------------------------------------------------------
def sendSystemMessage( msg ):
	resultMsg = ""
	try:
		resultMsg = "Message sent to %s clients." % util.systemMessage( msg )

	except:
		resultMsg = "Failed to send system message."

	return resultMsg


def xmppBroadcast( msg ):
	if BigWorld.globalBases.has_key( "XMPPEventNotifier" ):
		notifier = BigWorld.globalBases[ "XMPPEventNotifier" ]
		if BigWorld.entities.has_key( notifier.id ):
			notifier.broadcast( msg )


# Add all the Watchers.
def addWatchers():

	BigWorld.addFunctionWatcher( "command/addGuards", addGuardReturnMessage,
		[("Number of guards to add", int)], BigWorld.EXPOSE_LEAST_LOADED,
		"Add an arbitrary number of patrolling guards into the world.") 

	BigWorld.addFunctionWatcher( "command/removeGuards", delGuardReturnMessage,
		[("Number of guards to remove", int)], BigWorld.EXPOSE_LEAST_LOADED,
		"Remove an arbitrary number of patrolling guards into the world.")

	BigWorld.addFunctionWatcher( "command/systemMessage", sendSystemMessage,
		[("Message to send", str)], BigWorld.EXPOSE_ALL,
		"Send a global system message to all clients.")

	BigWorld.addFunctionWatcher( "command/xmppBroadcast", xmppBroadcast,
		[("Message to broadcast", str)], BigWorld.EXPOSE_ALL,
		"Broadcast an XMPP message" )

# Watchers.py
