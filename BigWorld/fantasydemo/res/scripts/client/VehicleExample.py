import BigWorld
import Keys
from Helpers import Caps


# This implements the VehicleExample on the Client.  It's purpose is to 
# provide the steps required to control and move a vehicle on the Client.

# To create the VehicleExample, telnet to a BigWorld Base:
#	telnet <host> 40001
# and type:
#	BigWorld.createBase( "VehicleExample" )
class VehicleExample( BigWorld.Entity ):

	stdModel = "characters/npc/striff/striff.model"

	def __init__( self ):
		BigWorld.Entity.__init__( self )
		
		
	def prerequisites( self ):
		return [VehicleExample.stdModel]
	
	
	# This is called by BigWorld when the Entity enters AOI, through creation or movement.
	def onEnterWorld( self, prereqs ):
	
		# We will use the striff model for this example
		self.model = prereqs[VehicleExample.stdModel]
		
		# Set appropriate filter for server controlled Entity
		self.filter = BigWorld.DumbFilter()
		
		# Set the appropriate targeting capabilities, so we can target and use the vehicle
		self.targetCaps = [Caps.CAP_CAN_USE]
		
		
	# This is called by BigWorld when the Entity leaves AOI, through creation or movement.
	def onLeaveWorld( self ):
		self.model = None
	
	
	# This is called whenever the pilot property is changed.
	# This is what we will use to perform our handshaking.
	# Note that if we were to implement boarding animations, 
	# 
	def set_pilot( self, oldValue ):
		thisPlayer = BigWorld.player()
		
		# If this call is result of a dismount
		if self.pilot == 0:
			
			# If this Player is dismounting
			if oldValue == thisPlayer.id:
			
				# Remove from player's list of wards
				thisPlayer.base.controlVehicle( self.id, 0 )
				
				# Remove Player control (physics no longer available)
				BigWorld.controlEntity( self, 0 )
				
				# Set appropriate filter for server controlled Entity
				self.filter = BigWorld.DumbFilter()
				
				# Teleport player off vehicle
				thisPlayer.physics.teleportVehicle( None )
				
				# Reactivate falling for player
				thisPlayer.physics.fall = 1
				
				# Set the appropriate targeting capabilities, so we can target and use the vehicle
				self.targetCaps = [Caps.CAP_CAN_USE]
		
				# Set camera to follow player
				BigWorld.camera().target = thisPlayer.matrix
				
			# Restore model
			BigWorld.entities[oldValue].setInvisible( 0 )
		
		# Otherwise this call is confirmation of mount request
		else:
		
			# If this Player is mounting
			if self.pilot == thisPlayer.id:
		
				# Add vehicle to player's list of wards
				thisPlayer.base.controlVehicle( self.id, 1 )
				
				# Allow Player control (physics now available)
				BigWorld.controlEntity( self, 1 )
				
				# Set physics type and properties (see python documentation)
				self.physics = BigWorld.STANDARD_PHYSICS
				self.physics.velocity		= ( 0.0, 0.0, 0.0 )
				self.physics.velocityMouse	= "Direction"
				self.physics.angular		= 0
				self.physics.angularMouse	= "MouseX"
				self.physics.collide = 1
				self.physics.fall = 1
				self.physics.modelWidth = 0.4
				self.physics.modelDepth = 0.3
				
				# Set appropriate filter for client controlled Entity
				self.filter = BigWorld.AvatarDropFilter()

				# Disable falling for player.  This is because vehicles are also used 
				# for moving platforms, whereby the player will be teleported off the 
				# vehicle when they step off it.  The fall mechanism should be disabled 
				# when the player is in control of the vehicle, rather than just moving 
				# around in/on it.
				thisPlayer.physics.fall = 0
				
				# Teleport player onto vehicle.  At this point 
				# the player's input will be redirected to the 
				# vehicle - see Avatar::handleKeyEvent().
				thisPlayer.physics.teleportVehicle( self )
				
				# Remove targeting capabilities
				self.targetCaps = []
				
				# Set camera to follow vehicle
				BigWorld.camera().target = self.matrix
				
			# Hide model
			BigWorld.entities[self.pilot].setInvisible( 1 )
			

	# Called by FantasyDemo when the Player uses a targeted Entity
	def use( self ):
	
		# This will notify the server of the Player's intent.
		# The server will set the pilot property if ok.
		# We recieve notification of chage to initiate process.
		self.cell.mount()
	

	# Called when Avatar leaves world and is using vehicle - see Avatar.onLeaveWorld()
	def pilotDead( self ):
	
		# This will free the vehicle for use by other players
		# The client may be dead, but that's ok, client just won't receive a response...
		self.cell.dismount()

	
	# Player will pass control to vehicle when boarded
	def handleKeyEvent( self, isDown, key, mods ):
		
		if isDown:
			if key == Keys.KEY_W:
				self.physics.velocity = (0, 0, 10)
				return 1
			elif key == Keys.KEY_S:
				self.physics.velocity.z = (0, 0, -10)
				return 1
			elif key == Keys.KEY_ESCAPE:
				self.cell.dismount()
				return 1
		else:
			if key == Keys.KEY_W:
				print "-W"
				self.physics.velocity = (0, 0, 0)
				return 1
			elif key == Keys.KEY_S:
				self.physics.velocity.z = (0, 0, 0)
				return 1
				
		return 0
