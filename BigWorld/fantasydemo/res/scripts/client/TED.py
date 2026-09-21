# Import the BigWorld modules
import BigWorld

# Import FantasyDemo modules
import FantasyDemo
from Helpers import Caps

# Import common modes that TED may be in
import TEDModes


# TED demonstrates the use of a variety of Entity Extras, including navigation,
# vision and proximity triggers.

# To create TED, telnet to a BigWorld Base:
#	telnet <host> 40001
# and type:
#	BigWorld.createBase( "TED" )
class TED( BigWorld.Entity ):

	stdModel = "characters/npc/guard/orc_moria_onesheet.model"

	# Initialise any required attributes
	def __init__( self ):
		BigWorld.Entity.__init__( self )
		
	
	def prerequisites( self ):
		return [TED.stdModel]


	# BigWorld client callback function used to initialise Entity when it enters
	# the world
	def onEnterWorld( self, prereqs ):
		self.model = prereqs[TED.stdModel]
		self.model.motors[0].entityCollision = 1
		self.model.motors[0].collisionRooted = 0
		self.filter = BigWorld.AvatarDropFilter()
		self.targetCaps = [Caps.CAP_CAN_USE]


	# BigWorld client callback function used to clean up Entity when it leaves
	# the world
	def onLeaveWorld( self ):
		pass


	# FantasyDemo method common to all client Entities to return identifying
	# name of Entity to be displayed
	def name( self ):
		return "TED"


	# FantasyDemo method common to all client Entities that can be used by the
	# player.
	def use( self ):
		self.cell.use()


	# BigWorld callback method used when 'mode' property has been changed on
	# server.  See .def for more details
	def set_mode( self, oldMode ):

		# If TED has become a ChatRoom interface
		if self.mode == TEDModes.TED_INUSE:

			# No need to do anything in this case, but the displayed chat
			# message illustrates the propagation point
			self.chat( u"Ouch!" )


	# Defined in .def file so server can directly chat with this client
	def chat( self, msg ):

		# Display the chat message on this client
		FantasyDemo.addChatMsg( self.id, msg )


# TED.py
