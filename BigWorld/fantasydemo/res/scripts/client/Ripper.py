"""This module implements the Ripper entity type."""


import math
import random
from functools import partial
import BigWorld
import FantasyDemo
import Keys
from Math import *
import AvatarModel
from Avatar import Avatar
from Helpers import PSFX
from Helpers import Caps
from Helpers import BWKeyBindings
from Helpers.BWKeyBindings import BWKeyBindingAction
from FDGUI import Minimap


class Ripper( BigWorld.Entity ):
	stdModel = "sets/vehicles/razor2.model"
	stdFlare = "sets/vehicles/razor_flare.model"
	dustParticles = "particles/ripper_dust.xml"
	breathParticles = "particles/ripper_breath.xml"
	NULL_MODEL_NUMBER = -1

	OUTSIDE_OFFSETX = -0.900
	OUTSIDE_OFFSETZ = 0.587

	def __init__( self ):
		BigWorld.Entity.__init__( self )
		self.pilotAvatar = None


	def prerequisites( self ):
		prerequisit = []
		prerequisit.append( Ripper.stdModel )
		prerequisit.append( Ripper.stdFlare )
		prerequisit.append( Ripper.dustParticles )
		prerequisit.append( Ripper.breathParticles )
		#prerequisit.append( "maps/fx/environment/dust.tga" )
		return prerequisit


	def onEnterWorld( self, prereqs ):
		self.targetCaps = [Caps.CAP_CAN_USE]

		self.filter = BigWorld.DumbFilter()

		self.model = prereqs[ Ripper.stdModel ]
		self.model.motors[0].entityCollision = 1
		self.model.motors[0].collisionRooted = 1
		self.focalMatrix = self.model.node("HANDPOS_left")

		self.model.root.attach( prereqs[Ripper.dustParticles] )

		breath = prereqs[Ripper.breathParticles]
		breath.system(0).action(1).sleepPeriod = random.randint( 40, 80 ) / 10.0
		self.model.root.attach( breath )

		BigWorld.addShadowEntity( self )
		Minimap.addEntity( self )

		if self.pilotID != -1:
			# the ripper is already being piloted so we need to add
			# the stand-in model and set the idle animations going

			self.model.RIdle()

			self.model.flare = BigWorld.Model( Ripper.stdFlare )
			self.model.flare.Go( 0, self.model.flare.On )

			self.filter = BigWorld.AvatarFilter()

			pilot = BigWorld.entity( self.pilotID )

			self.model.mount = None


	# This function is called by avatar when it enters the world.
	def passengerEnterWorld( self, pilot ):
		pilot.model.visible = False
		pilot.model.motors[0].entityCollision = False
		if self.model.mount == None:
			unpackedPilotModel = AvatarModel.unpack( pilot.avatarModel )
			self.model.mount = AvatarModel.create( unpackedPilotModel, BigWorld.Model('') )
			self.model.mount.RipperPilotIdle()
			self.model.mount.visible = True

			pilot.targetCaps = []


	def onLeaveWorld( self ):
		Minimap.delEntity( self )
		BigWorld.delShadowEntity( self )
		self.model.mount = None
		self.model.flare = None
		self.model = None


	# The player wants to use us
	def use( self ):
		self.playerActionCommence()
		self.walkToMountPosition()


	def playerActionCommence(self):
		BigWorld.player().moveActionCommence()
		BigWorld.player().allowFirstPersonModeToggle(False)


	def playerActionComplete(self):
		BigWorld.player().actionComplete()
		BigWorld.player().allowFirstPersonModeToggle(True)


	def walkToMountPosition( self, success = True ):
		WALK_TIMEOUT = 10
		VERTICAL_OFFSET_ALLOWED = 2.0
		player = BigWorld.player()

		if not success or self.pilotID != -1:
			player.model.Shrug( 0, player.actionComplete )
			self.playerActionComplete()
			return

		rpos = Vector3( self.position )
		rdir = Vector3( math.sin(self.yaw), 0, math.cos(self.yaw) )
		currOff = Vector3( player.position ) - rpos

		# Is the player is on the wrong side of the Ripper?
		if (currOff * rdir).y < 0:
			roffx = -0.886
			if currOff.dot( rdir ) > 0:
				# Is in front
				roffz = 3.11
			else:
				# Is behind
				roffz = -2.88

			ppos = Vector3( roffz * rdir.x + roffx * rdir.z, 0, roffz * rdir.z - roffx * rdir.x ) + rpos

			player.physics.velocity = ( 0, 0, player.walkFwdSpeed )
			player.physics.seek( (ppos.x, ppos.y, ppos.z, player.yaw), WALK_TIMEOUT, \
									VERTICAL_OFFSET_ALLOWED, self.walkToMountPosition )
			return

		( x, y, z ), ( yaw, pitch, roll ) = self.getMountDismountPosition()

		player.physics.velocity = ( 0, 0, BigWorld.player().walkFwdSpeed )
		player.physics.seek( ( x, y, z, yaw ), WALK_TIMEOUT, VERTICAL_OFFSET_ALLOWED, self.arriveAtMountPosition)


	# This callback is called when the player has finished seeking toward to mount position.
	# 		success 		Describes whether the final seek to the vehicle was successful
	def arriveAtMountPosition( self, success ):
		player = BigWorld.player()

		if not success or self.pilotID != -1:
			player.model.Shrug( 0, player.actionComplete )
			self.playerActionComplete()
			return

		player.allowFirstPersonModeToggle(True)
		player.toggleFirstPersonMode( False )
		player.allowFirstPersonModeToggle(False)

		if player.rightHand != -1:
			player.equip( -1 )

			waitTime = 0.0
			waitTime += player.model.action( 'ChangeItemBegin' ).duration
			waitTime += player.model.action( 'ChangeItemEnd' ).duration

			BigWorld.callback(waitTime, self.cellMountVehicle)
		else:
			self.cellMountVehicle()


	def cellMountVehicle(self):
		if BigWorld.player()._isConnected():
			self.cell.mountVehicle()
		else:
			def mount():
				self.mountVehicle(1, BigWorld.player().id)

			BigWorld.callback(1, mount)


	# This is a callback seen to all clients to announce that an avatar is boarding the vehicle.
	# At this point the client will have been given control of the ripper from the server and the
	# pilotID should already be set appropriately.
	#		succeeded 				Describes whether the action to board the vehicle was successful
	#		pilotAvatarID			The ID of the avatar boarding the vehicle. This is not nesseseraly
	#								this client's avatar ID.
	def mountVehicle( self, succeeded, pilotAvatarID ):
		# cleanup on mount failure
		if not succeeded:
			if BigWorld.player().id == pilotAvatarID:
				self.playerActionComplete()
			return

		pilot = BigWorld.entities[pilotAvatarID]

		# stop all previous actions
		for actionName in pilot.model.queue:
			pilot.model.action(actionName).stop()
		for actionName in self.model.queue:
			self.model.action(actionName).stop()
		if self.model.mount:
			for actionName in self.model.mount.queue:
				self.model.mount.action(actionName).stop()

		if BigWorld.player().id == pilotAvatarID:

			self.pilotAvatar = pilot
			BigWorld.player(self)

			unpackedPilotModel = AvatarModel.unpack( self.pilotAvatar.avatarModel )
			self.model.mount = AvatarModel.create( unpackedPilotModel, BigWorld.Model('') )

			self.pilotAvatar.model.visible = False
			self.pilotAvatar.physics.collide = False
			self.pilotAvatar.physics.fall = False		# Note: important otherwise apply gravity will alight us from the vehicle

			# setup callback to receive
			# when the animation finishes
			BigWorld.callback(self.model.Board.duration, self.finishMountVehicle)
		else:
			# this client is not controlling this ripper but
			# someone has just hopped on so make it appear to idle

			if pilot and pilot.inWorld:
				unpackedPilotModel = AvatarModel.unpack( pilot.avatarModel )
				self.model.mount = AvatarModel.create( unpackedPilotModel, BigWorld.Model('') )

				pilot.model.visible = False
				pilot.am.entityCollision = False

				pilot.targetCaps = []

			else:
				self.model.mount = None

			self.filter = BigWorld.AvatarFilter()

			# configure the Ripper's action matcher
			self.model.motors[0].entityCollision = True
			self.model.motors[0].collisionRooted = False

		def playIdle():
			self.model.RIdle()
			if self.model.mount:
				self.model.mount.RipperPilotIdle()

		# play the board actions
		self.model.Board().Boarded()
		if self.model.mount:
			self.model.mount.RipperPilotBoard().RipperPilotBoarded()
		BigWorld.callback(self.model.Board.duration, playIdle)

		self.model.flare = BigWorld.Model(Ripper.stdFlare)
		self.model.flare.Go(0, self.model.flare.On)


	def finishMountVehicle( self ):
		self.pilotAvatar.physics.teleport( self.position, ( self.yaw, self.pitch, self.roll ) )
		# Turn off player physics so that player position never changes relative
		# to the ripper. Theoretically, physics should not change player's
		# position but the accumulation of floating point errors means that
		# the player does move slightly with each tick so if you ride on the
		# ripper for an extended period, the player's position could be way off.
		self.pilotAvatar.physics = BigWorld.DUMMY_PHYSICS

		self.physics = BigWorld.HOVER_PHYSICS
		self.physics.turn = 0
		self.physics.thrust = 0
		self.physics.brake = 0
		self.physics.collide = 1
		self.physics.fall = 1
		self.physics.ripperTurnRate = 0.5
		self.physics.ripperZDrag = 0.99


	# This function is a callback sent to all clients with this ripper in their area of interest.
	#		pilotAvatar		The ID of the client avatar that sent the original dismount request.
	# Called by Ripper.dismount() on the cell.
	# When this is called the server has already taken back control of the ripper.
	def dismountVehicle( self, pilotAvatarID ):
		pilot = BigWorld.entity( pilotAvatarID )
		if pilot:
			for actionName in pilot.model.queue:
				pilot.model.action(actionName).stop()
			pilot.am.entityCollision = True

		if BigWorld.player().id == pilotAvatarID:
			pos, dir = self.getMountDismountPosition()
			BigWorld.player().physics.teleport( pos, dir )
			BigWorld.player().model.visible = False

			self.model.flare = None
			self.filter = BigWorld.DumbFilter()

			# play the board actions
			self.model.Alight().Alighted()
			self.model.mount.RipperPilotAlight().RipperPilotAlighted()

			# setup callback to receive when the animation finishes
			BigWorld.callback( self.model.Alight.duration, self.finishDismountVehicle )
		else:
			self.model.Alight().Alighted()
			# Pilot may not yet have entered the world
			if self.model.mount != None:
				self.model.mount.RipperPilotAlight().RipperPilotAlighted()

			# setup callback to receive when the animation finishes
			def removeMount(self):
				self.model.mount = None

				assert isinstance( pilot, Avatar )
				pilot.set_avatarModel( pilot.model )

			BigWorld.callback( self.model.Alight.duration, lambda: removeMount( self ) )



	def finishDismountVehicle( self ):
		BigWorld.player().physics.userDirected = True
		BigWorld.player().physics.fall = True

		self.model.mount = None
		BigWorld.player().model.visible = True

		self.playerActionComplete()


	# This function produces the position and orientation that the model
	# will need to be standing ( in world space ) to line up with the mount and dismount animations.
	def getMountDismountPosition( self ):
			rpos = Vector3( self.position )
			rdir = Vector3( math.sin(self.yaw), 0, math.cos(self.yaw) )

			roffx = Ripper.OUTSIDE_OFFSETX
			roffz = Ripper.OUTSIDE_OFFSETZ
			ppos = rpos + Vector3(	roffz * rdir.x + roffx * rdir.z,
									0,
									roffz * rdir.z - roffx * rdir.x )
			pyaw = self.yaw + math.pi/2.0

			return ppos, ( pyaw, 0, 0 )


	def cellDismountVehicle(self):
		if BigWorld.player()._isConnected():
			self.cell.dismountVehicle()
		else:
			def dismount():
				self.dismountVehicle(BigWorld.player().id)

			BigWorld.callback(1, dismount)


	def name( self ):
		return "Ripper"


	vehicleActions = [	"RIdle",
						"RTurnLeft",
						"RTurnRight",
						"Stop",
						"Thrust" ]

	pilotActions = [	"RipperPilotIdle",
						"RipperPilotTurnLeft",
						"RipperPilotTurnRight",
						"RipperPilotStop",
						"RipperPilotThrust" ]

	vehicleTransitionActions = [	"",
									"RTurningLeft",
									"RTurningRight",
									"Stopping",
									"Thrusting" ]

	pilotTransitionActions = [		"",
									"RipperPilotTurningLeft",
									"RipperPilotTurningRight",
									"RipperPilotStopping",
									"RipperPilotThrusting" ]



class PlayerRipper( Ripper, BWKeyBindings.BWActionHandler ):

	def onBecomePlayer( self ):
		self.setupActionList()
		FantasyDemo.rds.keyBindings.addHandler( self )

		self.filter = BigWorld.PlayerAvatarFilter()

		FantasyDemo.cameraType( FantasyDemo.rds.FLEXI_CAM )

		self.forwardThrust = 0.0
		self.backwardThrust = 0.0
		self.leftwardTurn = 0.0
		self.rightwardTurn = 0.0
		self.thrustStrength = 2.5

		self.doingAction = 0

		BigWorld.target.caps( Caps.CAP_NONE )

		self.wantTurn = 0
		self.wantMove = 1

		self.pilotAvatar.physics.teleport( self.position, ( 0, 0, 0 ) )

		if self.model.inWorld:
			self.checkAnims()


	def onBecomeNonPlayer( self ):
		self.pilotAvatar = None
		self.filter = BigWorld.DumbFilter()
		self.keyBindings = []
		FantasyDemo.rds.keyBindings.removeHandler( self )


	def handleKeyEvent( self, event ):
		if event.isRepeatedEvent() or not ( self.physics != None and self.inWorld ):
			return False

		FantasyDemo.rds.keyBindings.callActionForKeyState( event.key )

		self.updateThrust()

		return True


	def updateThrust( self ):
		if self.physics == None:
			return

		if not self.doingAction and self.physics.ripperZDrag < 1:
			self.physics.thrust = self.thrustStrength * ( self.forwardThrust -
				self.backwardThrust )
			self.physics.turn = self.rightwardTurn - self.leftwardTurn
		else:
			self.physics.thrust = 0
			self.physics.turn = 0

		self.checkAnims()


	# Handle dismount key event.
	#		isDown	The state of the key.
	@BWKeyBindingAction( "EscapeKey" )
	def beginDismount( self, isDown ):
		# Check that we have not already disembarked
		if ( not isDown ) or BigWorld.player() != self:
			return

		# initPhysics() re-enables collision and falling.
		self.pilotAvatar.initPhysics()
		self.pilotAvatar.physics.collide = False
		self.pilotAvatar.physics.fall = False

		# Turn off the ripper so it drops to the ground
		self.physics.userDirected = False
		self.physics.ripperElasticity = 0
		self.physics.ripperDesiredHeightFromGround = 0
		self.physics.ripperTurnRate = 0

		self.model.flare.Stop( 0, self.model.flare.Off )

		# wait for Ripper to fall to the ground
		BigWorld.callback( 0.5, self.dismountStep )


	# This function is recursively called until the ripper comes to a rest.
	def dismountStep( self ):
		# continue to wait if the Ripper has not yet come to a halt
		if self.physics.moving:
			BigWorld.callback( 0.5, self.dismountStep )
			return

		# park the Ripper
		self.physics = BigWorld.STANDARD_PHYSICS
		self.physics.thrust = 0
		self.physics.brake = 1
		self.physics.ripperZDrag = 1
		self.model.motors[0].entityCollision = 1
		self.model.motors[0].collisionRooted = 1

		# Make the avatar the player again.
		# Note: This will change the type of the ripper from a PlayerRipper
		# to a Ripper so PlayerRipper functions will not be available from now on.
		BigWorld.player( self.pilotAvatar )

		self.playerActionCommence()
		BigWorld.player().model.visible = False
		BigWorld.player().physics.fall = False

		self.cellDismountVehicle()


	# Update the animations of the ripper and pilot model
	# This is run only on the controlling client as it requires
	# parameters from the physics object.
	# This code will ultimately be replaced by an action matcher
	# but for now the action matcher does not provide the functionality
	# required to animate both the ripper and the pilot.
	# Note: Called by Physics::hoverStyleTick()
	def checkAnims( self ):
		if self.physics == None:
			return

		if self.physics.ripperZDrag < 1:
			if self.physics.thrust < 0:
				self.physics.brake = -self.physics.thrust
				self.physics.thrust = 0
			else:
				self.physics.brake = 0

		ethrust = self.physics.thrust
		ethrust -= self.physics.brake
		if ethrust > 1: ethrust = 1

		# Animation only below here

		if len( self.model.queue ) > 0 and self.model.queue[0] == 'Alight':
			return

		self.wantTurn = self.physics.turn
		if self.wantTurn < 0 : self.wantTurn = -1
		if self.wantTurn > 0 : self.wantTurn = 1

		self.wantMove = ethrust
		if self.wantMove < 0 : self.wantMove = -1
		if self.wantMove > 0 : self.wantMove = 1

		if self.wantTurn != 0:
			act = (self.wantTurn+1)/2 + 1
		elif self.wantMove != 0:
			act = (self.wantMove+1)/2 + 3
		else:
			act = 0

		act = int(act)

		ripperAction = self.model.action(Ripper.vehicleActions[act])
		ripperAction()
		BigWorld.callback(
			ripperAction.duration - ripperAction.blendOutTime - 0.0001,
			partial( self.playTransitionAction, act,
					 self.wantTurn, self.wantMove ) )

		if self.model.mount:
			self.model.mount.action(Ripper.pilotActions[act])()


	# This function is a callback used by checkAnims to handle actions
	# that transition between different behaviours (turning, stopping etc).
	def playTransitionAction( self, act, oldTurn, oldMove ):
		# If the player logs off while on the ripper, a callback to this may still be pending.
		# In this case, the class of self will have changed and we won't be able to do this.
		if not isinstance( self, PlayerRipper ):
			return

		if self.wantTurn != oldTurn or self.wantMove != oldMove:
			return

		if Ripper.vehicleTransitionActions[act] == "":
			return

		if self.model.queue[0] == 'Alight':
			return

		self.model.action( Ripper.vehicleTransitionActions[act] )()
		if self.model.mount:
			self.model.mount.action( Ripper.pilotTransitionActions[act] )()


	# This function is necessary to use the chat consol while the Ripper is the player.
	def handleConsoleInput( self, string ):
		if self.pilotAvatar:
			self.pilotAvatar.cell.chat( unicode(string) )
			FantasyDemo.addChatMsg( self.id, string )


	# This method handles collision callbacks from the ripper physics.
	def onCollide( self, newMomentum, collidePosition, severity, triangleFlags ):
		speed = newMomentum.length

		if speed > 0.5:
			PSFX.worldExplosion( self.model, newMomentum, collidePosition, triangleFlags, 50 )

			# severity is a dot product between old and new momentum.
			# thus if less than zero, it was a head-on collision,
			# around to +1 which is a minor glance

			# Sound calls disabled because sound events are missing from soundbank.

# 			if ( severity < 0.5 ):
# 				self.model.playSound( "seeker/explosion" )
# 			else:
# 				self.model.playSound( "players/hurt" )


	@BWKeyBindingAction( "MoveForward" )
	def moveForward( self, isDown ):
		if isDown:
			self.forwardThrust = 1.0
		else:
			self.forwardThrust = 0.0


	@BWKeyBindingAction( "MoveBackward" )
	def moveBackward( self, isDown ):
		if isDown:
			self.backwardThrust = 1.0
		else:
			self.backwardThrust = 0.0


	@BWKeyBindingAction( "TurnLeft" )
	def	turnLeft( self, isDown ):
		if isDown:
			self.leftwardTurn = 1.0
		else:
			self.leftwardTurn = 0.0


	@BWKeyBindingAction( "TurnRight" )
	def turnRight( self, isDown ):
		if isDown:
			self.rightwardTurn = 1.0
		else:
			self.rightwardTurn = 0.0


	@BWKeyBindingAction( "MoveUpward" )
	def moveUpward( self, isDown ):
		if isDown:
			self.physics.thrustAxis = (0,1,0)
			self.thrustStrength = 5.0
		else:
			self.physics.thrustAxis = (0,0,1)
			self.thrustStrength = 2.5


	def name( self ):
		return "Player Ripper"
		

def create():
	player = BigWorld.player()
	return BigWorld.createEntity('Ripper', player.spaceID, 0, player.position, (0,0,0), {})

#Ripper.py
