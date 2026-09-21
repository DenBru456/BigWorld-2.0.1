import sys
import math
import traceback
import BigWorld
import FantasyDemo
import Seat
import GUI
import random
import weakref
from functools import partial
import particles
import DroppedItem
import AvatarMode as Mode
import FX
import Math
from Math import Vector3
import Item
import Pixie
import TeleportSource as TeleportSource
import IndoorMapInfo
from WebScreen import WebScreen

import FDGUI
from FDGUI import Minimap

from Helpers import ConsoleCommands
from Helpers import PSFX
#from Helpers import itemGui
from Helpers import projectiles
from Helpers import collide

import Keys
from Helpers import Caps
from Helpers import BWKeyBindings
from Helpers.BWKeyBindings import BWKeyBindingAction
from Listener import Listenable
from Helpers.CallbackHelpers import *

from Helpers import XMPP
import XMPPRoster


from Math import *
from bwdebug import *

import AvatarModel
import PlayerModel
import Merchant
import Inventory



from ModeTarget import ModeTarget

DEBUG_NAVIGATION_PATHS = False

# ------------------------------------------------------------------------------
# Section: class Avatar
# ------------------------------------------------------------------------------
# Note: Any NPC class derived from Avatar must override the enterDeadMode()
# method otherwise they will play the respawn and teleport animation.
# ------------------------------------------------------------------------------


# helper class

class CoordinatedActionPlayer:
	"TODO: Document."

	def __init__( self, enA, enB, resA, resB, doneA = None, doneB = None ):
		self.enA = enA
		self.enB = enB
		self.resA = resA
		self.resB = resB
		self.callCount = 0
		self.doneA = doneA
		self.doneB = doneB

	def __call__( self ):
		self.callCount += 1

		if self.callCount == 2:
			if self.doneA != None:
				self.enA.model.action( self.resA )( 0, self.doneA )
			else:
				self.enA.model.action( self.resA )( 0, self.enA.actionComplete )
			if self.doneB != None:
				self.enB.model.action( self.resB )( 0, self.doneB )
			else:
				self.enB.model.action( self.resB )( 0, self.enB.actionComplete )
		elif self.callCount != 1:
			print "CoordinatedActionPlayer called too many times!"


# helper fns for GestureActions.
def swordSwingGesture( avatar, theAction ):
	loft = BigWorld.Loft( "maps/fx/fx_swish.bmp" )
	loft.maxAge = 0.15

	swordModel = avatar.model.right_hand
	node = swordModel.node("HP_sheath")
	node.attach(loft)
	loft.endPoint = swordModel.node("HP_tip")

	action = avatar.model.action( theAction.actionName )
	action( 0, partial(swordSwingGestureEnd, avatar, loft, node) )


def swordSwingGestureEnd( avatar, loft, node ):
	avatar.actionComplete()
	loft.threshold = 99999.0 # Set to something large to prevent any more trail to be added at this point.
	BigWorld.callback( loft.maxAge, partial(removeSwordSwingLoft, loft, node) )


def removeSwordSwingLoft( loft, node ):
	node.detach(loft)


# another helper class (really just a struct)
class GestureAction:
	"TODO: Document"

	def __init__( self, actionName, canMove, canHoldItem, soundToPlay="", fn=None ):
		self.actionName = actionName
		self.canMove = canMove
		self.canHoldItem = canHoldItem
		self.actionSound = soundToPlay
		self.fn = fn

	def play( self, model, completion ):
		# see if we have a list of actions or just one
		if type( self.actionName ) == type( (0,) ):
			for an in self.actionName[:-1]:
				model.action( an )()
			lastAction = self.actionName[-1]
		else:
			lastAction = self.actionName
		model.action( lastAction )()
		BigWorld.callback( model.action( lastAction ).duration - 0.3, completion )
		if ( self.actionSound != "" ):
			pass # model.playSound( self.actionSound )

# Named constants
STOW_PLACES = (
	SHOULDER,
	RIGHT_HIP,
	LEFT_HIP ) = range( 3 )

CONTEXT_HELP = (
	EXPLORE,
	MOUSE,
	BINOCULARS,
	SWORDFIGHT ) = range( 4 )


# the big avatar class
class Avatar( BigWorld.Entity, ModeTarget, Listenable ):
	"TODO: Document"

	combativeModes = (Mode.NONE, Mode.CROUCH, Mode.SNEAK, Mode.ALERT_SCAN)
	usingItemModes = (Mode.USING_ITEM, Mode.USING_ITEM_CROUCHED)
	crouchModes = (Mode.CROUCH, Mode.USING_ITEM_CROUCHED, Mode.THROW_CROUCHED, Mode.CATCH_CROUCHED)
	takeDownableModes = (Mode.NONE, Mode.CROUCH, Mode.SNEAK)

	STANCE_NEUTRAL = -1
	STANCE_BACKWARD = 0
	STANCE_FORWARD = 1
	STANCE_LEFT = 2
	STANCE_RIGHT = 3

	CL_HIT = 0
	CL_DESPERATE = 1
	CL_PARRY = 2
	CL_MISS = 3

	COD_SHOT = 0
	COD_SLAIN = 1
	COD_TAKEN_DOWN = 2
	COD_FELL = 3

	CAMERAMODE_NO_GUN = 1
	CAMERAMODE_WITH_GUN = 2

	# sfxActionMap: Map from action names to sound names or other specialfx such as sparks
	#				and their playback delay (in seconds)
	#
	# Sounds just use the plain sound name, sfx names are prefixed with "@": ie
	# @S = spark,
	# @B = blood
	#
	# NB: they are grouped (with blanks) by their animations
	# (ie anims are shared amoung actions)
	#
	sfxActionMap = {
		"CCPasFwdHit":		(("players/grunts/hurt", 0.500), ("@B", 0.500), ),
		"CCPasMidHit":		(("players/grunts/hurt", 0.500), ("@B", 0.500), ),
		"CCPasBakHit":		(("players/grunts/hurt", 0.500), ("@B", 0.500), ),

		"CCActSlay":		(("sword/shared/hit",	0.500),
							 ("footstep_grass_DL",	0.933),
							 ("footstep_grass_DR",	1.200),
							 ("players/bodyfall01",	1.500),
							 ("players/grunts/hurt",1.500),
							 ("players/bodyfall02",	2.035, -10),
							 ("players/bodyfall02",	2.200, -20),
							 ),

		"CCPasSlay":		(),

		"CCActFwdMiss":		(("sword/med/swish", 0.240), ),
		"CCActFwdParry":	(("sword/med/swish", 0.240), ),

		"CCPasFwdMiss":		(("sword/med/block", 0.500), ("@S", 0.500), ),
		"CCPasFwdParry":	(("sword/med/block", 0.500), ("@S", 0.500), ),

		"CCActFwdKnock":	(("sword/med/bigswish", 0.300), ),
		"CCActFwdHit":		(("sword/med/bigswish", 0.300), ("sword/shared/hit", 0.460), ),

		"CCPasFwdKnock":	(("sword/med/block", 0.500), ("@S", 0.500), ),

		"CCActMidMiss":		(("sword/med/swish", 0.400), ),
		"CCActMidParry":	(("sword/med/swish", 0.400), ),
		"CCActBakMiss":		(("sword/med/swish", 0.400), ),
		"CCActBakParry":	(("sword/med/swish", 0.400), ),

		"CCPasMidMiss":		(("sword/med/block", 0.500), ("@S", 0.500), ),
		"CCPasMidParry":	(("sword/med/block", 0.500), ("@S", 0.500), ),

		"CCPasMidKnock":	(("sword/med/block", 0.500), ("@S", 0.500), ),

		"CCActMidKnock":	(("sword/med/bigswish", 0.300), ),
		"CCActMidHit":		(("sword/med/bigswish", 0.300), ("sword/shared/hit", 0.500), ),
		"CCActBakKnock":	(("sword/med/bigswish", 0.300), ),
		"CCActBakHit":		(("sword/med/bigswish", 0.300), ("sword/shared/hit", 0.500), ),

		"CCPasBakKnock":	(("sword/med/block", 0.500), ("@S", 0.500), ),

		"CCPasBakMiss":		(("players/grunts/effort", 0.200), ),
		"CCPasBakParry":	(("players/grunts/effort", 0.200), ),
	}


	def __init__( self ):
		BigWorld.Entity.__init__( self )
		ModeTarget.__init__( self )
		Listenable.__init__( self )

		self.am = BigWorld.ActionMatcher( self )
		self.focalMatrix = MatrixProduct()

		self.healthHitTime = 0.0

		self.warp = None
		self.deathWarp = None
		self.alighting = 0		# used by Ripper.py

		self.overheadGui = None
		self.overheadIcon = None

		self.rightHandItem = None
		self.shoulderItem = None
		self.rightHipItem = None
		self.leftHipItem = None

		self._itemCache = {}

		self.targettingColour = (64,192,64,255)
		self.minimapColour = self.targettingColour

		# combat camera modes
		self.cameraMode = Avatar.CAMERAMODE_NO_GUN

		# Friends list. List order must correspond to base friendsList.
		self.friendsList = []

		self.cellBoundsModel = None
		#The current WebScreen being used
		self.currentWebScreen = None


	#---------------------------------
	# XMPP Example
	#---------------------------------

	# Callback methods from the XMPP interface on the Base
	def onXmppRegisterWithTransport( self, transport ):
		pass


	def onXmppDeregisterWithTransport( self, transport ):
		pass


	def onXmppMessage( self, friendID, transport, message ):
		pass


	def onXmppRoster( self, roster ):
		pass


	def onXmppRosterItemAdd( self, friendID, transport ):
		pass


	def onXmppRosterItemDelete( self, friendID, transport ):
		pass


	def onXmppPresence( self, friendID, transport, presence ):
		pass


	def onXmppError( self, message ):
		pass



	#---------------------------------
	# Note Data Store Example
	#---------------------------------
	def onAddNote( self, id ):
		return


	def onGetNotes( self, noteList ):
		return


	#---------------------------------
	# General Avatar methods
	#---------------------------------

	# This method is also used by the Ripper.
	def initPhysics( self ):
		self.physics = BigWorld.STANDARD_PHYSICS
		self.physics.velocity		= ( 0.0, 0.0, 0.0 )
		self.physics.velocityMouse	= "Direction"
		self.physics.angular		= 0
		self.physics.angularMouse	= "MouseX"
		self.physics.collide = 1
		self.physics.fall = 1
		self.physics.modelWidth = 0.47
		self.physics.modelDepth = 0.3


	# This method is called when the entity enters the world
	# Any of our properties may have changed underneath us,
	#  so we do most of the entity setup here
	def onEnterWorld( self, prereqs ):
		self.filter = BigWorld.AvatarFilter()

		self.setTargetCaps()

		self.am.turnModelToEntity = 0
		self.am.matcherCoupled = 1
		self.am.matchCaps = [2,]
		self.am.entityCollision = 1
		self.am.collisionRooted = 0
		self.am.footTwistSpeed = math.radians( 270 )

		self.entityDirProvider = BigWorld.EntityDirProvider(self, 1, 0)

		self.waitingMode = -1
		self.modelHidden = self.alighting
		self.inDeadState = 0
		self.causeOfDeath = Avatar.COD_SHOT
		self.tightFocus = -1

		self.rightHandItem = None

		# tell the team about it
		#Team.entityEntered( self )

		# set up our model and items
		orh = self.rightHand
		self._lockRHCounter = 0
		self.rightHand = Item.Item.NONE_TYPE

		#Never let self.model == None
		self.model = BigWorld.Model("")
		self.set_avatarModel()

		self.rightHand = orh
		self.set_rightHand( Item.Item.NONE_TYPE, 0 )

		BigWorld.addShadowEntity( self )

		if BigWorld.player() != None and BigWorld.player() != self:
			Minimap.addEntity( self )

		if self.vehicle and hasattr( self.vehicle, 'passengerEnterWorld' ):
			self.vehicle.passengerEnterWorld( self )

		# XMMP Friends list
		self.roster = XMPPRoster.XMPPRoster()


	# This method is called when the entity leaves the world
	def onLeaveWorld( self ):
		Minimap.delEntity( self )

		if self.warp != None:
			self.delModel( self.warp )
			self.warp = None

		if self.deathWarp != None:
			try:	self.delModel( self.deathWarp )
			except:	pass
			self.deathWarp = None

		# tell the team about it
		#Team.entityLeft( self )

		if self.mode == Mode.COMBAT_CLOSE:
			self.leaveCloseCombatMode()

		if hasattr( self, "doingAction" ):
			if self.doingAction > 0:
				self.actionComplete()

		# The code below may want to be put in at some stage. JWD 10/09/2002
		#self.worldTransition = 1
		#om = self.mode
		#self.mode = Mode.NONE
		#self.leaveMode()
		#self.mode = om
		#self.worldTransition = 0

		# If player is on a vehicle, let it know...
		#if not self.vehicle == None:
			#self.vehicle.pilotDead()

		BigWorld.delShadowEntity( self )
		BigWorld.target.exclude = self

		self.rightHandItem = None
		self.model = None

		self.overheadGui    = None
		self.overheadIcon   = None

		if hasattr( self, "waterListenerID" ):
			BigWorld.delWaterVolumeListener( self.waterListenerID )
			del self.waterListenerID



	def clientOnCreateCellFailure( self ):
		FantasyDemo.onCreateAvatarFailed()


	def setTargetCaps( self ):
		if self != BigWorld.player():
			#if self.mode == Mode.DEAD:
			#	if Team.members.has_key( self.id ):
			#		self.targetCaps = [Caps.CAP_CAN_REVIVE]
			#	else:
			#		self.targetCaps = [Caps.CAP_NEVER]
			#elif Team.members.has_key( self.id ):
			#	self.targetCaps = [Caps.CAP_CAN_BUG, Caps.CAP_CAN_USE, Caps.CAP_CAN_FEED]
			#else:
			self.targetCaps = [Caps.CAP_CAN_BUG, Caps.CAP_CAN_USE,
							   Caps.CAP_CAN_FEED, Caps.CAP_CAN_HIT,
							   Caps.CAP_CAN_TAKE_DOWN, Caps.CAP_CAN_MELEE,
							   Caps.CAP_CAN_SHONK]

	# Called by script (hack) to give us a simpler mesh, or not
	def toggleMesh( self, flag ):
		pass

	# Hide ourselves. Just hide, don't go away.
	@IgnoreCallbackIfDestroyed
	def hideModel( self, flag ):
		self.modelHidden = flag
		self.model.visible = not self.modelHidden

	# Returns true if we can set off a mine (by being near it)
	def canSetOffMine( self, mine ):
		return self.id != mine.owner

	# -------------------------------------------------------------------------
	# Section: Items trading
	# -------------------------------------------------------------------------

	def tradeActiveEnterMode( self ):
		'''Called when Avatar.mode gets set by the cell. The active
		Avatar takes care of setting up the stage, animating both characters
		and showing the trade icon if it's partner is this player.
		'''
		partner = ModeTarget._getModeTarget( self )
		if partner == None:
			ERROR_MSG( "Unable to find modeTarget entity: %s" % self.modeTarget )
			return

		player = BigWorld.player()
		self.tradeAnimateAccept()
		partner.tradeAnimateAccept()
		if partner == player:
			FantasyDemo.addChatMsg( -1, 'Player has agreed to trade with you' )
			player.tradeShowGUI( True )


	def tradeActiveLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell. Cleans the scene.
		'''
		player = BigWorld.player()
		if self.getLastModeTarget() == player:
			player.tradeShowGUI( False )


	def tradePassiveEnterMode( self ):
		'''Called when Avatar.mode gets set by the cell. If partner is this
		player, shows the trade icon and add a chat message to the console.
		'''
		player = BigWorld.player()
		if ModeTarget._getModeTarget( self ) == player:
			FantasyDemo.addChatMsg( -1, 'Player wants to trade with you' )


	def tradePassiveLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell.
		Clears trade icon if partner was this player.
		'''
		pass


	def tradeDeny( self ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def tradeAnimateAccept( self, endCallback = None ):
		'''Plays the trade accept animation on this avatar.
		'''
		if self.mode == Mode.TRADE_PASSIVE:
			self.model.Shake_B_Extend().Shake_B_Accept( 0, endCallback )
		elif self.mode == Mode.TRADE_ACTIVE:
			self.model.Shake_A_Extend().Shake_A_Accept( 0, endCallback )
		elif self.mode == Mode.COMMERCE:
			self.model.Shake_A_Extend().Shake_A_Accept( 0, endCallback )
		else:
			assert False, 'Not in trade or commerce mode'


	def tradeOfferItemNotify( self, itemType ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def tradeOfferItemDeny( self, tradeItemLock ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def tradeAcceptNotify( self ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def tradeCommitNotify( self, success, outItemsLock,
			outItemsSerial, outGoldPieces, inItemsTypes,
			inItemsSerials, inGoldPieces ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False

	# -------------------------------------------------------------------------
	# Section: Items locking
	# -------------------------------------------------------------------------

	def itemsLockNotify( self, lockHandle, itemsSerials, goldPieces ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def itemsUnlockNotify( self, success, lockHandle ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False

	# -------------------------------------------------------------------------
	# Section: Items commerce
	# -------------------------------------------------------------------------

	def commerceEnterMode( self ):
		'''Called when Avatar.mode gets set by the cell.
		The Avatar takes care of animating both characters.
		'''
		partner = ModeTarget._getModeTarget( self )
		if partner != None:
			partner.tradeAnimateAccept()
			self.tradeAnimateAccept()


	def commerceLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell. Does nothing.
		'''
		pass


	def commerceStartDeny( self ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def commerceItemsNotify( self, items ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False

	# -------------------------------------------------------------------------
	# Section: Items pick-up
	# -------------------------------------------------------------------------

	def pickUpResponse( self, success, droppedItemID, itemSerial ):
		'''Overriden by PlayerAvatar. Never called on non-player Avatars.
		'''
		assert False


	def pickUpNotify( self, droppedItemID ):
		'''Cell entity is notifying that this entity is picking up an item
		Params:
			droppedItemID		id of item entity being picked up
		'''
		try:
			droppedItem = BigWorld.entities[ droppedItemID ]
			self._pickUpProcedure( droppedItem )
			self.lockRightHandModel( True )
		except KeyError:
			print 'pickUpNotify for unknown entity: %d' % droppedItemID


	def _pickUpProcedure( self, droppedItem ):
		'''Do the pickup procedure.
		Params:
			droppedItem			item entity being picked up
		'''
		def doStep1():
			droppedItem.pickUpNotify( self )
			self.pickUpAnimate( doStep2, lambda: None )

		def doStep2():
			droppedItem.pickUpComplete()
			self.lockRightHandModel( False )

		doStep1()


	def pickUpAnimate( self, equipCallback, completeCallback ):
		'''Do a three step pick-up animation: (1) bend down,
		(2) pick-up/equip item and (3) raise up. Call equipCallback and
		completeCallback after step 2 and 3 respectively.
		Params:
			equipCallback		callback called when item is ready to be equiped
			completeCallback	callback called when animation has completed
		'''
		model = self.model.PickUpStart().PickUp( 0, equipCallback )
		model.PickUpComplete( 0, completeCallback )


	def disagree( self ):
		'''Play the disagree animation.
		'''
		self.actionCommence()
		self.didGesture( 4 )

	# -------------------------------------------------------------------------
	# Section: Items drop
	# -------------------------------------------------------------------------

	def dropNotify( self, droppedItem ):
		'''DroppedItem is notifying that this entity is dropping the item.
		Params:
			droppedItem			item entity being dropped
		'''
		self._dropProcedure( droppedItem )


	def _dropProcedure( self, droppedItem ):
		'''Do the drop procedure. Overriden by PlayerAvatar
		Params:
			droppedItem			item entity being dropped
		'''
		def doStep1():
			self.lockRightHandModel( True )
			self.dropAnimate( droppedItem, doStep2, lambda: None )

		def doStep2():
			droppedItem.dropComplete()
			self.lockRightHandModel( False )

		doStep1()


	def dropDeny( self ):
		'''Never called on non-player Avatars.
		'''
		assert False


	def dropAnimate( self, droppedItem, unequipCallback, completeCallback ):
		'''Do the drop animations itself in three parts. Decides what drop
		animation to play based on the distance from the entity to the item.
		Calls unequipCallback and completeCallback after steps 2 and 3,
		respectively.
		Params:
			droppedItem			item entity being dropped
			unequipCallback	callback called when item is ready to be unequiped
			completeCallback	callback called when animation has completed
		'''
		if self.mode == Mode.DEAD:
			unequipCallback()
			return

		queuer = self.model.PickUpStart().PickUp( 0, unequipCallback )
		queuer.PickUpComplete( 0, completeCallback )

	# -------------------------------------------------------------------------
	# Section: Feeding
	# -------------------------------------------------------------------------

	# We somehow ended up feeding something to someone (possibly ourself)
	def feed( self, item, targetID ):
		item

		if self != BigWorld.player():
			self.actionCommence()

		if self.rightHandItem.canEat:
			if targetID == 0:
				self.rightHandItem.eat( self )
			else:
				self.rightHandItem.feed( self, BigWorld.entity( targetID ) )
		else:
			print "Just what are you trying to eat?"
			self.actionComplete()


	# We somehow ended up eating something
	def eat( self, item ):
		item

		self.actionCommence()
		try:
			if self.rightHand == Item.Item.DRUMSTICK_TYPE:
				# BigWorld.playFxDelayed("eat_drumstick", 0.2, self.position)
				if random.random() < 0.2:
					pass # BigWorld.playFxDelayed("burp", 3.0, self.position)
				self.model.EatDrumstick(0,self.actionComplete);
				self.model.Fat()

			elif self.rightHand == Item.Item.GOBLET_TYPE:
				# BigWorld.playFxDelayed("drink", 0.2, self.position)
				if random.random() < 0.2:
					pass # BigWorld.playFxDelayed("burp", 3.5, self.position)
				self.model.DrinkFromFlask( 0,self.actionComplete )
				self.model.Skinny()

			else:
				print "Just what are you trying to eat?"
				self.actionComplete()
		except:
			self.actionComplete()


	# We made an unsucessful attempt at assailing someone
	#  (never called if we're the player)
	def assail( self ):
		if self.rightHandItem != None:
			self.rightHandItem.enact( self, None )

	def inMeleeCombat( self ):
		return self.rightHandItem != None and ( self.rightHandItem.canSwing )

	# utility function
	def inCombat( self ):
		return self.rightHandItem != None and ( self.rightHandItem.canShoot or self.rightHandItem.canSwing )

	def enterWaterCallback( self, entering, volume ):
		if entering:
			self.am.matchCaps = [16,]
		else:
			self.am.matchCaps = [2,]


	def set_avatarModel( self, oldValue = None, callback = lambda: None ):

		unpackedAvatarModel = AvatarModel.unpack( self.avatarModel )

		BigWorld.loadResourceListBG( AvatarModel.getPrerequisites( unpackedAvatarModel ),
									partial( self.set_avatarModel_stage2, self.avatarModel, unpackedAvatarModel, callback ) )


	@IgnoreCallbackIfDestroyed
	def set_avatarModel_stage2( self, packedAvatarModel, unpackedAvatarModel, callback, resourceRefs ):

		# this is a workaround for models not properly restoring actions and their callbacks
		# bug: 22631
		if hasattr( self, "doingAction" ) and self.doingAction > 0:
			BigWorld.callback( 0.5, partial( self.set_avatarModel_stage2, packedAvatarModel, unpackedAvatarModel, callback, resourceRefs ) )
			return

		if self.avatarModel != packedAvatarModel:
			return

		# detach all items from previous model
		if hasattr(self.model, "right_hand"):
			self.model.right_hand = None
		if hasattr(self.model, "left_hip"):
			self.model.left_hip = None
		if hasattr(self.model, "right_hip"):
			self.model.right_hip = None
		if hasattr(self.model, "shoulder"):
			self.model.shoulder = None


		savedActionQueue = ResMgr.DataSection( 'savedActionQueue' )
		self.model.saveActionQueue( savedActionQueue )

		self.model = AvatarModel.create( unpackedAvatarModel, self.model )

		self.model.restoreActionQueue( savedActionQueue )

		orh = self.rightHand
		if self.rightHand != Item.Item.NONE_TYPE:
			self.rightHand = Item.Item.NONE_TYPE
			self.set_rightHand( orh, 0 )

		if hasattr( self, "waterListenerID" ):
			BigWorld.delWaterVolumeListener( self.waterListenerID )
			del self.waterListenerID

		try:
			self.waterListenerID = BigWorld.addWaterVolumeListener( self.model.node("biped Spine"), self.enterWaterCallback )
		except:
			self.waterListenerID = BigWorld.addWaterVolumeListener( self.model.matrix, self.enterWaterCallback )

		#self.set_colour()

		# Add any extra effects here based on the model.
		# Note: This should probably be based on the Avatar state.
		# In the case of persistent particle effects, the code should just
		# check that Avatar state check is normal.

		# TO DO: add glowing eyes for wraiths.

		#self.respawnEnergyMist = particles.respawnEnergyMist( self )

		if self.am.owner != None: self.am.owner.delMotor( self.am )
		self.model.motors = ( self.am, )

		try:
			self.setFocalNode()
		except:
			pass

		try:
			lfoot = self.model.node( "biped L Toe0" )
			rfoot = self.model.node( "biped R Toe0" )

			# create left & right feet
			footSoundPath = "players/footsteps"
			self.footTriggers = [BigWorld.FootTrigger( 0, footSoundPath ),
								 BigWorld.FootTrigger( 1, footSoundPath )]
			lfoot.attach( self.footTriggers[0] )
			rfoot.attach( self.footTriggers[1] )

			# Add dust trails.
			self.dustSource = particles.attachDustSource( self.model )
			try:
				self.footTriggers[0].dustSource = self.dustSource.action(1)
				self.footTriggers[1].dustSource = self.dustSource.action(1)
			except:
				self.footTriggers[0].dustSource = self.dustSource.system(0).action(1)
				self.footTriggers[1].dustSource = self.dustSource.system(0).action(1)
		except:
			print "ERROR: Unable to set up foot triggers for model ['%s']" % "', '".join( self.model.sources )

		# put any item back in our hand, shoulders and hip.
		if orh != Item.Item.NONE_TYPE:
			self.rightHand = orh
			self.set_rightHand( Item.Item.NONE_TYPE, 0 )
		self.set_shoulder()
		self.set_rightHip()
		self.set_leftHip()

		self.hideModel( self.modelHidden )

		try:
			# HeadTracker Setup.
			self.headNodeInfo = BigWorld.TrackerNodeInfo(
				self.model,
				"biped Head",
				[ ( "biped Neck", -0.20 ),
				  ( "biped Spine", 0.50 ),
				  ( "biped Spine1", 0.40 ) ],
				"None",
				-60.0, 60.0,
				-80.0, 80.0,
				360,
				45,
				0.1)

			self.gunAimingNodeInfo = BigWorld.TrackerNodeInfo(
				self.model,
				"biped Spine",
				[	( "biped Spine1", 1 ),
					( "biped Neck", 1 ) ],
				"biped Spine",
				-60.0, 60.0,
				-80.0, 80.0,
				270.0 )

			self.tracker = BigWorld.Tracker()
			self.model.tracker = self.tracker

			# this if test is temporary and should be removed
			# as soon as the beziel model get his skeleton fixed
			import Guard
			if not isinstance(self, Guard.Guard):
				if not (self.rightHandItem and self.rightHandItem.canShoot):
					self.tracker.nodeInfo = self.headNodeInfo
				else:
					self.tracker.nodeInfo = self.gunAimingNodeInfo
				self.tracker.directionProvider = self.entityDirProvider

			if self.mode == Mode.DEAD:
				self.disableAllTrackers()
		except:
			print "ERROR: Unable to set head tracker for model ['%s']" % "', '".join( self.model.sources )


		# Get our respective camera heights from the model.
		# TBD: Setting these first for now. Will get model info later.
		self.cameraHeightWhenStanding = self.model.height
		self.cameraHeightWhenCrouched = self.model.height * 0.5
		self.cameraHeightWhenSeated   = self.model.height * 0.65

		if self.mode == Mode.SEATED:
			FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenSeated, 0.0 )
		elif self.mode == Mode.CROUCH:
			FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenCrouched, 0.0 )
		else:
			FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenStanding, 0.0 )

		# set up the lip sync fashion
		self.setupLipSyncer()

		self.onModelChangeUpdateMode()

		callback()

	# morph target names for morphing lips
	lipMorphs = ('oh', 'ahh', 'angry')

	# set up lip syncing if we have it
	def setupLipSyncer( self ):
		if hasattr( self, "lipSyncer"):
			self.model.lipsMorpher = BigWorld.PyMorphControl()
			self.model.lipsMorpher.input = self.lipSyncer
			self.model.lipsMorpher.targetNames = Avatar.lipMorphs
		elif hasattr( self.model, "lipsMorpher" ):
			self.model.lipsMorpher = None

	def chooseColourFromTable( self, idx ):
		if not hasattr( self, "customColourTable" ):
			cols = []
			cols.append([  (0.254646, 0.493217, 0.273348, 1.000000) , (0.933844, 0.777852, 0.769663, 1.000000) , (0.398893, 0.522769, 0.206916, 1.000000) , (0.101148, 0.138710, 0.111911, 1.000000)  ])
			cols.append([  (0.651712, 0.804786, 0.637214, 1.000000) , (0.454525, 0.296249, 0.603035, 1.000000) , (0.552301, 0.365443, 0.334284, 1.000000) , (0.427665, 0.431813, 0.525500, 1.000000)  ])
			cols.append([  (0.338514, 0.843630, 0.319555, 1.000000) , (0.102077, 0.223424, 0.069588, 1.000000) , (0.477499, 0.479614, 0.093775, 1.000000) , (0.153238, 0.658224, 0.282533, 1.000000)  ])
			cols.append([  (0.383577, 0.915329, 0.895179, 1.000000) , (0.366810, 0.726941, 0.973709, 1.000000) , (0.448015, 0.315202, 0.232618, 1.000000) , (0.570178, 0.286184, 0.187847, 1.000000)  ])
			cols.append([  (0.619137, 0.469237, 0.537302, 1.000000) , (0.369039, 0.300652, 0.496189, 1.000000) , (0.461669, 0.406311, 0.222290, 1.000000) , (0.808304, 0.842354, 0.731943, 1.000000)  ])
			cols.append([  (0.365277, 0.354405, 0.698976, 1.000000) , (0.171019, 0.461236, 0.538547, 1.000000) , (0.823559, 0.088536, 0.286342, 1.000000) , (0.375137, 0.903168, 0.767630, 1.000000)  ])
			cols.append([  (0.401896, 0.554190, 0.910975, 1.000000) , (0.992968, 0.291006, 0.166388, 1.000000) , (0.210172, 0.191736, 0.186281, 1.000000) , (0.630907, 0.286023, 0.236809, 1.000000)  ])
			cols.append([  (0.612891, 0.585045, 0.627191, 1.000000) , (0.255579, 0.025262, 0.184869, 1.000000) , (0.467111, 0.669241, 0.226030, 1.000000) , (0.552551, 0.736929, 0.379236, 1.000000)  ])
			cols.append([  (0.478003, 0.438623, 0.290965, 1.000000) , (0.894686, 0.862873, 0.615390, 1.000000) , (0.671886, 0.552357, 0.281442, 1.000000) , (0.885097, 0.856283, 0.778209, 1.000000)  ])
			cols.append([  (0.522206, 0.451343, 0.232465, 1.000000) , (0.569357, 0.515254, 0.144128, 1.000000) , (0.461813, 0.073066, 0.234372, 1.000000) , (0.625959, 0.186348, 0.592377, 1.000000)  ])
			cols.append([  (0.888899, 0.553464, 0.173847, 1.000000) , (0.293426, 0.285857, 0.198984, 1.000000) , (0.547580, 0.092823, 0.267288, 1.000000) , (0.939010, 0.293352, 0.517629, 1.000000)  ])
			cols.append([  (0.759867, 0.959759, 0.982294, 1.000000) , (0.880115, 0.283955, 0.033396, 1.000000) , (0.266175, 0.537536, 0.438662, 1.000000) , (0.512929, 0.354165, 0.266605, 1.000000)  ])
			cols.append([  (0.600831, 0.743807, 0.703723, 1.000000) , (0.300400, 0.545004, 0.644512, 1.000000) , (0.688422, 0.340142, 0.004766, 1.000000) , (0.472573, 0.440426, 0.267864, 1.000000)  ])
			cols.append([  (0.578025, 0.845675, 0.745759, 1.000000) , (0.349171, 0.086918, 0.277436, 1.000000) , (0.590162, 0.227906, 0.554312, 1.000000) , (0.337594, 0.360935, 0.262908, 1.000000)  ])
			cols.append([  (0.623980, 0.672316, 0.189026, 1.000000) , (0.889134, 0.583676, 0.198866, 1.000000) , (0.892509, 0.731511, 0.831040, 1.000000) , (0.546391, 0.280228, 0.050640, 1.000000)  ])
			cols.append([  (0.899648, 0.528558, 0.941157, 1.000000) , (0.533302, 0.750191, 0.940004, 1.000000) , (0.665484, 0.199860, 0.366958, 1.000000) , (0.445581, 0.481421, 0.296309, 1.000000)  ])
			cols.append([  (0.597921, 0.487229, 0.327416, 1.000000) , (0.796666, 0.699612, 0.937783, 1.000000) , (0.277807, 0.083920, 0.114420, 1.000000) , (0.826359, 0.146185, 0.960009, 1.000000)  ])
			cols.append([  (0.149531, 0.438053, 0.002597, 1.000000) , (0.062633, 0.474245, 0.343709, 1.000000) , (0.773542, 0.469882, 0.313250, 1.000000) , (0.725692, 0.755280, 0.502405, 1.000000)  ])
			cols.append([  (0.159739, 0.195771, 0.325857, 1.000000) , (0.588584, 0.225984, 0.057916, 1.000000) , (0.234929, 0.333477, 0.505054, 1.000000) , (0.666816, 0.259040, 0.163941, 1.000000)  ])
			cols.append([  (0.768643, 0.270522, 0.107105, 1.000000) , (0.054516, 0.141897, 0.589053, 1.000000) , (0.615351, 0.653648, 0.588571, 1.000000) , (0.988234, 0.852759, 0.636260, 1.000000)  ])
			cols.append([  (0.830812, 0.718017, 0.028693, 1.000000) , (0.593831, 0.727215, 0.451927, 1.000000) , (0.287905, 0.462448, 0.150299, 1.000000) , (0.674195, 0.838175, 0.462626, 1.000000)  ])
			cols.append([  (0.913555, 0.646139, 0.555507, 1.000000) , (0.561943, 0.438088, 0.591138, 1.000000) , (0.226763, 0.228060, 0.592938, 1.000000) , (0.875686, 0.859162, 0.775180, 1.000000)  ])
			cols.append([  (0.500000, 0.200000, 0.100000, 1.000000) , (0.437556, 0.831906, 0.047606, 1.000000) , (0.268502, 0.470271, 0.089447, 1.000000) , (0.942319, 0.872523, 0.890474, 1.000000)  ])
			self.customColourTable = cols

		return self.customColourTable[ idx % len(self.customColourTable) ]



	# Someone set the item in our right hand
	# First Stage: Set up animations
	def set_rightHand( self, oldRH = None, itemChangeAnim = 1 ):
		if oldRH != None and oldRH == self.rightHand: return

		# if we're in the process of becoming the player, don't
		# call its functions (this is BAD that we have to do this!)
		if self == BigWorld.player() and self.physics == None:
			endFn = partial( Avatar.set_rightHandEnd, self )
		else:
			endFn = self.set_rightHandEnd

		# Test if the hard point exists for this model.
		try:
			self.model.right_hand
		except AttributeError, e:
			if len( "".join( self.model.sources ) ) > 0:
				print "ASSET ERROR: No hard point 'right_hand'  model ['%s']" % "', '".join( self.model.sources )
			return

		# stop any existing animations
		if self.inWorld:
			aq = self.model.queue
			haveCIB = "ChangeItemBegin" in aq
			haveCIE = "ChangeItemEnd" in aq

			# ... if we can't recycle them
			if haveCIE:
				# currently queue is only playing actions, not waiting ones
				self.model.ChangeItemEnd.stop()

		# increment the right hand lock counter.  when it goes back down to
		# zero, the model swap can take place.
		self.lockRightHandModel( True )

		# this is the item retrieval lock on the rhm.
		self.lockRightHandModel( True )

		# get the item, either this has been cached, or we need to bg load it
		if self._itemCache.has_key(self.rightHand):
			self.lockRightHandModel(False)
		else:
			#start the item loading, and increment the rhi counter again, only decrementing
			#it when the item has finished loading.
			Item.LoadBG(self.rightHand, partial(self.lockRightHandModel, False))

		# start the animations if we want them
		if self.inWorld:
			#Added this exception handler due to temporary lack of
			#Actions in models.  Should probably fix this in art not
			#with workarounds in code.
			if hasattr( self.model, "ChangeItemBegin" ):
				cib = self.model.ChangeItemBegin
				cibDur = cib.duration - cib.blendOutTime - 0.0001
			else:
				ERROR_MSG( "model does not have required action ChangeItemBegin" )
				endFn( itemChangeAnim )
				return

			if itemChangeAnim == 1:
				if haveCIE or not haveCIB:
					cib().ChangeItemEnd()
					#cib()
					#self.model.ChangeItemEnd( -cibDur )
					self.lastICAStarted = BigWorld.time()
				else:
					self.lastICAStarted += 0.0001
					cibDur -= BigWorld.time() - self.lastICAStarted
					if cibDur < 0: cibDur = 0.0001
			else:	# itemChangeAnim == 0
				if not (haveCIB or haveCIE):
					# have to be careful if there's one already running,
					# that its callback doesn't happen after ours,
					# so we wait the whole duration just in case
					# (this is the else case of this conditional)
					cibDur = 0

			if cibDur:
				BigWorld.callback( cibDur, partial( endFn, itemChangeAnim ) )
			else:
				endFn( itemChangeAnim )
		else:
			endFn( itemChangeAnim )


	# Second Stage: Swap actual item in hand
	def set_rightHandEnd( self, itemChangeAnim ):
		if self.rightHandItem != None:
			self.rightHandItem.unequip( self )

		if self.inWorld and itemChangeAnim == 1:
			pass # BigWorld.playFx("stow_item", self.position)

		self.lockRightHandModel( False )


		#tmp workaround for no action on some model.
		try:
			self.model.HoldUpright.stop()
		except AttributeError:
			pass


	def getItem( self, itemType, itemLoader = None ):
		if self._itemCache.has_key( itemType ):
			return self._itemCache[ itemType ]
		elif itemLoader:
			return Item.newItem( itemType, itemLoader.resourceRefs )
		elif hasattr(self, "itemLoader") and self.itemLoader:
			return Item.newItem( itemType, self.itemLoader.resourceRefs )
		else:
			#Note - should never reach this part of the code, doing so will cause a pause
			#in the main thread and indicates the background loading of items has gone awry.
			return Item.newItem( itemType )

	@IgnoreCallbackIfDestroyed
	def lockRightHandModel( self, lock, itemLoader = None ):
		if not lock:
			self._lockRHCounter -= 1
		else:
			self._lockRHCounter += 1

		assert self._lockRHCounter >= 0, 'Right hand lock went negative'

		if self._lockRHCounter == 0:

			self.rightHandItem = self.getItem( self.rightHand, itemLoader )
			if hasattr( self, "itemLoader" ):
				self.itemLoader = None

			if self.rightHandItem != None:
				self.model.right_hand = self.rightHandItem.model
				if self.inCombat():
					self.rightHandItem.enactDrawn( self )
				else:
					self.rightHandItem.enactIdle( self )
			else:
				self.model.right_hand = None
		elif itemLoader != None:
			#cache itemLoader until we need it.  When observing 3rd persons change
			#items that are already loaded in memory (for example when the player
			#avatar already has the item cached), the Item.loadBG call finishes
			#immediately, and the unlock calls to this fn ending up going like:
			#lockRightHandModel( false, itemLoader )  #lock goes to 1
			#lockRightHandModel( false, None )		  #lock goes to 0 - show new item
			#(The first one is called when the item is BG loaded - i.e. immediately)
			#(The second one is called when the switch item animation finishes)
			self.itemLoader = itemLoader


	# Someone changed the item on our shoulder.
	def set_shoulder( self, oldItem = None ):
		if oldItem != None and oldItem == self.shoulder:
			return

		# Unequip the old item if we had one
		if self.shoulderItem:
			del self.shoulderItem
			self.shoulderItem = None

		# Test if the hard point exists for this model.
		try:
			self.model.shoulder
		except:
			#print 'Avatar model does not have hardpoint: shoulder'
			return

		self.shoulderItem = self.getItem( self.shoulder )
		if self.shoulderItem != None:
			self.model.shoulder = BigWorld.Model(*self.shoulderItem.model.sources)
		else:
			self.model.shoulder = None


	# Someone changed the item on our right hip.
	def set_rightHip( self, oldItem = None ):
		if oldItem != None and oldItem == self.rightHip:
			return

		# Unequip the old item if we had one
		if self.rightHipItem:
			del self.rightHipItem
			self.rightHipItem = None

		# Test if the hard point exists for this model.
		try:
			self.model.right_hip
		except:
			#print 'Avatar model does not have hardpoint: right_hip'
			return

		self.rightHipItem = self.getItem( self.rightHip )
		if self.rightHipItem != None:
			self.model.right_hip = BigWorld.Model(*self.rightHipItem.model.sources)
		else:
			self.model.right_hip = None


	# Someone changed the item on our left hip.
	def set_leftHip( self, oldItem = None ):
		if oldItem != None and oldItem == self.leftHip: return

		# Unequip the old item if we had one
		if self.leftHipItem:
			del self.leftHipItem
			self.leftHipItem = None

		# Test if the hard point exists for this model.
		try:
			self.model.left_hip
		except:
			#print 'Avatar model does not have hardpoint: left_hip'
			return

		self.leftHipItem = self.getItem( self.leftHip )
		if self.leftHipItem != None:
			self.model.left_hip = BigWorld.Model(*self.leftHipItem.model.sources)
		else:
			self.model.left_hip = None


	# Someone changed our health
	def set_healthPercent( self, oldHealth = None ):
		# record the time that regeneration should start
		if oldHealth > self.healthPercent:
			self.healthHitTime = BigWorld.time() + 3.0
		else:
			self.healthHitTime = BigWorld.time()

		oldHealthPct = oldHealth / 100.0 if oldHealth is not None else None
		self.listeners.healthUpdated( self.healthPercent / 100.0, oldHealthPct )

		if self == BigWorld.target():
			FantasyDemo.rds.fdgui.updateTargetHealth()

		if self.mode == Mode.COMBAT_CLOSE and self.healthPercent == 0:
			self.set_stance( self.stance )

	# Someone updated our frag count
	def set_frags( self, oldFrags = None ):
		if BigWorld.player().id == self.id and self.frags > oldFrags:
			if self.frags != 1:
				FantasyDemo.addChatMsg( -1, "You now have %d frags" % self.frags )
			else:
				FantasyDemo.addChatMsg( -1, "You got your first frag" )

	# Someone set our mode
	def set_mode( self, oldMode = None ):
		if self.mode == oldMode:
			return

		self.cancelMode( oldMode )
		self.enterMode( oldMode )


	# Someone set our mode target
	def set_modeTarget( self, oldModeTarget = None ):
		# tell the old target about it:
		if oldModeTarget != None and oldModeTarget != Mode.NO_TARGET:
			oldTargetEntity = BigWorld.entity( oldModeTarget )
			if oldTargetEntity != None:
				BigWorld.entity( oldModeTarget ).modeTargetBlur( self )

		# tell the new target about it
		if self.modeTarget != Mode.NO_TARGET:
			newTargetEntity = BigWorld.entity( self.modeTarget )
			if newTargetEntity != None:
				BigWorld.entity( self.modeTarget ).modeTargetFocus( self )

		self.lastModeTarget = oldModeTarget


	def _onModeTargetReady( self ):
		"""
		Overridden ModeTarget method.
		"""
		DEBUG_MSG( "" )
		if ModeTarget._onModeTargetReady( self ):
			self.enterMode( Mode.NONE )


	def setModeTarget( self, targetID ):
		oldTarget = self.modeTarget
		self.modeTarget = targetID
		self.set_modeTarget( oldTarget )


	def getLastModeTarget( self ):
		try:
			return BigWorld.entities[ self.lastModeTarget ]
		except KeyError:
			errorMsg = 'Avatar.getModeTarget: unknown last target entity (id=%d)'
			print errorMsg % self.lastModeTarget
			return None


	# Going into shonk mode
	def enterShonkMode( self ):
		# If the target is this client's player, then inform the player of
		# the intention to shonk.
		target = ModeTarget._getModeTarget( self )
		if target == None:
			return

		if target == BigWorld.player():
			FantasyDemo.addChatMsg( -1,
				"%s would like to play Paper/Scissors/Rock with you." % self.name() )
			FantasyDemo.addChatMsg( -1,
				"Target %s and press [7] [8] or [9] on the numpad to play." % self.name() )

		self.model.ShonkWait()

	# Going into handshake mode
	def enterHandshakeMode( self ):
		# BigWorld.playFx("rustle", self.position)

		self.inIdle = 0
		self.am.turnModelToEntity = 0

		self.model.Shake_A_Extend().Shake_A_Idle()

		target = ModeTarget._getModeTarget( self )
		if target == None:
			return

		# If the target is this client's player, then inform the player of
		# the intention to shake hands.
		if target == BigWorld.player():
			FantasyDemo.addChatMsg( -1,
				"%s would like to shake your hands." % self.name() )
			FantasyDemo.addChatMsg( -1,
				"Target %s and left-click to accept the handshake." % self.name() )


	# Going into pull up mode
	def enterPullUpMode( self ):
		self.model.PullUpActiveBegin().PullUpActiveIdle()

		# doingAction is left on while we wait for the server response,
		# so we stop that action here before enterMode starts another.
		self.actionComplete()

		target = ModeTarget._getModeTarget( self )
		if target == None:
			return

		# If the target is this client's player, then inform the player of
		# the intention to pull-up.
		if target == BigWorld.player():
			BigWorld.callback( 1.0, self.informTargetOfLiftUp )


	@IgnoreCallbackIfDestroyed
	def informTargetOfLiftUp( self ):
		if self.mode == Mode.PULLUP:
			FantasyDemo.addChatMsg( -1,
				"%s would like to lift you up." % self.name() )
			FantasyDemo.addChatMsg( -1,
				"Target %s and left-click to agree to this." % self.name() )


	# Going into push up mode
	def enterPushUpMode( self ):
		self.model.PushUpActiveBegin().PushUpActiveIdle()

		# doingAction is left on while we wait for the server response,
		# so we stop that action here before enterMode starts another.
		self.actionComplete()

		target = ModeTarget._getModeTarget( self )
		if target == None:
			return

		# If the target is this client's player, then inform the player of
		# the intention to bunk-up.
		if target == BigWorld.player():
			BigWorld.callback( 1.0, self.informTargetOfBunkUp )

	@IgnoreCallbackIfDestroyed
	def informTargetOfBunkUp( self ):
		if self.mode == Mode.PUSHUP:
			FantasyDemo.addChatMsg( -1,
				"%s would like to give you a bunk up." % self.name() )
			FantasyDemo.addChatMsg( -1,
				"Target %s and left-click to agree to this." % self.name() )

	# Going into combat mode
	def enterCombatMode( self, locked, temporary ):
		if not temporary and self.rightHandItem:
			pass

		#AUSTIN GDC - move all matchCaps into items
		#if not locked:
		#	self.am.matchCaps = [0] + filter( lambda x : x>2, self.am.matchCaps )
		#	self.model.CombatL0Blender()
		#else:
		#	self.am.matchCaps = [0,2] + filter( lambda x : x>2, self.am.matchCaps )
		#	self.model.CombatL2Blender()
		#	self.enableTracker( self.gunAimingNodeInfo )

	# Going out of combat mode
	def leaveCombatMode( self, locked, temporary ):
		#AUSTIN GDC - move all matchCaps into items
		#self.am.matchCaps = filter( lambda x : x>2, self.am.matchCaps )

		if not temporary and self.rightHandItem:
			pass

		#AUSTIN GDC - remove combat blenders
		#if not locked:
		#	self.model.CombatL0Blender.stop()
		#else:
		#	self.model.CombatL2Blender.stop()
		#	self.enableTracker( self.headNodeInfo )

	# Going into crouch mode
	def enterCrouchMode( self ):
		self.model.EnterCrouch().Crouch()
		self.actionCommence()


	# Leaving crouch mode
	def leaveCrouchMode( self ):
		self.model.LeaveCrouch(0, self.actionComplete)

	def crouchActionMidway( self ):
		pass

	# Going into sneak mode
	def enterSneakMode( self ):
		pass
		#AUSTIN GDC - move all matchCaps into items
		#self.am.matchCaps = self.am.matchCaps + [6];

	# Leaving sneak mode
	def leaveSneakMode( self ):
		pass
		#AUSTING GDC - move all matchCaps into items
		#self.am.matchCaps = filter( lambda c: c != 6, self.am.matchCaps )


	# Going into seated mode
	def enterSeatedMode( self ):
		self.filter.callback( 0, partial( self.sitDownWait, 5 ) )

	# TODO: At the moment, we wait for up to 5 seconds for the target to be in
	# our AoI. We should not really do this.
	@IgnoreCallbackIfDestroyed
	def sitDownWait( self, count ):
		if BigWorld.entity( self.modeTarget ) != None:
			Seat.sitDown( self )
		elif count > 0:
			BigWorld.callback( 1, partial( self.sitDownWait, count-1 ) )

	# Leaving seated mode
	def leaveSeatedMode( self ):
		Seat.standUp( self )

	# Starting using the item in your hand
	def enterUsingItemMode( self ):
		if self.rightHand != Item.Item.NONE_TYPE:
			try: self.rightHandItem.retain( self )
			except:	self.actionCommence()

	# Stopping using the item in your hand
	def leaveUsingItemMode( self ):
		if self.rightHand != Item.Item.NONE_TYPE:
			try:	self.rightHandItem.release( self )
			except:	self.actionComplete()

	# Helper function for leaveUsingItemMode
	def doneWithLeftHand( self ):
		self.model.left_hand = None


	# Entering close combat
	def enterCloseCombatMode( self ):
		# If we're the player, we've already called actionCommence
		#  when we started the swing

		# Try fetching this entity now
		if BigWorld.entities.has_key( self.modeTarget ):
			self.ccTarget = BigWorld.entity( self.modeTarget )
		else:
			ERROR_MSG( "Unable to find modeTarget entity: %s" % self.modeTarget )
			self.ccTarget = None
			return

		# The fight doesn't start until one of the combatants is nominated
		#  as its director, by receiving a salida message.
		self.ccIsFightDirector = 0
		self.ccBreaking = 0

		# Play the appropriate combat idle animation
		self.set_stance()

		# If we're targetting the player let them know
		if self.ccTarget == BigWorld.player():
			BigWorld.player().ccRespond( self )

		self.listeners.enterCloseCombatMode()


	# Leaving close combat
	def leaveCloseCombatMode( self ):
		BigWorld.callback( 0.1, self.closeCombatDelayedExit )

		# Let us know it's all over
		self.closeCombatNo( self.ccTarget, 1 )

		# Let the target know it's all over too
		if self.ccTarget != None:
			try:
				self.ccTarget.closeCombatNo( self, 0 )
			except:
				pass

		self.listeners.leaveCloseCombatMode()

		# Remove close combat caps
		#AUSTING GDC - move all matchCaps into items
		#self.am.matchCaps = filter( lambda c: c not in range(8,11), self.am.matchCaps )

	# Tidy up after leaving close combat mode. Delayed to hopefully get
	# any messages which may change how we get out of the mode in time.
	@IgnoreCallbackIfDestroyed
	def closeCombatDelayedExit( self ):
		if self.inWorld:
			if self.healthPercent <= 0:
				BigWorld.callback( 1.0, self.actionComplete )
			elif self.ccBreaking:
				BigWorld.callback( 0.7, self.actionComplete )
			else:
				self.model.CCOver( 0, self.actionComplete )


	# The server has decided a new step in the dance
	def salida( self, result ):
		# See if we've had any of these messages before
		if not self.ccIsFightDirector:
			self.ccIsFightDirector = 1

			# Nope, let everyone know who's calling the shots
			self.ccTarget = BigWorld.entity( self.modeTarget )
			self.closeCombatGo( self.ccTarget, 1 )
			try:
				self.ccTarget.closeCombatGo( self, 0 )
			except:
				pass

		# OK, process the step as usual then
		self.closeCombatStepActive( result )


	# Being the target of close combat
	def closeCombatGo( self, assailant, weAreInitiator ):
		assailant
		weAreInitiator

		self.ccBreaking = 0

		self.am.turnModelToEntity = 1
		self.tracker.directionProvider = None

	# No longer the target of close combat
	def closeCombatNo( self, assailant, weAreInitiator ):
		assailant
		weAreInitiator

		if self.mode != Mode.DEAD:
			self.am.turnModelToEntity = 0
			self.tracker.directionProvider = self.entityDirProvider

	# The next step in the close combat dance (active)
	def closeCombatStepActive( self, lr ):
		# Choose our counterpart for this step
		if self.ccTarget == None:
			self.ccTarget = BigWorld.entity( self.modeTarget )
			try:
				self.ccTarget.closeCombatGo( self, 0 )
			except:
				pass
		elif not self.ccTarget.inWorld:
			try:
				self.ccTarget.closeCombatNo( self, 0 )
			except:
				pass
			self.ccTarget = None

		# Tell our dancing partner what to do
		try:
			# Could be none or could not have this fn
			self.ccTarget.closeCombatStepAnswer( lr )
		except:
			pass

		# If we got something from the server, then display it,
		#  otherwise just play a dummy action
		#if lr != -1:
		#	act = self.getCCAction( (lr >> 4) - 1, (lr & 7) - 1, (lr >> 3) & 1 )
		#	self.ccLastResult = -1
		#else:
		#	act = self.model.CCAttack1

		if (lr >> 6) == 1:
			act = self.ccActiveAction( lr & 0x3F )
			delay = 0
		else:
			act = self.ccPassiveAction( lr & 0x3F )
			delay = 8 / 30.0	# 8 frames delay

		if act: self.closeCombatPerform( act, delay )

	# The next step in the close combat dance (passive)
	def closeCombatStepAnswer( self, lr ):
		#if lr != -1:
		#	act = self.getCCAction( (lr & 7) - 1, (lr >> 4) - 1, not ((lr >> 3) & 1) )
		#else:
		#	act = self.model.CCParryR

		if (lr >> 6) == 1:
			act = self.ccPassiveAction( lr & 0x3F )
			delay = 8 / 30.0	# 8 frames delay
		else:
			act = self.ccActiveAction( lr & 0x3F )
			delay = 0

		if act: self.closeCombatPerform( act, delay );

	# This method performs an action for either the active or passive combatant
	def closeCombatPerform( self, act, delay ):
		# start the action running
		if act.impact[2] == 0:
			act( -delay )
		else:
			act( -delay, None, 1 )

		# give the action matcher a break
		#self.am.matcherCoupled = 0
		# no point doing this until we can do the thing below

		# move the entity position to the end of this action
		#self.position = Vector3(self.position) + Vector3(act.displacement)
		# can't move client entity position ... yet - we need the
		# filter modification thingy

		# Note: really want to turn on am after end of action ...
		# so it does the idle/stance thing for us... hmmm.
		# assumes that position will be right or not overriden by
		# server. ouch, this is not going to be nice.


	hitResultStrings = {
		CL_HIT: "hit",
		CL_DESPERATE: "desperate parry",
		CL_PARRY: "parry",
		CL_MISS: "miss",
		(1<<5) | 0: "slay",
		(1<<5) | 1: "break"
	}

	stancePartDict = {
		STANCE_NEUTRAL: "Mid",
		STANCE_BACKWARD: "Bak",
		STANCE_FORWARD: "Fwd",
		STANCE_LEFT: "Mid",
		STANCE_RIGHT: "Mid"
	}

	hitResultPartDict = {
		CL_MISS:		"Miss",
		CL_PARRY:		"Parry",
		CL_DESPERATE:	"Knock",
		CL_HIT:			"Hit"
	}

	# Play sounds and sparks
	def doFX(self, actionName):
		for soundAction in self.fxActionMap[actionName]:
			if soundAction[0][0] == "@":
				which = soundAction[0][1]
				f = None
				if which == 'S':
					# sparks
					if self.rightHandItem and self.rightHandItem.canSwing:
						f = self.rightHandItem.createSparks
				elif which == 'B':
					# blood
					f = partial( PSFX.attachBloodSpray, self.model,
						2,	# Direction, 1=left, 2=right
						5	# Number of blood sprays.
					)

				if f: BigWorld.callback( soundAction[1], f )
			else:
				if len(soundAction) == 3:
					pass 	# BigWorld.playFxDelayedAtten(soundAction[0], soundAction[1],
							# 					soundAction[2], self.position)
				else:
					pass # BigWorld.playFxDelayed(soundAction[0], soundAction[1], self.position)


	# Return the attacker's action to play based on this result from the server
	def ccActiveAction( self, res ):
		print "Attack result was", Avatar.hitResultStrings[res]

		if res & (1<<5):
			special = res & 7
			if special == 0:	# slay
				self.doFX( "CCActSlay" )
				return self.model.CCActSlay
			else:				# break
				self.ccBreaking = 1
				return self.model.CCActBreak

		prePart = "CCAct" + Avatar.stancePartDict[ self.stance ]

		defMove = res & 7
		actionName = prePart + Avatar.hitResultPartDict[ defMove ]

		self.doFX( actionName )

		return self.model.action( actionName )


	# Return the defender's action to play based on this result from the server
	def ccPassiveAction( self, res ):
		if res & (1<<5):
			special = res & 7
			if special == 0:	# slay
				self.causeOfDeath = Avatar.COD_SLAIN
				return None # self.model.CCPasSlay
				# We wait until we get told we're dead
			else:				# break
				return self.model.CCPasBreak

		prePart = "CCPas" + Avatar.stancePartDict[ self.stance ]

		defMove = res & 7
		actionName = prePart + Avatar.hitResultPartDict[ defMove ]

		self.doFX( actionName )

		return self.model.action( actionName )


	# Figure out an action based on the input stances (no longer used)
	def getCCAction( self, ownStance, othStance, ownTurn ):
		r = random.random()

		#print "getCCAction for", self.playerName, "ownStance", \
		#	ownStance, "othStance", othStance, "ownTurn", ownTurn

		if ownStance == 1:					# forward
			act = self.model.CCAttack3			# big attack
		elif ownStance == 0:				# backward
			if othStance != 0 and r < 0.5:
				act = self.model.CCParryL		# random parry
			else:
				act = self.model.CCParryR		# unless both defending
		else:								# neutral
			if othStance == 1:					# other forward
				if r < 0.5:							# random parry
					act = self.model.CCParryL
				else:
					act = self.model.CCParryR
			elif othStance == 0:				# other backward
				if r < 0.5:							# random attack
					act = self.model.CCAttack1
				else:
					act = self.model.CCAttack2
			else:								# other (both) neutral
				if ownTurn:							# our attack
					if r < 0.5:
						act = self.model.CCAttack1
					else:
						act = self.model.CCAttack2
				else:								# our defend
					if r < 0.5:
						act = self.model.CCParryL
					else:
						act = self.model.CCParryR

		return act


	stanceCapsDict = {
		STANCE_NEUTRAL: [8],
		STANCE_BACKWARD: [8,10],
		STANCE_FORWARD: [8,9],
		STANCE_LEFT: [8],
		STANCE_RIGHT: [8]
		}

	# The stance property has been set
	def set_stance( self, oldStance = None ):
		oldStance

		if self.mode != Mode.COMBAT_CLOSE: return

		#AUSTIN GDC - move all matchCaps into items
		#kept = filter( lambda c: c not in range(8,11), self.am.matchCaps )
		#
		#if self.healthPercent > 0:
		#	self.am.matchCaps = kept + Avatar.stanceCapsDict[ self.stance ]
		#else:	# We are dazed
		#	self.am.matchCaps = kept + [8,9,10]

	modelColours = (
		(1,1,1,1),	# white
		(1,1,0,1),	# yellow
		(1,0,1,1),	# magenta
		(0,1,1,1),	# cyan
		(1,0,0,1),	# red
		(0,1,0,1),	# green
		(0,0,1,1),	# blue
		(0,0,0,1),	# black
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1),	# grey
		(0.5,0.5,0.5,1)		# grey
	)		# other colours by request :)
	modelColourCount = 7

	# The colour property has been set
	def set_colour( self, oldColour = None ):
		pass
		#TO DO: implement colour changing
		#if self.colour == oldColour: return

		#try:		self.model.Legs.Colour = Avatar.modelColours[ self.colour & 15 ]
		#except:		pass
		#try:		self.model.Torso.Colour = Avatar.modelColours[ self.colour >> 4 ]
		#except:		pass

	DEAD_PENALTY = 10

	# Set dead state for all Avatars when dead.
	@IgnoreCallbackIfDestroyed
	def setDeadState( self, dyingAnimation = 1, delay = 0 ):
		if delay > 0:
			BigWorld.callback( 0.000001, partial( self.setDeadState, dyingAnimation, delay-1 ) )
			return
		self.inDeadState = 1
		self.waitingMode = -1

		self.disableAllTrackers()

		self.am.entityCollision = 0
		self.am.turnModelToEntity = 0

		self.setTargetCaps()

		# modeTarget is used to indicate how we died.
		# if silent take down, let the attack handle
		# the death animation
		if self.modeTarget == Avatar.COD_TAKEN_DOWN:
			return

		if self.model != None and self.model.inWorld:
			ntime = 0
			if self.causeOfDeath == Avatar.COD_SHOT:
				if dyingAnimation:
					da = self.model.Die
					da()
					ntime = da.duration-da.blendOutTime - 0.1
				de = self.model.Dead
				de( ntime )
				ntime += de.duration - de.blendOutTime
			else:	# COD_SLAIN
				if dyingAnimation:
					da = self.model.CCPasSlay
					da()
					ntime = da.duration-da.blendOutTime - 0.0001
				de = self.model.CCPasSlayDead
				de( ntime )
				ntime += de.duration - de.blendOutTime

			# align model to terrain
			self.filter = BigWorld.AvatarDropFilter()
			self.filter.alignToGround = True

			if hasattr( self, "am" ):
				self.am.useEntityPitchAndRoll = True
				self.am.turnModelToEntity = True
				self.am.bodyTwistSpeed = math.radians( 60.0 )

	# Becoming dead
	def enterDeadMode( self ):
		self.actionCommence()

		# Hide the model now if we are just entering the world,
		# and don't both with any of the teleportation effects
		# (which are highly likely to stuff up since they would be out of date)
		if self.worldTransition:
			self.setDeadState( 0 )	# no dying animation
			self.hideModel( True )
			return

		# Wait for causeOfDeath to be set... (twice through ticks since
		# enterDeadMode called from network input which is before callback
		# handling in game loop, and we need a frame to have been drawn)
		self.setDeadState( 1, 2 )

		# Set up the teleport out effect
		positionOffset = Vector3( 0.25, 0.00, 1.50 )
		cosYaw = math.cos( self.model.yaw )
		sinYaw = math.sin( self.model.yaw )
		positionOffset = Vector3( (
			positionOffset.x * cosYaw + positionOffset.z * sinYaw,
			positionOffset.y,
			positionOffset.z * cosYaw - positionOffset.x * sinYaw ) )
		ascendPoint = Vector3( self.position ) + positionOffset

		self.deathWarp = BigWorld.Model( "objects/models/fx/fx_deathwarp.model" )
		self.deathWarp.position = ascendPoint
		self.deathWarp.yaw = self.model.yaw

		BigWorld.callback( Avatar.DEAD_PENALTY + 3.0, self.beginTeleportation )
		FantasyDemo.firstPerson( False )
		FantasyDemo.resetCamera()

	def tryToTeleport( self, spaceName, pointName ):
		self.base.tryToTeleport( spaceName, pointName, self.spaceID )

	def teleportTo( self, spaceName, pointName ):
		TeleportSource.startTeleportation( spaceName, pointName )

	def addInfoMsg( self, msg ):
		FantasyDemo.addChatMsg( -1, msg )

	@IgnoreCallbackIfDestroyed
	def beginTeleportation( self ):
		if self.mode != Mode.DEAD:	return

		self.addModel( self.deathWarp )
		self.deathWarp.Go( 0, self.doTeleportation )

	@IgnoreCallbackIfDestroyed
	def doTeleportation( self ):
		if self.mode != Mode.DEAD:	return

		self.hideModel( True )
		self.deathWarp.Continue( 0, self.endTeleportation )

	@IgnoreCallbackIfDestroyed
	def endTeleportation( self ):
		if self.mode != Mode.DEAD:	return

		self.delModel( self.deathWarp )
		self.deathWarp = None
		self.am.matcherCoupled = 1


	def beginReincarnation( self ):
		if self.inWorld:
			dropPointPair = BigWorld.findDropPoint( self.spaceID, self.position )
			if dropPointPair == None:
				dropPoint = Vector3( self.position )
			else:
				dropPoint = dropPointPair[0]

			self.warp = BigWorld.Model( "objects/models/fx/fx_warp.model" )
			self.addModel( self.warp )
			self.warp.position = dropPoint
			self.warp.Go( 0, self.endReincarnation )

			# self.model.playSound( "spawnIn" )

			self.model.RespawnFall().RespawnLand()
			BigWorld.callback( self.model.RespawnFall.duration,
				self.respawnHitGround )

		BigWorld.callback( 0.25, partial( self.hideModel, False ) )

	@IgnoreCallbackIfDestroyed
	def respawnHitGround( self ):
		PSFX.attachRespawnMist( self.model )
		# TBD: Play sound here.


	def endReincarnation( self ):
		self.delModel( self.warp )
		self.warp = None

		self.actionComplete()


	# Helper function to disable all an Avatar's trackers
	def disableAllTrackers( self ):
		self.tracker.directionProvider = None

	# Helper function to enable specific tracker, called from guns.py
	def enableTracker( self, nodeInfo = None ):
		# this if test is temporary and should be removed
		# as soon as the beziel model get his skeleton fixed
		import Guard
		if isinstance(self, Guard.Guard):
			return

		if nodeInfo and not nodeInfo == self.tracker.nodeInfo:
			self.tracker.nodeInfo = nodeInfo
		if not self.tracker.directionProvider:
			self.tracker.directionProvider = self.entityDirProvider

	def unsetDeadState( self ):
		self.inDeadState = 0
		try:
			self.model.Dead.stop()
			self.model.CCPasSlayDead.stop()
		except AttributeError:
			pass
		self.causeOfDeath = Avatar.COD_SHOT
		self.am.entityCollision = 1
		self.am.matcherCoupled = 1
		self.filter = BigWorld.AvatarFilter()
		self.setTargetCaps()
		self.enableTracker()

	# Begin reincarnated
	def leaveDeadMode( self ):
		#Team.isDead( self.id, 0 )
		# remove the death warp (and interrupt its sequence) if it is still around
		if self.deathWarp != None:
			try:	self.delModel( self.deathWarp )
			except:	pass
			self.deathWarp = None

		# ok, now continue with the reincarnation
		self.unsetDeadState()

		if hasattr( self, "am" ):
			self.am.useEntityPitchAndRoll = False
			self.am.turnModelToEntity = False
			self.am.bodyTwistSpeed = math.radians( 360.0 )

		# reincarnate
		self.beginReincarnation()

	# Entering no mode
	def enterNoneMode( self ):
		pass

	# Leaving no mode
	def leaveNoneMode( self ):
		pass

	def onModelChangeUpdateMode( self ):
		# Called once the model has been set up correctly
		# go back into whatever mode we were in
		self.worldTransition = 1
		if( ModeTarget._isModeTargetReady( self ) ):
			self.enterMode( oldMode = Mode.NONE )
		else:
			ModeTarget._waitForModeTarget( self )
		self.worldTransition = 0

	# Going into any mode
	def enterMode( self, oldMode ):
		if self.mode == Mode.NONE:
			self.enterNoneMode()
			return

		assert not self._waitingForModeTarget

		if self.mode == Mode.SHONK:
			self.enterShonkMode()
		elif self.mode == Mode.HANDSHAKE:
			self.enterHandshakeMode()
		elif self.mode == Mode.PULLUP:
			self.enterPullUpMode();
		elif self.mode == Mode.PUSHUP:
			self.enterPushUpMode();
		elif self.mode == Mode.COMBAT_UNLOCKED:
			self.enterCombatMode(0, 0)
		elif self.mode == Mode.COMBAT_LOCKED:
			self.enterCombatMode(1, 0)
		elif self.mode == Mode.USING_ITEM:
			self.enterUsingItemMode()
		elif self.mode == Mode.CROUCH:
			self.enterCrouchMode()
		elif self.mode == Mode.SEATED:
			self.enterSeatedMode();
		elif self.mode == Mode.COMBAT_CLOSE:
			self.enterCloseCombatMode()
		elif self.mode == Mode.TRADE_PASSIVE:
			self.tradePassiveEnterMode()
		elif self.mode == Mode.TRADE_ACTIVE:
			self.tradeActiveEnterMode()
		elif self.mode == Mode.COMMERCE:
			self.commerceEnterMode()
		elif self.mode == Mode.DEAD:
			self.enterDeadMode()
		elif self.mode == Mode.WEB_SCREEN:
			pass
		else:
			print "Avatar::enterMode: In unknown mode ", self.mode

		if self.mode < Mode.ANSWERABLE:
			self.actionCommence()
			self.waitingMode = self.mode

	# Going out of any mode
	def cancelMode( self, oldMode ):
		if oldMode == Mode.NONE:
			self.leaveNoneMode()
			return

		if oldMode < Mode.ANSWERABLE:
			if self.waitingMode != -1:
				# wait for a bit to see if we're going to get a message with it
				BigWorld.callback( 0.5,
					partial( self.showModeCancellation, oldMode ) )
		elif oldMode == Mode.COMBAT_UNLOCKED:
			self.leaveCombatMode(0, 0)
		elif oldMode == Mode.COMBAT_LOCKED:
			self.leaveCombatMode(1, 0)
		elif oldMode == Mode.USING_ITEM:
			self.leaveUsingItemMode()
		elif oldMode == Mode.CROUCH:
			self.leaveCrouchMode()
		elif oldMode == Mode.SEATED:
			self.leaveSeatedMode()
		elif oldMode == Mode.COMBAT_CLOSE:
			self.leaveCloseCombatMode()
		elif oldMode == Mode.TRADE_PASSIVE:
			self.tradePassiveLeaveMode()
		elif oldMode == Mode.TRADE_ACTIVE:
			self.tradeActiveLeaveMode()
		elif oldMode == Mode.COMMERCE:
			self.commerceLeaveMode()
		elif oldMode == Mode.DEAD:
			self.leaveDeadMode()
		elif oldMode == Mode.WEB_SCREEN:
			pass
		else:
			print "Avatar::cancelMode: Out unknown mode ", oldMode

	# Play the cancellation animation
	@IgnoreCallbackIfDestroyed
	def showModeCancellation( self, mode ):
		if self.waitingMode == mode:
			if self.mode in Avatar.combativeModes:
				self.model.Disagree( 0, self.actionComplete )
			else:
				self.actionComplete()
			self.waitingMode = -1

	# Becoming a target
	def modeTargetFocus( self, other ):
		pass

	# Quitting as target
	def modeTargetBlur( self, player ):
		try:
			FantasyDemo.rds.fdgui.targetGui.source = None
		except AttributeError:
			pass

	# Some action has begun
	def actionCommence( self, combativeAction = 0 ):
		if not (self.rightHandItem and self.rightHandItem.canShoot):
			self.tracker.directionProvider = None

	# Some action is complete
	@IgnoreCallbackIfDestroyed
	def actionComplete( self ):
		#print "Avatar::actionComplete: Stopping action"
		if self.mode != Mode.SEATED and self.mode != Mode.DEAD:
			self.am.turnModelToEntity = 0
			self.am.matcherCoupled = 1
		if self.mode != Mode.DEAD:
			# tracker and entityDirProvider is only set once the model is loaded
			if hasattr( self, "tracker" ) and hasattr( self, "entityDirProvider" ):
				self.tracker.directionProvider = self.entityDirProvider
			try:
				self.tracker.directionProvider = self.entityDirProvider
			except AttributeError:
				pass


	# We got fragged!
	def fragged( self, shooterID ):
		e = BigWorld.entity( shooterID )
		if e != None:
			shname = e.name()
		else:
			shname = "An invisible monster"
		FantasyDemo.addChatMsg( self.id, shname + " fragged me!" )


	# Callback from tracking to get our name
	def name( self ):
		return self.playerName;


	def castSpell( self, targetid, hitLocn, materialKind ):
		try:
			self.currentSpell = self.rightHandItem.spell
		except:
			self.currentSpell = None

		if self.currentSpell != None:
			self.currentSpell.go( self, targetid, self.rightHandItem, hitLocn, materialKind )


	# Someone told us to shoot.
	def fireWeapon( self, shotid, lock ):
		if shotid == 0:
			lock = -1

		firePrep = None

		if lock == -1:
			fireBeg = self.model.CombatL0BeginFire
			fireExe = self.model.CombatL0ExecuteFire
			firePrep = self.model.CombatL0Blender
			movableShoot = 1
		else:
			fireBeg = self.model.CombatL1BeginFire
			fireExe = self.model.CombatL1ExecuteFire
			movableShoot = 1

		preparationTime = fireBeg.duration - fireBeg.blendOutTime
		# postTime = preparationTime + (fireExe.duration - fireExe.blendOutTime)

		if self.rightHandItem and self.rightHandItem.canShoot:
			self.rightHandItem.fire( self, preparationTime )

		fn = None
		if BigWorld.entities.has_key( shotid ):
			se = BigWorld.entity( shotid )
			if hasattr( se, "recoil" ):
				fn = partial( se.recoil, self, lock )

		if firePrep != None:
			firePrep.stop()
			self.enableTracker()
			# Commented out the following line when using ShootAir animation
			# as CombatL0 animation.
			#self.enableTracker( self.gunAimingNodeInfo )

		fireBeg( 0, fn )
		fireExe( -(preparationTime-0.01), partial( self.doneFire, firePrep ) )

		BigWorld.callback( 0.1, partial( self.model.playSound, "guns/fire" ) )

		return movableShoot


	# Called when we have finished a fire action.
	# If firePost is passed in, and we are still in combat
	# mode, then call the fn.
	def doneFire( self, firePost ):
		BigWorld.callback( 0.5, self.doneFire2 )

		if firePost != None and self.mode == Mode.COMBAT_UNLOCKED:
			self.enableTracker( self.headNodeInfo )
			# Commented out the following line when using ShootAir animation
			# as CombatL0 animation.
			#self.gunAimingTracker.trackNothing()
			firePost()

	# Completely finished with firing now.
	# Call actionComplete, and turn off the gun aiming tracker if
	# we lost our target in the meantime
	@IgnoreCallbackIfDestroyed
	def doneFire2( self ):
		self.actionComplete()

		# if we've lost our target since we began, we'd better
		# turn off the gun aiming tracker as targetBlur won't
		if self.mode != Mode.COMBAT_LOCKED:
			self.enableTracker( self.headNodeInfo );


	# We got shot at! (overriden by player)
	def recoil( self, shooter, lockAccuracy ):
		if lockAccuracy >= 1:
			# BigWorld.playFx( "players/grunts/hurt" , self.position )
			self.model.Recoil( -0.1 )
			self.recoilCommon( shooter, lockAccuracy )
		else:
			self.model.Recoil( -0.1 )
			self.recoilCommon( shooter, lockAccuracy )

	# Show the shield (not overriden by players)
	def recoilCommon( self, shooter, lockAccuracy ):
		dir = Vector3( shooter.position ) - Vector3( self.position )
		dir.normalise()

		if lockAccuracy >= 1:
			hitm = BigWorld.Model( "objects/models/fx/fx_shieldhit.model" )
		else:
			hitm = BigWorld.Model( "objects/models/fx/fx_shieldglance.model" )

		# BigWorld.playFx( "shield_hit", self.position )

		self.addModel( hitm )

		hitm.position = Vector3( self.position ) + dir.scale( 0.3 ) + Vector3(0,1.5,0)
		hitm.yaw = math.atan2( dir.x, dir.z )

		hitm.Go()
		BigWorld.callback( hitm.Go.duration, partial( self.delModel, hitm ) )

	# Shoot the target with a projectile
	def shootProjectile( self, target, projectileName ):
		# general settings
		srcoff = Vector3(0,1.5,0)
		dstoff = Vector3(0,1.2,0)
		projectile = BigWorld.Model(projectileName)
		self.addModel( projectile )
		projectile.position = self.position + srcoff
		mot = BigWorld.Homer()
		mot.target = target.model.matrix
		#mot.offset = dstoff
		mot.speed = 48
		mot.turnRate = 10

		# calculate the trip time based on the displacement
		disp = (Vector3(self.position)+srcoff) -	\
			(Vector3(target.model.position)+dstoff)
		sx = math.sqrt(disp.x*disp.x + disp.z*disp.z)
		sy = disp.y
		ay = -9.8
		U = mot.speed
		intercept = U*U*U*U - 2*U*U*sy*ay - ay*ay*sx*sx

		# if we can't make it, return now
		if intercept < 0:
			return

		tsq = (2.0/(ay*ay)) * (sy*ay - U*U + math.sqrt(intercept))
		t = math.sqrt(abs(tsq))
		mot.tripTime = t

		# rotate arrow to point in direction of initial velocity
		ux = sx/t
		uy = sy/t - 0.5*ay*t
		#print "ux is ", ux, " uy is ", uy
		projectile.rotate( math.atan2(uy,ux), (1,0,0) )
		projectile.yaw = math.atan2(disp.x,disp.z) + math.pi/2

		# and whack on the motor
		projectile.addMotor( mot )
		#self.addModel( projectile )

		# and whack on ye olde blur
		#particles.arrowBlur( projectile, mot.tripTime )
		PSFX.attachArrowTrace( projectile, None, mot.tripTime )

		# call us back when you get close enough
		mot.proximity = 0.5
		mot.proximityCallback = partial( self.clearProjectile, projectile )


	# Remove the specified projectile
	def clearProjectile( self, projectile ):
		self.delModel( projectile )


	# We're talking and the player heard us
	def chat( self, msg ):
		FantasyDemo.addChatMsg( self.id, msg )



	# We did a gesture and the player saw us
	def didGesture( self, actionID ):
		try:
			theAction = Avatar.gestureActions[actionID]
			if theAction.fn is not None:
				theAction.fn( self, theAction )
			else:
				self.model.action( theAction.actionName )( 0, self.actionComplete )
			if ( theAction.actionSound != "" ):
				pass # BigWorld.playFx( theAction.actionSound, self.position )
		except:
			self.actionComplete()


	# Server method telling us our shonk offer has been accepted
	def shonk( self, opponentID, oppAction, ownAction ):
		self.waitingMode = -1

		#print "Avatar::shonk: I performed %d, and Avatar %d performed %d." % (
		#	ownAction, opponentID, oppAction)

		# figure out what happened
		ownResult = ((3 + ownAction - oppAction) % 3)
		oppResult = ((3 + oppAction - ownAction) % 3)

		# figure out who our opponent is
		oppo = BigWorld.entity( opponentID )

		# Set camera to fixed position if the player is one of the Avatars
		# playing shonk.
		if self == BigWorld.player() or oppo == BigWorld.player():

			localCameraPos = Vector3( 1.25, 2.25, 0.75 )
			localCameraLookAt = Vector3( 0.00, 2.00, 0.75 )
			if self == BigWorld.player():
				target = self
			else:
				target = oppo

			( cameraPos, lookAtPos ) = self.calculateCameraView(
				target, localCameraPos, localCameraLookAt )

			FantasyDemo.setFixedCamera( cameraPos, lookAtPos )

		# start the game actions
		callback = CoordinatedActionPlayer( self, oppo,
			Avatar.shonkResultActionNames[ownResult],
			Avatar.shonkResultActionNames[oppResult] )

		selfEnd = partial( self.shonkComplete, ownAction, ownResult, callback )
		oppEnd = partial( oppo.shonkComplete, oppAction, oppResult, callback )

		self.model.action( Avatar.shonkPlayActionNames[ownAction] )( 0, selfEnd )
		oppo.model.action( Avatar.shonkPlayActionNames[oppAction] )( 0, oppEnd )

	def shonkComplete( self, action, result, callback ):
		if self == BigWorld.player():

			if result == 0:
				FantasyDemo.addChatMsg( -1, "It is a draw!" )
			else:
				if result == 1:
					FantasyDemo.addChatMsg( -1, "You win!" )
					if action == 0:
						FantasyDemo.addChatMsg( -1, "Paper wraps Rock" )
					elif action == 1:
						FantasyDemo.addChatMsg( -1, "Scissors cuts Paper" )
					else:
						FantasyDemo.addChatMsg( -1, "Rock blunts Scissors" )
				else:
					FantasyDemo.addChatMsg( -1, "You lose!" )
					if action == 0:
						FantasyDemo.addChatMsg( -1, "Scissors cuts Paper" )
					elif action == 1:
						FantasyDemo.addChatMsg( -1, "Rock blunts Scissors" )
					else:
						FantasyDemo.addChatMsg( -1, "Paper wraps Rock" )

			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		callback()


	# Calculates the position and lookAtPos for the camera given a relative
	# camera and lookAt position to an Entity.
	#
	# Returns a pair with the first element being the world camera position;
	# and the second element being the world camera lookAt position.
	def calculateCameraView( self, entity, cameraPos, lookAtPos ):
		sinYaw = math.sin( entity.model.yaw )
		cosYaw = math.cos( entity.model.yaw )

		worldPos = Vector3( entity.position ) + Vector3( (
			cameraPos.x * cosYaw + cameraPos.z * sinYaw,
			cameraPos.y,
			cameraPos.z * cosYaw - cameraPos.x * sinYaw ) )

		worldLookAt = Vector3( entity.position ) + Vector3( (
			lookAtPos.x * cosYaw + lookAtPos.z * sinYaw,
			lookAtPos.y,
			lookAtPos.z * cosYaw - lookAtPos.x * sinYaw ) )

		return ( worldPos, worldLookAt )

	# -------------------------------------------------------------------------
	# Section: Handshake
	# -------------------------------------------------------------------------

	# Server method telling us our handshake offer has been accepted
	def handshake( self, partnerID ):
		self.waitingMode = -1

		partner = BigWorld.entity( partnerID )
		if self.mode == Mode.HANDSHAKE:
			print "Shaking hands with " + partner.name()
		else:
			print "Avatar.handshake() called from unknown mode"
			return

		# These seem to make it look worse.
		# set our yaw to what the other client must think it is
		# given the position it's gone to.
		#self.am.turnModelToEntity = 0
		#print "Our yaw set to: ", partner.model.Shake_B_Accept.seek[3]
		#self.model.yaw = partner.model.Shake_B_Accept.seek[3]
		# set our partners yaw to what it should be explicitly
		#partner.am.turnModelToEntity = 0
		#print "Our partner's yaw set to: ", self.model.Shake_B_Accept.seekInv[3]
		#partner.model.yaw = self.model.Shake_B_Accept.seekInv[3]

		# Set camera to fixed position if the player is doing the handshake.
		if self == BigWorld.player() or partner == BigWorld.player():

			localCameraPos = Vector3( 1.25, 2.25, 0.75 )
			localCameraLookAt = Vector3( 0.00, 2.00, 0.75 )
			if self == BigWorld.player():
				target = self
			else:
				target = partner

			( cameraPos, lookAtPos ) = self.calculateCameraView(
				target, localCameraPos, localCameraLookAt )

			BigWorld.target.clear()
			FantasyDemo.setFixedCamera( cameraPos, lookAtPos )

		if partner != BigWorld.player():
			partner.actionCommence()

		self.disableAllTrackers()
		partner.disableAllTrackers()

		sbe = partner.model.Shake_B_Extend
		sbe().Shake_B_Accept( 0, partner.handshakeComplete )
		self.model.Shake_A_Accept( sbe.duration, self.handshakeComplete )


	def handshakeComplete( self ):
		if self == BigWorld.player():
			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		self.actionComplete()


	# Server method telling us our pull up offer has been accepted
	def pullUp( self, partnerID ):
		self.waitingMode = -1

		partner = BigWorld.entity( partnerID )
		print "Avatar::pullUp: Pulling up ", partner.name()

		partner.am.matcherCoupled = 0
		# commented out because it turns the model away from the wall if the player has moved the mouse
		#partner.model.yaw = partner.yaw

		# At this point we have a choice. We can either leave our partner's
		#  pose set to what it thinks it should be, and play the animation
		#  with the possibility of hands not exactly meeting up, or we can
		#  set it to what we know looks good, and experience a pop in its
		#  pose when we recouple the action matcher. Since the hands usually
		#  match up reasonably well, I'm leaving it at what it thinks is
		#  right for now. These differences arise primary due to the
		#  resolution of 'yaw', which is not great. Another possibility is
		#  that higher resolution yaws could be passed up with the state
		#  change and with this message.				John 7/6/01 {P^/
		#pose = self.model.PullUpActiveBegin.seek
		#partner.model.position = pose[0:3]
		#partner.model.yaw = pose[3]


		# Set camera to fixed position if the player is involved.
		if self == BigWorld.player() or partner == BigWorld.player():
			localCameraPos = Vector3( -1.50, 2.00, 2.50 )
			localCameraLookAt = Vector3( 0.00, -2.50, 0.50 )

			( cameraPos, lookAtPos ) = self.calculateCameraView(
				self, localCameraPos, localCameraLookAt )

			#BigWorld.fixedCameraPos( cameraPos.x, cameraPos.y, cameraPos.z )
			#BigWorld.fixedCameraLookAt( lookAtPos.x, lookAtPos.y, lookAtPos.z )
			#FantasyDemo.cameraType( FantasyDemo.rds.FIXED_CAMERA )

		if partner == BigWorld.player():
			partner.am.inheritOnRecouple = 0
			partner.physics.teleport( partner.model.PullUpPassiveImpact.impact[0:3] )
		else:
			partner.actionCommence()	# player has already commenced

		pupb = partner.model.PullUpPassiveBegin;
		pupb().PullUpPassiveAccept( 0, partner.pullUpEndPartner ).Idle()

		aftertime = pupb.duration - pupb.blendOutTime - 0.001
		self.model.PullUpActiveAccept( aftertime, self.pullUpEnd )

	def pullUpEnd( self ):
		if self == BigWorld.player():
			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		self.model.Idle.stop()
		self.actionComplete()

	def pullUpEndPartner( self ):
		if self == BigWorld.player():
			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		self.model.Idle.stop()
		self.actionComplete()

	# Server method telling us our push up offer has been accepted
	def pushUp( self, partnerID ):
		self.waitingMode = -1

		partner = BigWorld.entity( partnerID )
		print "Avatar::pushUp: Pushing up ", partner.name()


		partner.am.matcherCoupled = 0
		# commented out because it turns the model away from the wall if the player has moved the mouse
		#partner.model.yaw = partner.yaw

		# we have to move up 5cm here because the two animations together
		# don't _quite_ provide enough lift for us :)
		pmp = partner.model.position
		partner.model.position = pmp[0], pmp[1] + 0.05, pmp[2]

		if self == BigWorld.player(): sname = "Player"
		else: sname = "Initer"
		#~ print sname, " entity position: " , self.position, ", yaw: ", self.yaw
		#~ print sname, " model  position: " , self.model.position, ", yaw: ", self.model.yaw
		if partner == BigWorld.player(): sname = "Player"
		else: sname = "Partnr"
		#~ print sname, " entity position: " , partner.position, ", yaw: ", partner.yaw
		#~ print sname, " model  position: " , partner.model.position, ", yaw: ", partner.model.yaw


		# Set camera to fixed position if the player is involved.
		if self == BigWorld.player() or partner == BigWorld.player():
			localCameraPos = Vector3( -2, 8, 1.5 )
			localCameraLookAt = Vector3( 1, -4.5, 2 )

			( cameraPos, lookAtPos ) = self.calculateCameraView(
				self, localCameraPos, localCameraLookAt )

			#BigWorld.fixedCameraPos( cameraPos.x, cameraPos.y, cameraPos.z )
			#BigWorld.fixedCameraLookAt( lookAtPos.x, lookAtPos.y, lookAtPos.z )
			#FantasyDemo.cameraType( FantasyDemo.rds.FIXED_CAMERA )

		if partner == BigWorld.player():
			#partner.am.inheritOnRecouple = 0

			dir = Vector3( math.sin(partner.yaw), 0, math.cos(partner.yaw) )
			#dist = Vector3(partner.model.PushUpPassiveAccept.displacement) + \
			#	Vector3(partner.model.PushUpPassiveComplete.displacement);
			dist = Vector3( 0, 5.1, 1.35 )		# don't ask :)
			newPos = Vector3( partner.position ) + dir.scale( dist.z )
			newPos.y = newPos.y + dist.y
			partner.physics.teleport( newPos )
			# this isn't perfect, but it will do :)

			# or try adding impacts... hmmm...
		else:
			partner.actionCommence()


		self.model.PushUpActiveAccept( 0, self.pushUpEnd ).Idle()
		partner.model.PushUpPassiveAccept().PushUpPassiveComplete(
			0, partner.pushUpEndPartner ).Idle()

	def pushUpEndPartner( self ):
		if self == BigWorld.player():
			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		self.model.Idle.stop()
		self.actionComplete()

	def pushUpEnd( self ):
		if self == BigWorld.player():
			FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
		self.model.Idle.stop()
		self.actionComplete()


	# The player wants to use us
	def use( self ):
		# See if we are in a mode then
		player = BigWorld.player()
		if self.mode == Mode.SHONK:
			# should put up a menu (stays until focus lost?) asking how
			# the player wants to reply... hmmm need to think about this
			player.shonkKey( random.randrange( 3 ) )
		elif self.mode == Mode.HANDSHAKE:
			player.handshakeKey()
		elif self.mode == Mode.PULLUP:
			player.pullUpKey()
		elif self.mode == Mode.PUSHUP:
			player.pushUpKey()
		elif self.mode == Mode.JOIN_GROUP:
			player.answerJoinGroup( self )
		elif self.mode in ( Mode.THROW, Mode.THROW_CROUCHED ):
			player.catchKey( self )
		elif self.mode in ( Mode.CATCH, Mode.CATCH_CROUCHED ):
			player.throwKey( self )
		elif self.mode == Mode.TRADE_PASSIVE:
			player.onTradeKey()

	# Seperated from the above so the right trigger doesn't heal other players
	def useFromWhiteButton( self ):
		if isinstance(player.rightHandItem, Reviver) or isinstance(player.rightHandItem, Medipack):
			player.rightHandItem.use( player, self )


	# Some class-static data definitions

	simpleModelName = "characters/avatars/base/base.model"

	shonkPlayActionNames = [ "ShonkPaper", "ShonkScissors", "ShonkRock" ]
	shonkResultActionNames = [ "Shrug", "ShonkWin", "ShonkLose" ]

	#
	#---------------------------------------------------------------------------


	gestureActions = {
		0 :GestureAction("ShooAway",		0,	1),
		1 :GestureAction("OneHandedWave",	1,	0),
		2 :GestureAction("TwoHandedWave",	1,	0),
		3 :GestureAction("Cry",				0,	0),
		4 :GestureAction("Shrug",			1,	1),
		5 :GestureAction("ShonkWin",		0,	1),
		6 :GestureAction("ShonkLose",		0,	0),
		7 :GestureAction("ShonkPaper",		0,	0),
		8 :GestureAction("ShonkScissors",	0,	0),
		9 :GestureAction("ShonkRock",		0,	0),
		10:GestureAction("FoldArms",		0,	0),
		11:GestureAction("CatchBreath",		0,	0),
		12:GestureAction("HeavyBreathing",	0,	0),
		13:GestureAction("WatchItWarning",	1,	0),
		14:GestureAction("WhoMe",			0,	0),
		15:GestureAction("StopWarning",		1,	1),
		16:GestureAction("Laugh",			1,	1),
		17:GestureAction("HeavyLaugh",		0,	0),
		18:GestureAction("BeckonTaunt",		0,	1),
		19:GestureAction("Agree",			0,	1),
		20:GestureAction("Disagree",		0,	1),
		21:GestureAction("SubtleBeckon",	1,	1),
		22:GestureAction("FranticBeckon",	0,	1),
		23:GestureAction("KissMyAssTaunt",	0,	0),
		24:GestureAction("Point",			0,	1),
		25:GestureAction("PointToSelf",		0,	0),
		26:GestureAction("PointWarning",	0,	1),
		27:GestureAction("Ponder",			0,	0),
		28:GestureAction("RudeGesture",		0,	0),
		29:GestureAction("GiveUp",			0,	1),
		30:GestureAction("FaceRoar",		1,	1, "orc_roar"),
		31:GestureAction("RaiseSword",		0,	1),
		32:GestureAction("HeadStretch",	0,	0),
		33:GestureAction("Troller",	0,	0),
		34:GestureAction("TeamJoinAccept", 0, 1),
		35:GestureAction("Jump",	0,	1),
		36:GestureAction("PressPalm",	0,	0),
		37:GestureAction("GoGoGo",	0,	0),
		38:GestureAction("GetDown",	0,	0),
		39:GestureAction("MoveUp",	0,	0),
		40:GestureAction("Salute",	0,	0),
		41:GestureAction("Shhhh",	0,	0),
		42:GestureAction("PointLeft",	0,	0),
		43:GestureAction("PointRight",	0,	0),
		44:GestureAction("Fat",	1,	1),
		45:GestureAction("Skinny",	1,	1),
		46:GestureAction("SwingSword",	1,	1, "", swordSwingGesture),
	}

	# This sets the target focal node for this entity,
	#  for either normal (-1), loose combat (0),
	#  tight combat (1), or take down (2) focus
	def setFocalNode( self, tight = None ):
		if tight == None:
			tight = self.tightFocus
		else:
			self.tightFocus = tight

		if tight == -1:
			self.focalMatrix.a = self.model.node( "biped Head" )
		elif tight == 0:
			self.focalMatrix.a = self.model.node( "biped Spine1" )
		elif tight == 1:
			self.focalMatrix.a = self.model.node( "biped Head" )
		elif tight == 2:
			self.focalMatrix.a = self.model.node( "biped Head" )
		else:
			self.focalMatrix.a = self.model.node( "biped Head" )

	def notLoggedOn( self, playerName ):
		FantasyDemo.addChatMsg( -1, playerName + " is not logged on" )

	# -------------------------------------------------------------------------
	# Friends list
	# -------------------------------------------------------------------------

	# Helper method to get the target player name if friendName is empty
	def getTargetForFriendlyAction( self, friendName ):
		if len( friendName ):
			return friendName

		target = BigWorld.target()
		if target != None and isinstance(target, Avatar):
			return target.playerName

		else:
			FantasyDemo.addChatMsg( -1, \
				"Please specify friend name or have friend targetted." )
			return ""


	# Helper method to find the index of friendName in self.friendsList
	def getFriendIdxByName( self, friendName ):
		for i in range( len( self.friendsList ) ):
			if self.friendsList[i][0] == friendName:
				return i
		return -1

	def newFriendsList( self, friendsList ):
		self.friendsList = [ ( x, False ) for x in friendsList ]

	def setFriendStatus( self, idx, isOnline ):
		friend = self.friendsList[idx]
		self.friendsList[idx] = ( friend[0], isOnline )
		self.onFriendPresence( friend[0], isOnline )


	def onFriendPresence( self, friend, isOnline ):
		if friend.find( "@" ) != -1:
			friend += "[IM]"

		if isOnline:
			FantasyDemo.addChatMsg(	-1, friend + " is online.",
					FDGUI.TEXT_COLOUR_ONLINE )
		else:
			FantasyDemo.addChatMsg(	-1, friend + " has logged off.",
					FDGUI.TEXT_COLOUR_OFFLINE )


	def addFriend( self, friendName ):
		targetFriendName = self.getTargetForFriendlyAction( friendName )

		if not len( targetFriendName ):
			return

		idx = self.getFriendIdxByName( targetFriendName )
		if idx < 0:
			self.base.addFriend( targetFriendName )
		else:
			FantasyDemo.addChatMsg( -1, targetFriendName +
				" is already your friend." )


	def onAddedFriend( self, friendName, online ):
		self.friendsList.append( ( friendName, online ) )
		FantasyDemo.addChatMsg( -1, friendName + " is your new friend." )


	def delFriend( self, friendName ):
		targetFriendName = self.getTargetForFriendlyAction(friendName)

		if len(targetFriendName) > 0:
			idx = self.getFriendIdxByName(targetFriendName)

			if idx >= 0:
				del self.friendsList[idx]
				self.base.delFriend(idx)
				FantasyDemo.addChatMsg( -1, targetFriendName +
					" is no longer your friend." )

			else:
				FantasyDemo.addChatMsg( -1, targetFriendName +
					" is not currently one of your friends." )


	def infoFriend( self, friendName ):
		targetFriendName = self.getTargetForFriendlyAction(friendName)

		if len(targetFriendName) > 0:
			idx = self.getFriendIdxByName(targetFriendName)

			if idx >= 0:
				self.base.getFriendInfo(idx)
			else:
				FantasyDemo.addChatMsg( -1, targetFriendName +
					" is not one of your friends." )


	def onRcvFriendInfo( self, friendName, info ):
		FantasyDemo.addChatMsg( -1, info )


	def displayFriendsList( self, onlineFriends, offlineFriends, friendsType ):

		totalFriends = len( onlineFriends ) + len( offlineFriends )

		msg = "%d of %d %s friends online:" % \
					( len( onlineFriends ), totalFriends, friendsType )
		FantasyDemo.addChatMsg( -1, msg )

		if len( onlineFriends ):
			msg = "   online: " + ", ".join( onlineFriends )
			FantasyDemo.addChatMsg( -1, msg, FDGUI.TEXT_COLOUR_ONLINE )

		if len( offlineFriends ):
			msg = "   offline: " + ", ".join( offlineFriends )
			FantasyDemo.addChatMsg( -1, msg, FDGUI.TEXT_COLOUR_OFFLINE )


	def listFriends( self ):

		# In-game friends
		onlineFriends = [ name for (name, online) in self.friendsList
							if online ]
		offlineFriends = [ name for (name, online) in self.friendsList
							if not online ]

		self.displayFriendsList( onlineFriends, offlineFriends, "in-game" )

		# Instant Messaging friends
		friendsDict = self.roster.friendsByStatus()

		offlineFriends = friendsDict.get( "unavailable", [] )

		# Combine any friends that aren't offline into the online group
		onlineFriends = []
		for presence in friendsDict.keys():
			if presence == "unavailable":
				continue

			onlineFriends.extend( friendsDict[ presence ] )

		self.displayFriendsList( onlineFriends, offlineFriends, "IM" )


	def msgFriend( self, friendName, message ):
		targetFriendName = self.getTargetForFriendlyAction(friendName)

		if len(targetFriendName) > 0:
			idx = self.getFriendIdxByName(targetFriendName)
			if idx >= 0:
				self.base.sendMessageToFriend( idx, message )
			else:
				FantasyDemo.addChatMsg( -1, targetFriendName +
					" is not one of your friends." )

	def onReceiveMessageFromAdmirer( self, admirerName, message ):
		FantasyDemo.addChatMsg( -1, admirerName + " says to you: " + message, 2 )


	# We received a message
	def showMessage( self, type, source, msg ):
		FantasyDemo.addChatMsg( -1,
			( "Debug", "Tell", "Group", "Info" )[type] + " - " + source + ": " + msg )


	# Dummy methods used in bots testing
	def loadGenMeth1( strArg ): pass
	def loadGenMeth2( intArg, strArg ): pass
	def loadGenMeth3( floatArg1, floatArg2, floatArg3 ): pass
	def loadGenMeth4( arrayArg ): pass

	def entitySummoned( self, id, typeName ):
		if id != 0:
			FantasyDemo.addChatMsg( -1, "Summoned " + typeName + " id:" + str( id ) )
		else:
			FantasyDemo.addChatMsg( -1, "Failed to summon entity of type: " + typeName )


	def findOwnCellBounds( self ):
		p = self.position
		i = 0
		while i < len(self.cellBounds):
			blX = self.cellBounds[i+0]
			blY = self.cellBounds[i+1]
			trX = self.cellBounds[i+2]
			trY = self.cellBounds[i+3]
			i += 4

			if blX <= p.x and p.x <= trX:
				if blY <= p.z and p.z <= trY:
					return (blX,blY,trX,trY)
		return None


	def set_cellBounds( self, oldCellBounds ):
		try:
			FantasyDemo.rds.fdgui.minimap.m.cellBounds = self.cellBounds
		except:
			#python cellBounds attribute may be compiled out
			pass

		self.setupCellBoundsModel()


	def setupCellBoundsModel( self ):
		ownCellBounds = self.findOwnCellBounds()

		if self.cellBoundsModel is None:
			return

		if not self.showCellBoundsModel or ownCellBounds is None:
			self.cellBoundsModel.visible = False
			return

		# cant handle float max so clamp to smaller value
		clampedCellBounds = []
		clampedCellBounds.append( min( 1000.0 + self.position[0], max( -1000.0 + self.position[0], ownCellBounds[0] ) ) )
		clampedCellBounds.append( min( 1000.0 + self.position[2], max( -1000.0 + self.position[2], ownCellBounds[1] ) ) )
		clampedCellBounds.append( min( 1000.0 + self.position[0], max( -1000.0 + self.position[0], ownCellBounds[2] ) ) )
		clampedCellBounds.append( min( 1000.0 + self.position[2], max( -1000.0 + self.position[2], ownCellBounds[3] ) ) )

		sizeX = clampedCellBounds[2] - clampedCellBounds[0]
		sizeY = 2000.0
		sizeZ = clampedCellBounds[3] - clampedCellBounds[1]

		centerX = ( clampedCellBounds[2] + clampedCellBounds[0] ) / 2
		centerY = 0
		centerZ = ( clampedCellBounds[3] + clampedCellBounds[1] ) / 2

		self.cellBoundsModel.scale = ( sizeX, sizeY, sizeZ )
		self.cellBoundsModel.position = ( centerX, centerY, centerZ )
		self.cellBoundsModel.visible = True


	def inWebScreenMode( self ):
		return self.mode == Mode.WEB_SCREEN

# End of class Avatar

# static function to parse folders and add files to the preload list
def addFolderToPreloads( folder, masks, list ):
	if ".svn" in folder:
		return

	section = ResMgr.root[ folder ]
	if section == None:
		return

	for key in section.keys():
		done = 0
		for mask in masks:
			if key.endswith( mask ):
				list.append( folder + '/' + key )
				done = 1
#				print "Adding to preloads: " + folder + '/' + key
		if not done:
			addFolderToPreloads( folder + '/' + key, masks, list )


# static function to append models to preload onto 'list'
def preload( list ):
	preLoadList = []

	preLoadList.append( "scripts/" )

	# Manually add all lens flare bitmaps.  At the very least we should extend
	# the prereqs / preload system to know about mfm files.

	# BigWorld ones
	#preLoadList.append( "system/maps/fx_flare_glow.dds" )
	#preLoadList.append( "system/maps/fx_lens_sec.bmp" )

	# FantasyDemo ones
	#preLoadList.append( "maps/fx/fx_flare_glow.bmp" )
	#preLoadList.append( "maps/fx/flare_glow.bmp" )
	#preLoadList.append( "maps/fx/flare_halo.bmp" )
	#preLoadList.append( "maps/fx/flare_rainbow.bmp" )
	#preLoadList.append( "maps/fx/lens_sec.bmp" )
	#preLoadList.append( "maps/fx/mask_flare.bmp" )
	#preLoadList.append( "maps/fx/flare_trees.bmp" )
	preLoadList.append( "maps/fx/fx_swish.bmp" )

	# Add game metadata XML files to preload list.  Note these should not
	# be preloaded, but instead statically bound as python data
	addFolderToPreloads( "sfx", "*.xml", preLoadList )
	addFolderToPreloads( "system/post_processing/chains", "*.ppchain", preLoadList )
	addFolderToPreloads( "particles", "*.xml", preLoadList )
	addFolderToPreloads( "sets/desert/particles", "*.xml", preLoadList )
	addFolderToPreloads( "scripts/data", "*.xml", preLoadList )
	addFolderToPreloads( "environments/fx", "*.xml", preLoadList )

	# Add lens flare XML files to preload list.
	addFolderToPreloads( "materials/fx", "*.mfm", preLoadList )
	addFolderToPreloads( "environments/fx", "*.xml", preLoadList )
	addFolderToPreloads( "system/materials/", "*.mfm", preLoadList )


	# Add fx files
	#addFolderToPreloads( "shaders/std_effects", "*.fx", preLoadList )


	list += preLoadList
	#print list


	#
	# PlayerAvatar C++ Interface Note:
	# The identifier 'physics' refers to the C++ Python Object Physics. It is a
	# special variable as it is initially set to a specified value to initialise
	# it to a particular physics model.
	#
	# eg. self.physics = BigWorld.STANDARD_PHYSICS will initialise the physics
	# object for the PlayerAvatar instance.
	#
	# Any subsequent call can then treat 'physics' as a structure with data
	# members that control physics behaviour.
	#
	# eg. self.physics.collide = true will turn on collision detection for the
	# PlayerAvatar.
	#
	# The list of physics data members are:
	#     velocity, (X,Y,Z) movement velocity
	#     velocityMouse, Direction|MouseX|MouseY indicating how the mouse
	#         behave velocity.
	#     angularMouse, Direction|MouseX|MouseY indicating how the mouse
	#         affects direction.
	#     angular, a double value indicating current angular velocity.
	#     nudge, the (X,Y,Z) movement value to be moved this frame.
	#     turn, the double value indicating turned amount this frame.
	#     fall, a true or false value indicating if gravity should affect it.
	#     collide, a true or false value indicating if collision detection is
	#              turned on or off for this Avatar.
	#

class PlayerAvatar( Avatar, BWKeyBindings.BWActionHandler ):
	"TODO: Document"

	DROPPICK_TIMEOUT = 3


	def onAddNote( self, id ):
		if id == 0:
			FantasyDemo.addChatMsg( -1, "Note addition failed" )
		else:
			FantasyDemo.addChatMsg( -1, "Added Note: %d" % id )


	def onGetNotes( self, noteList ):
		if len( noteList ) > 0:
			# Note: Chat messages are currently being forced from unicode
			# to a utf-8 encoded string to be sent to the server and saved
			# into the DB. The corresponding encoding is in ConsoleCommands.py
			for note in noteList:
				FantasyDemo.addChatMsg( -1, "Found note: %d - %s" % ( note[ "id" ], note[ "description" ].decode( "utf8" ) ) )
		else:
			FantasyDemo.addChatMsg( -1, "No Notes Found" )


	#---------------------------------
	# XMPP Example
	#---------------------------------

	def onXmppRegisterWithTransport( self, transport ):
		# Because the property is BASE_AND_CLIENT, it will only be propagated
		# on entity creation, so we'll add a dummy record now for convenience.
		self.xmppTransportDetails.append(
			{ "transport": transport, "username": "", "password": "" } )

		registerMsg = "Successfully registered %s account with XMPP gateway" % \
						transport
		FantasyDemo.addChatMsg( -1, registerMsg, FDGUI.TEXT_COLOUR_SYSTEM )


	def onXmppDeregisterWithTransport( self, transport ):
		for transportDetails in self.xmppTransportDetails:
			if transportDetails[ "transport" ] == transport:
				self.xmppTransportDetails.remove( transportDetails )

		deregisterMsg = "Successfully deregistered %s account with XMPP " \
						"gateway" % transport
		FantasyDemo.addChatMsg( -1, deregisterMsg, FDGUI.TEXT_COLOUR_SYSTEM )


	# Callback methods from the XMPP interface on the Base
	def onXmppMessage( self, friendID, transport, message ):
		sender = friendID.split( "/", 1 )[0] + "[IM %s]" % transport
		publishMessage = sender + ": " + message
		FantasyDemo.addChatMsg( -1, publishMessage, FDGUI.TEXT_COLOUR_OTHER_SAY )


	def onXmppRoster( self, roster ):
		# The visitor that will be used to notify us of events
		visitor = XMPP.AvatarRosterVisitor()

		# Update our XMPPRoster
		self.roster.update( roster, visitor )


	def onXmppRosterItemAdd( self, friendID, transport ):
		# The visitor that will be used to notify us of events
		visitor = XMPP.AvatarRosterVisitor()

		# Update our XMPPRoster
		self.roster.add( friendID, transport, rosterVisitor = visitor )


	def onXmppRosterItemDelete( self, friendID, transport ):
		# The visitor that will be used to notify us of events
		visitor = XMPP.AvatarRosterVisitor()

		# Update our XMPPRoster
		self.roster.remove( friendID, transport, rosterVisitor = visitor )


	def onXmppPresence( self, friendID, transport, presence ):
		# The visitor that will be used to notify us of events
		visitor = XMPP.AvatarRosterVisitor()

		if presence == "subscribe":

			# We don't have to add them to our list again.
			if self.roster.isFriend( friendID, transport ):
				return

			# They have subscribed to us, so lets ask them to be our friend too.
			self.base.xmppAddFriend( friendID, transport )

		elif presence == "unsubscribe":
# TODO: implement this. we don't want to see presence notifications about
#       friends we are in the middle of deleting.
			self.roster.addPendingFriendRemoval( friendID, transport )

			# Auto-remove anybody from our own roster if they have removed us
			self.base.xmppDelFriend( friendID, transport )

		elif presence == "error":
			# This will most likely be as a result of an invalid transport
			# registration. This message can be changed later if other
			# cases are discovered.
			errorMsg = "Failed to add friend %s. Your account credentials " \
				"for the %s transport may be incorrect." % \
					(friendID, transport)

			FantasyDemo.addChatMsg( -1, errorMsg, FDGUI.TEXT_COLOUR_SYSTEM )

			# Now make sure the roster item is removed for that user.
			self.base.xmppDelFriend( friendID, transport )

		else:

			# Update our XMPPRoster
			self.roster.updatePresence( friendID, transport, presence, visitor )



	def onXmppError( self, message ):
		FantasyDemo.addChatMsg( -1, message )


	def onBecomePlayer( self ):
		print "PlayerAvatar::onBecomePlayer"
		if self.inWorld:
			self.onEnterWorld( None, 0 )


	def onEnterWorld( self, prereqs, initial=1 ):
		print "PlayerAvatar::onEnterWorld: begin"

		FantasyDemo.cameraType(0)

		self._initInventory()
		self._initInventoryGUI()

		if initial:
			self.initialPosition = self.position
			Avatar.onEnterWorld( self, prereqs )

		# we're using a filter tailor-made for us
		self.filter = BigWorld.PlayerAvatarFilter()
		self.am.entityCollision = 1
		self.am.collisionRooted = 0

		self._initInternalData()

		FantasyDemo.cameraType(0)

		self.setUpMovementSpeedsFromModel()

		self.initialPos = self.position
		self.pickingUpItem = False
		self.allowFPSModeToggle = True

		# physics setup
		self.initPhysics()
		self.am.velocityProvider = self.physics.uncorrectedVelocity

		# spawnPoint must be called after self.initialPos is set.
		self.physics.teleport( self.spawnPoint() )

		# Data associated with Movement
		self._initMovementData()

		# Targetting stuff
		BigWorld.target.exclude = self
		self.enableMouseTargetting()
		self.targetCaps = [ Caps.CAP_NEVER ]
		BigWorld.target.caps( Caps.CAP_NONE )
		self.minAimScore = 0.0
		self.maxAimScore = 0.99
		self.minimapColour = (64,64,255,255)

		self._initCombatData()
		self._initTradeData()

		FantasyDemo.rds.fdgui.onPlayerAvatarEnterWorld( self )
		FantasyDemo.addChangeEnvironmentsListener( self.onChangeEnvironments )
		self._initHealth()

		self.inventoryWindow.updateInventory(
				self.inventoryItems,
				self.inventoryMgr.availableGoldPieces() )

		#self._initInventory()

		self.set_rightHand( itemChangeAnim = 0 )	# set target caps
		self.set_shoulder()
		self.set_rightHip()
		self.set_leftHip()

		self._initWoWMode()

		self.moveForwardKeys = []
		self.moveBackwardKeys = []
		self.moveLeftKeys = []
		self.moveRightKeys = []

		self.guiMode( 0 )
		self.oldZoomLevel = 0
		FDGUI.Cursor.showCursor( True ) # Non-forced
		FantasyDemo.rds.keyBindings.addHandler( self )

		# and do stuff we can do every time scripts are reloaded
		self.reload()

		self.minimapIcon = GUI.load("gui/minimap_icon.gui")
		self.minimapHandle = FantasyDemo.rds.fdgui.minimap.m.add(self.matrix, self.minimapIcon)

		self.showCellBoundsModel = False
		self.cell.enableCellBoundsCapture( True )
		self.cellBoundsModel = BigWorld.Model( "sets/global/checker.model" )
		self.cellBoundsModel.visible = False
		self.addModel( self.cellBoundsModel )

		print "PlayerAvatar::onEnterWorld: end"


	def enableMouseTargetting( self ):
		if not hasattr( self, "mouseTargettingMatrix" ):
			self.mouseTargettingMatrix = BigWorld.MouseTargettingMatrix()
		BigWorld.target.source = self.mouseTargettingMatrix
		BigWorld.target.selectionFovDegrees = 5.0
		BigWorld.target.deselectionFovDegrees = 8.0


	def disableMouseTargetting( self ):
		if not hasattr( self, "playerTargettingMatrix" ):
			self.playerTargettingMatrix = BigWorld.ThirdPersonTargettingMatrix( BigWorld.PlayerMatrix() )
		BigWorld.target.source = self.playerTargettingMatrix
		BigWorld.target.selectionFovDegrees = 15.0
		BigWorld.target.deselectionFovDegrees = 20.0


	def _initInternalData( self ):
		self.doingAction = 0
		self.firstPerson = 0
		self.freeCamera = 0
		self.modelPreset = 0


	def _initMovementData( self ):
		self.forwardMagnitude	= 0.0
		self.upwardMagnitude	   = 0.0
		self.rightwardMagnitude	= 0.0
		self.speedMultiplier    = 1.0
		self.isDashing		 	   = 0
		self.isRunning			   = 1
		self.flying             = 0


	def _initCombatData( self ):
		self.toldServerID = 0
		self.NCTOutstanding = 0
		self.doingMovableAction = 0
		self.waitingToStand = 0
		self.ccLastAttacker = None


	def _initInventoryGUI( self ):
		weakself = weakref.proxy( self )

		def selectAndEquip( itemIndex ):
			itemSerial = self.inventoryMgr.itemIndex2Serial( itemIndex )
			itemType = self.inventoryMgr.selectItem( itemSerial )
			self._checkStowAndEquip()

		self.inventoryWindow = FantasyDemo.rds.fdgui.inventoryWindow.script
		self.inventoryWindow.inventoryMgr = weakref.proxy( self.inventoryMgr )

		self._stowSerial = [ Inventory.NOITEM ] * len( STOW_PLACES )


	def _initInventory( self ):
		self.inventoryMgr = Inventory.InventoryMgr( self, True )

		for i in self.inventoryItems:
			itemType = i["itemType"]
			Item.LoadBG(itemType,partial(self._cacheItem,itemType))


	def _initWoWMode( self ):
		self._useWoWMode = FantasyDemo.rds.useWoWMode
		self.inWoWMode = False
		self.onMouseMove = None
		self.inMouseMove = False
		self.isMovingToDest = False
		self.moveByStrafe = False
		self.autoMove = False
		self.isMoving = False
		self.isPanning = False
		self.mouseDown = False


	@BWKeyBindingAction( "WoWMode" )
	def _toggleWoWMode( self, isDown ):
		# Should only be used in response to a specific user command.
		# To show or hide the WoW mode for other reasons (like using the
		# binoculars), use the _enter and _leave methods.
		if isDown:
			if self.inWoWMode:
				self._leaveWoWMode()
				self._useWoWMode = False
			else:
				FantasyDemo.handleCameraKey( forceToStandardCamera = True )
				self._enterWoWMode()
				self._useWoWMode = True


	def _enterWoWMode( self ):
		if self.inWoWMode:
			return

		self.inWoWMode = True
		self.onMouseMove = None
		self.inMouseMove = False
		self.amountMouseMoved = 0
		self.isMovingToDest = False
		self.moveByStrafe = False
		self.autoMove = False
		self._setForwardMagnitude()
		self.physics.userDirected = False
		FDGUI.Cursor.forceShowCursor( True )
		self.enableEntityDirCamera()


	def enableEntityDirCamera( self ):
		FantasyDemo.setCursorCameraSource( self.entityDirProvider )
		self._isEntityDir = True

	def disableEntityDirCamera( self ):
		if hasattr( self, "_isEntityDir") and self._isEntityDir:
			m = Math.Matrix( self.entityDirProvider )
			BigWorld.dcursor().yaw = m.yaw
			BigWorld.dcursor().pitch = m.pitch
			self._isEntityDir = False
		FantasyDemo.setCursorCameraSource( BigWorld.dcursor().matrix )



	def _leaveWoWMode( self ):
		if not self.inWoWMode:
			return

		self.inWoWMode = False
		self.onMouseMove = None
		self.inMouseMove = False
		self.isMovingToDest = False
		self.moveByStrafe = False
		self.autoMove = False
		self._setForwardMagnitude()
		self.physics.userDirected = True
		FDGUI.Cursor.forceShowCursor( False )


	def _setupMouseMove( self ):
		self.amountMouseMoved = 0

		leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
		rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )
		if leftIsDown and rightIsDown:
			self._mouseMoveChange( 0, 0 )
		else:
			self.onMouseMove = self._mouseMoveChange


	def _enterMouseMove( self ):
		self.inMouseMove = True
		GUI.mcursor().visible = False
		GUI.mcursor().clipped = True
		self.disableMouseTargetting()

		try:
			turningHalfLife = BigWorld.camera().turningHalfLife
			if turningHalfLife > 0.0:
				self.savedTurningHalfLife = turningHalfLife
				BigWorld.camera().turningHalfLife = 0.0
		except AttributeError:
			#Free camera has no turningHalfLife attribute
			pass


	def _mouseMoveChange( self, dx, dy ):
		'''This function enables and disables camera movement using the
		direction cursor.

		To enable the camera movement it checks for mouse movement to become
		greater than a threshold. Once enabled, it is only disabled when both
		mouse buttons are up.

		It should be called on all mouse button events (up and down) to react
		to changes in the mouse button state as well as on all mouse move event
		until the threshold has been crossed.
		'''
		self._setForwardMagnitude()

		self.amountMouseMoved += abs(dx) + abs(dy)
		leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
		rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

		if leftIsDown and rightIsDown:
			self.autoMove = False
			self._enterMouseMove()

		if rightIsDown:
			if self.amountMouseMoved > FantasyDemo.rds.mouseMoveThreshold:
				self.onMouseMove = None
				self.moveByStrafe = True
				self.physics.userDirected = True
				if self.isMoving:
					BigWorld.dcursor().yaw = self.yaw
					BigWorld.dcursor().pitch = self.pitch
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

		elif leftIsDown:
			if self.amountMouseMoved > FantasyDemo.rds.mouseMoveThreshold:
				self.onMouseMove = None
				self.physics.userDirected = False
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

		else:
			if self.moveByStrafe:
				self.enableEntityDirCamera()
			self.inMouseMove = False
			self.onMouseMove = None
			self.moveByStrafe = False
			self.physics.userDirected = False
			BigWorld.setCursor( GUI.mcursor() )
			GUI.mcursor().visible = True
			GUI.mcursor().clipped = False
			if hasattr( self, "savedTurningHalfLife" ):
				BigWorld.camera().turningHalfLife = self.savedTurningHalfLife
				del self.savedTurningHalfLife
			self.enableMouseTargetting()


	def _movePlayer( self, position ):
		position = Math.Vector3(position) + (0,1,0)
		self._cleaupNavPathModels()
		try:
			self._moveNavPath = BigWorld.navigatePathPoints( self.position, position )
		except ValueError:
			self._moveNavPath = [ position ]
		

		if DEBUG_NAVIGATION_PATHS:
			for pathPoint in self._moveNavPath:
				m = BigWorld.Model( "helpers/models/unit_cube.model" )
				self.addModel( m )
				m.position = pathPoint
				self._moveNavPathModels.append( m )
			
		self._movePlayerNext()
		
		
	def _cleaupNavPathModels( self ):
		if hasattr(self, "_moveNavPathModels" ):
			for m in self._moveNavPathModels:
				self.delModel( m )
		self._moveNavPathModels = []
		
		
	def _movePlayerNext( self, prevSuccess=True ):
		if prevSuccess and len(self._moveNavPath) > 0:
			position = self._moveNavPath[0]
			self._moveNavPath = self._moveNavPath[1:]
			
			segmentLength = Math.Vector3(position).distTo( self.position )
			velocity = self.runFwdSpeed
			
			timeout  = max( 2.0, 2.0 * (segmentLength / velocity) )
			
			if DEBUG_NAVIGATION_PATHS:
				print "Moving to %s which is %f meters from where we are now (timeout=%f, velocity=%f). %d nav points left after this move." % \
					(position, segmentLength, timeout, velocity, len(self._moveNavPath))
			
			curr_yaw = (position - self.position).yaw
			destination = (position[0], position[1], position[2], curr_yaw)
			self.physics.velocity = (0, 0, velocity)
			self.physics.seek( destination, timeout, 100, self._movePlayerNext )
			self.isMovingToDest = True
		else:
			self._cleaupNavPathModels()
			if DEBUG_NAVIGATION_PATHS and not prevSuccess:
				print "_movePlayerNext: Failed to reach destination waypoint."
			self.isMovingToDest = False


	def _cancelMovePlayer( self ):
		BigWorld.player().physics.seek( None, 0, 0, None )
		self.isMovingToDest = False
		self._cleaupNavPathModels()


	def getMouseCollidePos( self ):
		mp = GUI.mcursor().position
		collisionType, target = collide.collide( mp.x, mp.y )
		return ( collisionType, target )


	def onAddItem( self, itemType, itemSerial ):
		if not self._itemCache.has_key( itemType ):
			Item.LoadBG(itemType,partial(self._cacheItem,itemType))


	def onRemoveItem( self, itemType, itemSerial ):
		pass

	@IgnoreCallbackIfDestroyed
	def _cacheItem( self, itemType, resourceLoader ):
		self._itemCache[itemType] = self.getItem( itemType, resourceLoader )


	def _initTradeData( self ):
		self._tradeOfferLock = None


	def onChangeEnvironments( self, inside ):
		self.inside = inside
		Minimap.onChangeEnvironments( inside )


	# This function lets us know we've been reloaded ...
	# and we want to re-get all these function pointers.
	def reload( self ):
		reload( sys.modules["Item"] )

		self.setupActionList()
		self.onBindCallback = self._getMovementKeys
		self.onBindCallback()


	def _getMovementKeys( self ):
		keyBindings = FantasyDemo.rds.keyBindings
		self.moveForwardKeys = keyBindings.getBindingsForAction( "MoveForward" )
		self.moveBackwardKeys = keyBindings.getBindingsForAction( "MoveBackward" )
		self.moveLeftKeys = keyBindings.getBindingsForAction( "MoveLeft" )
		self.moveRightKeys = keyBindings.getBindingsForAction( "MoveRight" )


	def updateCursor( self ):
		mouseEnabled = self.inWoWMode

		if mouseEnabled:
			BigWorld.setCursor( GUI.mcursor() )
		else:
			BigWorld.setCursor( BigWorld.dcursor() )
		GUI.mcursor().visible = mouseEnabled
		GUI.mcursor().clipped = not mouseEnabled



	def onBecomeNonPlayer( self ):
		self.filter = BigWorld.AvatarFilter()
		self.targetCaps = [ Caps.CAP_CAN_USE, Caps.CAP_CAN_HIT ]
		FantasyDemo.rds.keyBindings.removeHandler( self )

		# Could set self.gui, etc. to None if we wanted to
		# dispose their memory now too - instead it'll be
		# disposed when this Avatar is next made into a Player,
		# and those attributes are overwritten with new ones :-/


	def onLeaveWorld( self ):
		Avatar.onLeaveWorld( self )
		self._leaveWoWMode()
		FantasyDemo.delChangeEnvironmentsListener( self.onChangeEnvironments )
		FantasyDemo.rds.fdgui.onPlayerAvatarLeaveWorld( self )
		TeleportSource.cleanupTeleportGUI()
		FX.cleanupBufferedEffects()
		self._cleaupNavPathModels()


	#This method implements player avatar specific additions to Avatar's
	#enterWaterCallback.
	def enterWaterCallback( self, entering, volume ):
		Avatar.enterWaterCallback( self, entering, volume )
		self.setUpMovementSpeedsFromModel()
		if entering:
			self.walkFwdSpeed /= 2.0
			self.runFwdSpeed /= 3.0
			self.dashFwdSpeed /= 4.0
			if not hasattr( self, "waterViscosity" ):
				self.waterViscosity = 3.0
				self.waterBuoyancy = 16
				self.waterSurfaceHeightDelta = -1.30
			self.physics.inWater = True
			self.physics.viscosity = self.waterViscosity
			self.physics.waterSurfaceHeight = volume.surfaceHeight + self.waterSurfaceHeightDelta
			self.physics.buoyancy = self.waterBuoyancy
		else:
			self.physics.inWater = False
		self.updateVelocity()


	# Avatar override: Going into using item mode
	def enterUsingItemMode( self ):
		Avatar.enterUsingItemMode( self )
		self.updateVelocity()

	# Avatar override: Going out of using item mode
	def leaveUsingItemMode( self ):
		#if self.rightHand != Item.Item.NONE_TYPE and self.rightHandItem:
		#	self.rightHandItem.release( self )
		Avatar.leaveUsingItemMode( self )

	# Avatar override: Entering crouch mode
	def enterCrouchMode( self ):
		FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenCrouched, 0.0 )
		Avatar.enterCrouchMode( self )
		self.updateVelocity()

	# Avatar override: Leaving crouch mode
	def leaveCrouchMode( self ):
		FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenStanding, 0.0 )
		Avatar.leaveCrouchMode( self )

	# Avatar override: Going into seated mode
	def enterSeatedMode( self ):
		self.sitDownWait( 5 )

	# Avatar override:
	@IgnoreCallbackIfDestroyed
	def sitDownWait( self, count ):
		if BigWorld.entity( self.modeTarget ) != None:
			FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenSeated, 0.0 )
			Seat.sitDown( self )
		elif count > 0:
			BigWorld.callback( 1, partial( self.sitDownWait, count-1 ) )

	# Avatar override: Leaving seated mode
	def leaveSeatedMode( self ):
		FantasyDemo.setCursorCameraPivot( 0.0, self.cameraHeightWhenStanding, 0.0 )
		Seat.standUp( self )

	def spawnPoint( self ):
		online = BigWorld.server()
		if online:
			rad = 3.0
			return (self.initialPos[0] + random.uniform( -rad, rad ),
				self.initialPos[1],
				self.initialPos[2] + random.uniform( -rad, rad ) )
		else:
			return self.initialPos

	def enterDeadMode( self ):
		BigWorld.callback( 6.0 + Avatar.DEAD_PENALTY,
			partial( self.physics.teleport, self.spawnPoint() ) )
		BigWorld.callback( 8.0 + Avatar.DEAD_PENALTY, self.cell.reincarnate )
		self.updateVelocity()
		self.equip( Item.Item.NONE_TYPE, 0 )
		self._leaveWoWMode()
		if hasattr( self, "physics" ) and self.physics is not None:
			self.physics.userDirected = False
		Avatar.enterDeadMode( self )

	def leaveDeadMode( self ):
		Avatar.leaveDeadMode( self )
		self.updateVelocity()
		self.filter = BigWorld.PlayerAvatarFilter()
		self.targetCaps = []
		self._enterWoWMode()

	def endReincarnation( self ):
		Avatar.endReincarnation( self )

		# Make sure doing action is zero, in case we died in some weird state
		if self.doingAction != 0: self.doingAction = 0

	# Avatar override: Becoming a target
	def modeTargetFocus( self, other ):
		# TODO: Put arrow over 'other'
		pass

	# Avatar override: Quitting as target
	def modeTargetBlur( self, other ):
		# TODO: Remove arrow from 'other'
		pass

	def moveActionCommence( self ):
		self.doingMovableAction += 1
		self.actionCommence()

	# Avatar override: Action commence
	def actionCommence( self ):
		#print "PlayerAvatar::actionCommence: doingAction was %d, now %d" % (
		#	self.doingAction, self.doingAction+1 )
		Avatar.actionCommence( self )
		if not self.doingAction:
			self._actionCommenceDirected = self.physics.userDirected
			self.physics.userDirected    = 0
		self.doingAction += 1
		self.updateVelocity()

	# Avatar override: Action complete
	def actionComplete( self ):
		if self.doingAction == 0:
			print "Warning: doingAction would go negative."
			traceback.print_stack()
			return

		#print "PlayerAvatar::actionComplete: doingAction was %d, now %d" % (
		#	self.doingAction, self.doingAction-1 )
		self.doingAction -= 1

		self.updateVelocity()

		if self.doingMovableAction > 0:
			self.doingMovableAction -= 1

		try:
			if not self.doingAction:
				self.physics.userDirected = self._actionCommenceDirected
		except AttributeError:
			pass

		Avatar.actionComplete( self )

		self.doingActionDecremented()

	# doingAction was decremented (only done in actionComplete
	#  and when right mouse released for targetting)
	def doingActionDecremented( self ):
		# If we are now free, then respond to any waiting events
		if self.mode == Mode.NONE and self.doingAction == 0:

			# If we're being attacked then fight back immediately
			if self.ccLastAttacker != None and \
				self.ccLastAttacker.mode == Mode.COMBAT_CLOSE and \
				self.ccLastAttacker.modeTarget == self.id:
					self.ccRespond( self.ccLastAttacker )


	# Enter the appropriate GUI mode
	def guiMode( self, mode ):
		if mode == 0:
			#Standard H.U.D.
			FantasyDemo.rds.fdgui.showBinoculars( False )
			FantasyDemo.firstPerson( self.firstPerson )
			BigWorld.projection().fov = 1.0472 #60 degrees
			if self._useWoWMode:
				self._enterWoWMode()
			self.hideModel( self.firstPerson )
		elif mode == 1:
			#Spy Camera. Removed.
			pass
		else:
			#Binoculars
			FantasyDemo.rds.fdgui.showBinoculars( True )
			BigWorld.projection().fov = 0.5 #zoomed in
			FantasyDemo.firstPerson( True )
			if self.inWoWMode:
				self._leaveWoWMode()
			self.hideModel( 1 )

			# Calculate the new FOV into which to move.
			#self.oldZoomLevel = 0
			#minFOV = 2.5
			#maxFOV = 18.0
			#newFOV = maxFOV + ( minFOV - maxFOV ) * (
			#	self.oldZoomLevel / 30.0 )
			# <binoculars need more work> BigWorld.changeFOV( newFOV, 0.01 )

		self.guiModeSelected = mode


	# -------------------------------------------------------------------------
	# Command: Cancel current action.
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "EscapeKey" )
	def escapeKey( self, isDown ):
		handled = False

		if isDown:
			handled = True

			if self.mode in ( Mode.TRADE_ACTIVE, Mode.TRADE_PASSIVE ):
				self.tradeCancel()
			elif self.mode == Mode.COMMERCE:
				self.commerceCancel()
			elif self.mode == Mode.SEATED:
				BigWorld.entity(self.modeTarget).use()
			elif self.mode != Mode.NONE and not self.inCombat():
				FantasyDemo.cameraType( FantasyDemo.rds.CURSOR_CAMERA )
				if not self._isConnected():
					omode = self.mode
					self.mode = -1
					self.set_mode( omode )
				elif self.mode == Mode.COMBAT_CLOSE:
					self.cell.cancelMode()
					if self.ccTarget is not None and \
							self.ccTarget.mode == Mode.COMBAT_CLOSE and \
								self.ccTarget.modeTarget == self.id:
						self.ccTarget.cell.cancelMode()
				else:
					self.cell.cancelMode()
			elif self.inCombat():
				# remove the weapon, so that you go out of combat mode
				self.unequipItem()
			elif not self.doingAction and self.rightHand != Item.Item.NONE_TYPE:
				self.unequipItem()
			else:
				handled = False

		return handled


	# -------------------------------------------------------------------------
	# Command: Last resort gameplay-ignoring current action cancel
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "LastResortEscapeKey" )
	def lastResortEscapeKey( self, isDown ):
		if not isDown: return

		if hasattr( self, "lastResortGui" ): return

		g = GUI.Text( "WAIT" )
		g.position = (0,0,1)
		GUI.addRoot( g )
		self.lastResortGui = g

		# First wait 2s
		self.lastResortGui.colour = (255,0,0,255)
		BigWorld.callback( 2, self.lrekTwo )

	@IgnoreCallbackIfDestroyed
	def lrekTwo( self ):
		# Try a normal escape
		try:
			self.escapeKey( 1 )
		except:
			pass

		# And wait 2s
		self.lastResortGui.colour = (255,255,255,255)
		BigWorld.callback( 2, self.lrekThree )

	@IgnoreCallbackIfDestroyed
	def lrekThree( self ):
		# Now try a server cancel mode
		if self.mode != Mode.NONE:
			self.cell.cancelMode()

		# Wait 2s
		self.lastResortGui.colour = (255,0,0,255)
		BigWorld.callback( 2, self.lrekFour )

	@IgnoreCallbackIfDestroyed
	def lrekFour( self ):
		# If we're still not in the right mode, reincarnate ourselves
		# (which always gets us out of any mode ... currently)
		if self.mode != Mode.NONE:
			self.cell.reincarnate()

		# Wait 2s
		self.lastResortGui.colour = (255,255,255,255)
		BigWorld.callback( 2, self.lrekFive )

	@IgnoreCallbackIfDestroyed
	def lrekFive( self ):
		# Clean up locally

		# Clear our mode anyway
		self.mode = Mode.NONE

		# Doing action
		if self.doingAction < 0: self.doingAction = 0
		while self.doingAction > 0: self.actionComplete()

		# Clear our right hand item
		self.rightHand = -1
		self.cell.setRightHand( -1 )

		# Recreate our model (fixes queue, visibility, and trackers)
		self.set_modelNumber()

		self.lastResortGui.colour = (255,0,0,255)
		BigWorld.callback( 0.5, self.lrekEnd )

	def lrekEnd( self ):
		# Turn off any weird GUI things
		self.firstPerson = 0
		self.guiMode( 0 )

		self.hud.lastResortGui = None
		del self.lastResortGui


	# -------------------------------------------------------------------------
	# Command: Sets the zoom level for the player.
	# -------------------------------------------------------------------------
	def setZoomLevel( self, newZoomLevel ):
		if self.guiModeSelected == 2:
			# Calculate the new FOV into which to move.
			minFOV = 2.5
			maxFOV = 18.0
			newFOV = maxFOV + ( minFOV - maxFOV ) * ( newZoomLevel / 30.0 )

			timeToChange = 0.25
			if self.oldZoomLevel > newZoomLevel:
				pass # BigWorld.playFx( "binoc_out", self.position )
				pass # BigWorld.changeFOV( newFOV, timeToChange * 2.0 )
			elif self.oldZoomLevel < newZoomLevel:
				pass # BigWorld.playFx( "binoc_in", self.position )
				BigWorld.changeFOV( newFOV, timeToChange )
				timeToChange = 0.25

			self.oldZoomLevel = newZoomLevel


	# -------------------------------------------------------------------------
	# Command: Toggles between first and third person mode.
	# -------------------------------------------------------------------------
	def toggleFirstPersonMode( self, isDown ):
		if not self.guiModeSelected == 2 and self.allowFPSModeToggle:
			if not self.freeCamera:
				if isDown:
					self.firstPerson = 1
				else:
					self.firstPerson = 0

				FantasyDemo.firstPerson( self.firstPerson )
				self.hideModel( self.firstPerson )
				return True
		return False


	def allowFirstPersonModeToggle(self, allow):
		self.allowFPSModeToggle = allow

	# -------------------------------------------------------------------------
	# Command: Toggles between mouse control and direction cursor modes for
	# the camera.
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "FreeCameraMode" )
	def toggleFreeCameraMode( self, isDown ):
		if not self.firstPerson:
			if isDown:
				self.freeCamera = not self.freeCamera
				FantasyDemo.freeCamera( self.freeCamera )

	# -------------------------------------------------------------------------
	# Command: Null action. This is used if the C++ code has a binding for
	# one of the keys used by another command; the script code then binds
	# that set to the null action.
	#
	# eg. The C++ code looks for Shift+MiddleMouseButton.
	# Since the script also watches for MiddleMouseButton, then it needs to
	# also bind Shift+MiddleMouseButton to nullAction to disambiguate the
	# key presses.
	# -------------------------------------------------------------------------
	def nullAction( self, isDown ):
		pass

	# -------------------------------------------------------------------------
	# Section: Items trading commands
	# -------------------------------------------------------------------------

	@BWKeyBindingAction( "Trade" )
	def onTradeKey( self, isDown = True ):
		'''Handles do-trade key event.
		Params:
			isDown				key down state
		'''
		if not isDown:
			return

		if self.mode == Mode.SEATED or self.inCombat():
			return

		if self.mode not in (Mode.TRADE_ACTIVE, Mode.TRADE_PASSIVE):
			if not self.doingAction:
				self.tradeTry()
		else:
			self.tradeCancel()


	def onTradeOfferItem( self, itemSerial ):
		'''Handles item offer events (when the user draggs and
		dropps an item in the trade area in the inventory GUI).
		Do not allow new offers if there is one already on the
		table (the player must cancel the current one first).
		Params:
			itemIndex			index of item in the inventory
		'''
		assert self.mode in ( Mode.TRADE_ACTIVE, Mode.TRADE_PASSIVE )
		assert self._tradeOfferLock == None

		try:
			self._tradeOfferLock = self.inventoryMgr.itemsLock( [itemSerial], 0 )
			self.cell.tradeOfferItemRequest( self._tradeOfferLock, itemSerial )
			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )
		except ValueError:
			errorMsg = 'PlayerAvatar.onTradeOfferItem: invalid item (itemSerial=%d)'
			print errorMsg % itemSerial

		except Inventory.LockError:
			errorMsg = 'PlayerAvatar.onTradeOfferItem: lock error (itemSerial=%d)'
			print errorMsg % itemSerial


	def onTradeAccept( self, accept ):
		'''Handles trade commit events (when user clicks
		on the trade button in the inventory gui)
		'''
		assert self.mode in ( Mode.TRADE_ACTIVE, Mode.TRADE_PASSIVE )
		self.cell.tradeAcceptRequest( accept )

	# -------------------------------------------------------------------------
	# Section: Items trading
	# -------------------------------------------------------------------------

	def tradeTry( self ):
		'''Try entering the trade mode
		'''
		partner = BigWorld.target()
		if self.inventoryItems and partner and isinstance( partner, Avatar ):
			self.unequipItem()
			self.moveActionCommence()
			if partner.mode == Mode.TRADE_PASSIVE and \
					partner.modeTarget == self.id:
				self.tradeActiveEngage( partner )
			else:
				self.cell.tradeStartRequest( partner.id )
				self.setModeTarget( partner.id )
			return

		self.disagree()


	def tradeCancel( self ):
		'''Requests cancelation of trade mode
		'''
		self.cell.tradeCancelRequest()


	def tradeActiveEngage( self, partner ):
		'''Try entering the active trade mode. Partner is already waiting
		for us to trade with him (he is in TRADE_PASSIVE mode). Do this in
		two steps: (1) move close to Partner and (2) request trade mode
		Params:
			partner				the trade partner entity
		'''
		def doStep1():
			self._tradePosSeek( partner, doStep2, doFail )

		def doStep2():
			self.cell.tradeStartRequest( partner.id )
			self.setModeTarget( partner.id )

		def doFail():
			self.setModeTarget( Mode.NO_TARGET )
			self.actionComplete()
			self.disagree()

		doStep1()


	def tradeActiveEnterMode( self ):
		'''Called when PlayerAvatar.mode gets set by the cell.
		The active Avatar takes care of setting up the stage,
		animating both characters and showing the trade icon
		'''
		partner = ModeTarget._getModeTarget( self )

		if partner:
			partner.tradeAnimateAccept()
			self.tradeAnimateAccept()
			self.tradeShowGUI( True )


	def tradeActiveLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell. Cleans the scene.
		'''
		self._tradeLeaveMode()


	def tradePassiveEnterMode( self ):
		'''Called when PlayerAvatar.mode gets set by the cell. Shows the trade icon.
		'''
		pass


	def tradePassiveLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell. Clears trade icon.
		'''
		self._tradeLeaveMode()


	def tradeDeny( self ):
		'''The cell is denying our request to enter trade mode.
		(maybe partner can't or doesn't want to trade with us).
		'''
		self.setModeTarget( Mode.NO_TARGET )
		self.actionComplete()
		self.disagree()


	def _tradePosSeek( self, partner, successCallback, failCallback ):
		'''Move avatar to the position where the coordinated handshake
		animation can be played. Eventually calls successCallback or
		failCallback depending of the outcome of the seek operation.
		Params:
			partner           partner with whom to do the handshake
			successCallback	callback to be called if seek is successfull
			failCallback		callback to be called if seek fails
		'''
		def onSeek( success ):
			if success:
				successCallback()
			else:
				failCallback()

		self.physics.seek( partner.model.Shake_B_Accept.seekInv, 5.0, 0.10, onSeek )
		self.physics.velocity = ( 0, 0, self.walkFwdSpeed )


	def tradeShowGUI( self, visible ):
		'''Shows/hide inventory GUI in trade mode.
		Params:
			visible				True if GUI is to be shown. False if should be hidden
		'''
		self.updateCursor()


	def tradeOfferItemNotify( self, itemType ):
		'''Cell is notifying us that an item is being offered by trade partner.
		Params:
			itemType				Type of item being offered by partner
		'''
		pass


	def tradeOfferItemDeny( self, tradeItemLock ):
		'''Notifies this avatar that his item offer has been denied
		by the server (maybe it has been locked via web trading).
		Params:
			tradeItemLock		handle to offered item's lock
		'''
		assert self._tradeOfferLock == tradeItemLock
		self._tradeOfferLock = None

		self.inventoryMgr.itemsUnlock( tradeItemLock )
		self.disagree()


	def tradeAcceptNotify( self, accepted ):
		'''Cell is notifying us that our trade partner has accepted our offer.
		Params:
			accepted				True if partner is accepting item. False otherwise
		'''
		pass


	def tradeCommitNotify( self, success, outItemsLock,
			outItemsSerial, outGoldPieces, inItemsTypes,
			inItemsSerials, inGoldPieces ):
		'''Cell is responding to our trade commit request.
		Params:
			success				True if trade was successful. False otherwise
			outItemsLock		Lock of items being traded out
			outItemsSerial		serials of items being traded out
			outGoldPieces		ammount of gold being traded out
			inItemsTypes		array of items being traded in
			inItemsSerials		serials of items being traded in
			inGoldPieces		ammount of gold pieces being traded in
		'''
		# this notification is also used by the commerce system.
		# If this is the case, do a commerce commit notification
		if self.mode == Mode.COMMERCE:
			self._commerceCommitNotify( success, outItemsLock, inItemsTypes )
		elif self._tradeOfferLock != None:
			self._tradeCommitNotify( success, outItemsLock )

		if success:
			serials = self.inventoryMgr.itemsTrade(
					outItemsSerial, outGoldPieces,
					inItemsTypes, inItemsSerials,
					inGoldPieces, outItemsLock )

			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )
		else:
			self.inventoryMgr.itemsUnlock( outItemsLock )


	def _tradeCommitNotify( self, success, outItemsLock ):
		'''Takes care of properly updating the trading interface after a
		trade transcation has been completed. Note that the actual items/gold
		transcation will be carried by the tradeCommitNotify method.
		Params:
			success				True if trade was successful. False otherwise
			outItemsLock		lock handle for items being traded out
		'''
		assert self._tradeOfferLock == outItemsLock
		self._tradeOfferLock = None

		if not success:
			ModeTarget._getModeTarget( self ).disagree()
			self.disagree()


	def _tradeLeaveMode( self ):
		'''Common functions for when player avatar leaves the trade mode.
		'''
		self.setModeTarget( Mode.NO_TARGET )
		self.tradeShowGUI( False )
		self.actionComplete()
		if self._tradeOfferLock != None:
			self.cell.itemsUnlockRequest( self._tradeOfferLock )
			self._tradeOfferLock = None

	# -------------------------------------------------------------------------
	# Section: Items locking
	# -------------------------------------------------------------------------

	def onUnlockItem( self, lockHandle ):
		'''Handles unlock item events (when user clicks on a locked
		item in the inventory gui). Requests unlocking to server.
		Params:
			lockHandle			handle to item(s) lock
		'''
		self.cell.itemsUnlockRequest( lockHandle )


	def itemsLockNotify( self, lockHandle, itemsSerials, goldPieces ):
		'''Cell is notifying us about items being locked. Just should only
		be called when the locking was not done as a request from the client
		(since in those cases, the client locks his items preenptively).
		Lock items localy so that the player cannot use them. Unequip
		current item if it is in the list of items to lock.
		Params:
			lockHandle			handle to recently locked items
			itemsSerials		serial to all items being locked
			goldPieces			ammount of gold to lock
		'''
		try:
			try:
				if self.inventoryMgr.currentItemSerial() in itemsSerials:
					self.unequipItem()
			except ValueError: # no current item
				pass
			self.inventoryMgr.itemsRelock( lockHandle, itemsSerials, goldPieces )
			self.inventoryWindow.updateInventory(
				self.inventoryItems,
				self.inventoryMgr.availableGoldPieces() )
		except Inventory.LockError:
			errorMsg = 'ClientAvatar.itemsLockNotify: cannot lock items'
			print errorMsg


	def itemsUnlockNotify( self, success, lockHandle ):
		'''Notification that some item(s) have being unlocked in the
		server. Unlock them localy, as well. If lockHandle is for the
		item currently offered for trade, remove it from trade GUI.
		Params:
			success				True if request granted or is not a response to one
			lockHandle			handle to recently unlocked items
		'''
		if success:
			try:
				self.inventoryMgr.itemsUnlock( lockHandle )
			except Inventory.LockError:
				errorMsg = 'PlayerAvatar.itemsUnlockNotify: error unlocking items (handle=%d)'
				print errorMsg % lockHandle
				pass

			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )

			if lockHandle == self._tradeOfferLock:
				self._tradeOfferLock = None
		else:
			self.disagree()
			if lockHandle == self._tradeOfferLock:
				FantasyDemo.addChatMsg( -1, 'Cannot withdraw accepted offer' )
			else:
				FantasyDemo.addChatMsg( -1, 'Cannot unlock item' )

	# -------------------------------------------------------------------------
	# Section: Items commerce commands
	# -------------------------------------------------------------------------

	@BWKeyBindingAction( "Commerce" )
	def onCommerceKey( self, isDown = True, partner = None ):
		'''Handles do-commerce key event.
		Params:
			isDown				key down state
		'''
		if not isDown:
			return

		if self.mode == Mode.SEATED or self.doingAction or self.inCombat():
			return

		if self.mode != Mode.COMMERCE:
			if partner == None:
				partner = BigWorld.target()
			self.commerceTry( partner )
		else:
			self.commerceCancel()


	def onSellItem( self, itemSerial ):
		'''Handles item sell events (when the user
		clicks on the sell button in the inventory GUI)
		Params:
			itemIndex			index of item in the inventory
		'''
		#~ print '--->', itemSerial
		#~ return

		assert self.mode == Mode.COMMERCE
		try:
			itemLock = self.inventoryMgr.itemsLock( [itemSerial], 0 )
			self.cell.commerceSellRequest( itemLock, itemSerial )
		except (Inventory.LockError, ValueError):
			FantasyDemo.addChatMsg( -1, "Unable to sell specified item" )


	def onBuyItem( self, itemIndex ):
		'''Handles item buy events (when the user clicks on the
		buy button in the inventory GUI). Ignore command if we're
		waiting for a reply from server about a previous buy.
		Params:
			itemIndex			index of item in the seller inventory
		'''
		if self._buyItemIndex is not None:
			return

		try:
			itemPrice = Item.price( self._commerceItems[ itemIndex ]['itemType'] )
			itemLock = self.inventoryMgr.itemsLock( [], itemPrice )
			self._buyItemIndex = itemIndex
			self.cell.commerceBuyRequest( itemLock, itemIndex )
		except Inventory.LockError:
			FantasyDemo.addChatMsg( -1, "Not enough gold pieces to buy item" )
			self.disagree()
		except IndexError:
			errorMsg = 'PlayerAvatar.onBuyItem: invalid item index (idx=%d)'
			print errorMsg % itemIndex
			self.disagree()

	# -------------------------------------------------------------------------
	# Section: Items commerce
	# -------------------------------------------------------------------------

	def commerceTry( self, partner ):
		'''Try entering the commerce mode
		'''
		if partner and isinstance( partner, Merchant.Merchant ):
			if partner.modeTarget == Mode.NO_TARGET:
				self.unequipItem()
				self.moveActionCommence()
				self.commerceEngage( partner )
				return
		self.disagree()


	def commerceCancel( self ):
		'''Requests cancelation of commerce mode
		'''
		self.cell.commerceCancelRequest()


	def commerceEngage( self, partner ):
		'''Try entering the commerce mode. Do this in two steps:
		(1) move close to Merchant and (2) request commerce mode.
		Params:
			partner				the commerce partner entity
		'''
		def doStep1():
			self._tradePosSeek( partner, doStep2, doFail )

		def doStep2():
			self.actionCommence()
			self.setModeTarget( partner.id )
			self.cell.commerceStartRequest( partner.id )

		def doFail():
			self.setModeTarget( Mode.NO_TARGET )
			self.actionComplete()
			self.disagree()

		doStep1()


	def commerceEnterMode( self ):
		'''Called when PlayerAvatar.mode gets set by the cell.
		The PlayerAvatar takes care of setting up the stage, animating
		both characters and showing the commerce icon
		'''
		def endHandshake():
			self.actionComplete()

		partner = ModeTarget._getModeTarget( self )
		if partner != None:
			self.tradeAnimateAccept( endHandshake )
			partner.tradeAnimateAccept()
			self._commerceShowGUI( True )
			self._buyItemIndex = None


	def commerceLeaveMode( self ):
		'''Called when Avatar.mode gets set by the cell. Cleans the scene.
		'''
		traderWindow = FantasyDemo.rds.fdgui.traderWindow.script
		traderWindow.updateInventory( [], 0 )
		traderWindow.active( False )

		if not self._inventoryWasActive:
			self.inventoryWindow.active( False )

		self.actionComplete()
		partner = ModeTarget._getModeTarget( self )
		self.setModeTarget( Mode.NO_TARGET )
		self._commerceShowGUI( False )
		self._commerceItems = None
		self.cell.finaliseCommerceCancel()


	def commerceStartDeny( self ):
		'''The cell is denying our request to enter commerce mode.
		(maybe Merchant has just been grabbed by another player).
		'''
		self.setModeTarget( Mode.NO_TARGET )
		self.actionComplete()
		self.disagree()


	def _commerceShowGUI( self, visible ):
		'''Shows/hide inventory GUI in commerce mode.
		Params:
			visible				True if GUI is to be shown. False if should be hidden
		'''
		if visible:
			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )

		self.updateCursor()


	def commerceItemsNotify( self, items ):
		'''The Merchant is notifying us about the items it has for sale.
		Params:
			items					List of item being sold by merchant
		'''
		self._commerceItems = items

		traderWindow = FantasyDemo.rds.fdgui.traderWindow.script
		traderWindow.updateInventory( self._commerceItems, 0 )
		traderWindow.active( True )

		self._inventoryWasActive = self.inventoryWindow.isActive
		self.inventoryWindow.active( True )


	def _commerceCommitNotify( self, success, outItemsLock, inItemsTypes ):
		'''This method is called by the trade commit notify if the
		transaction was the result of a commerce (buy/sell) operation.
		Note that the actual items/gold transcation will be carried by
		the tradeCommitNotify method. This methos will only take care
		of properly updating the commerce interface.
		Params:
			success				True if trade was successful. False otherwise
			outItemsLock		lock handle for items being traded out
			inItemsTypes		types of items being traded in
		'''
		if success:
			try:
				discardSerial, outItems, goldPieces = \
					self.inventoryMgr.itemsLockedRetrieve( outItemsLock )

				if outItems:
					# Player is selling
					Inventory.addItems( self._commerceItems, [{'serial': discardSerial[i], 'itemType':outItems[i], 'lockHandle':Inventory.NOLOCK } for i in range(len(outItems)) ] )
				else:
					# Player is buying
					assert len( inItemsTypes ) == 1
					assert self._commerceItems[ self._buyItemIndex ]['itemType'] == inItemsTypes[0]
					Inventory.removeItem( self._commerceItems, self._buyItemIndex )
					self._buyItemIndex = None

				traderWindow = FantasyDemo.rds.fdgui.traderWindow.script
				traderWindow.updateInventory( self._commerceItems, 0 )
				traderWindow.active( True )

			except Inventory.LockError:
				errorMsg   = 'PlayerAvatar._commerceCommitNotify: lock not found '
				parameters = '(lock=%d)' % outItemsLock
				print errorMsg + parameters
		else:
			self._buyItemIndex = None
			FantasyDemo.addChatMsg( -1, "Merchant is unable to proceed with trade" )
			ModeTarget._getModeTarget( self ).disagree()
			self.disagree()


	# -------------------------------------------------------------------------
	# Section: Items pick-up and drop commands
	# -------------------------------------------------------------------------

	@BWKeyBindingAction( "PickDrop" )
	def onPickDropKey( self, isDown = True ):
		'''Handles pick/drop item key events.
		Params:
			isDown				key down state
		'''
		# ignore key if player is seated, in
		# combat or doing some other action
		if self.mode == Mode.SEATED or not isDown or \
				self.doingAction:
			return

		# if not holding an item, try picking one up
		# if holding an item, try dropping it
		if self.rightHand == Item.Item.NONE_TYPE:
			self.pickUpTry()
		else:
			self.dropTry()


	def onEquipNDrop( self, itemIndex ):
		'''Handles item drop event (when the user draggs and
		drops an item in the drop area in the inventory gui)
		Params:
			itemIndex			index to inventory of item being dropped
		'''
		currentItem = self.inventoryMgr.currentItem()
		if currentItem != self.rightHand:
			self.equip( currentItem )
			cib = self.model.ChangeItemBegin
			cibDur = cib.duration - cib.blendOutTime - 0.0001
			cie = self.model.ChangeItemEnd
			cieDur = cie.duration - cie.blendOutTime - 0.0001
			BigWorld.callback( cibDur + cieDur, partial( self.onPickDropKey ) )
		else:
			self.onPickDropKey()

	# -------------------------------------------------------------------------
	# Section: Items pick-up
	# -------------------------------------------------------------------------

	def pickUpTry( self ):
		'''Try to pick-up current target.
		'''
		target = BigWorld.target()
		Item = DroppedItem.DroppedItem
		if target and isinstance( target, Item ) and target.pickUpTry():
			self.pickExecute( target )
		else:
			self.disagree()


	def pickExecute( self, droppedItem ):
		'''Do the first two steps in the pick-up procedure:
		(1) seek pick-up position and (2) request pick-up to cell.
		Params:
			droppedItem			item entity being picked up
		'''
		def doStep1():
			self.unequipItem()
			self.moveActionCommence()
			self.pickUpSeekPos( droppedItem, doStep2, handleFailure )

		def doStep2():
			if self._isConnected():
				self.cell.pickUpRequest( droppedItem.id )
				self._pickUpSetupCancelTimer()
			else:
				# if not connected, short circuit
				import time
				self.pickUpResponse( True, droppedItem.id, int(time.clock()) + 100 )

		def handleFailure():
			self.disagree()
			self.actionComplete()

		doStep1()


	def _pickUpSetupCancelTimer( self ):
		'''Sets timer for cancelation of pick-up.
		'''
		@IgnoreCallbackIfDestroyed
		def cancel( self ):
			if self._waitingPickup:
				self.disagree()
				self.actionComplete()
				self._waitingPickup = False

		self._waitingPickup = True
		BigWorld.callback( self.DROPPICK_TIMEOUT, partial( cancel, self ) )


	def pickUpResponse( self, success, droppedItemID, itemSerial ):
		'''Cell entity is notifying that this entity is picking up an item
		Params:
			success				True is pickup request was granted. False otherwise
			droppedItemID		id of item entity being picked up
			itemSerial			serial assigned to item when inside the inventory
		'''
		if success:
			try:
				droppedItem = BigWorld.entities[ droppedItemID ]
				self._pickUpProcedure( droppedItem, itemSerial )
			except KeyError:
				errorMsg = 'pick-up response for unknown entity: %d'
				print errorMsg % droppedItemID
		else:
			self.disagree()
			self.actionComplete()

		self._waitingPickup = False


	def _pickUpProcedure( self, droppedItem, itemSerial ):
		'''Does the pickup procedure and adds item to inventory.
		Params:
			droppedItem			item entity being picked up
			itemSerial			serial assigned to item when inside the inventory
		'''

		def doStep1():
			self.lockRightHandModel( True )
			self.pickUpAnimate( doStep2, doStep3 )

		def doStep2():
			droppedItem.pickUpComplete()
			itemType = droppedItem.classType
			self.inventoryMgr.addItem( itemType, itemSerial )
			self.inventoryMgr.selectItem( itemSerial )
			itemIndex = self.inventoryMgr.currentItemIndex()

			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )

			self.lockRightHandModel( False )
			self.equip( itemType, 0 )

		def doStep3():
			self.actionComplete()

		doStep1()
		self._waitingPickup = False


	def pickUpSeekPos( self, droppedItem, successCallback, errorCallback ):
		'''Moves avatar close to the item where the pickup animation
		should be played. Eventually calls successCallback or failCallback
		depending of the outcome of the seek operation.
		Params:
			droppedItem			item entity being picked up
			successCallback	callback to be called if seek is successfull
			failCallback		callback to be called if seek fails
		'''
		moveToPos = Vector3( droppedItem.position )

		#	1. Find the normalised direction
		#     from player to item.
		delta = moveToPos - Vector3( self.position )
		delta.normalise()

		#	2. Offset that distance by an approximate
		#     hand-to-item distance.
		#
		#  TODO: The magic cueball says it is around 45 cm.
		#  We should not be relying on the magic cueball.
		handToItemDist = 0.45
		delta = delta.scale( handToItemDist )
		moveToPos -= delta

		#	3. Calculate the desired termination
		#     yaw from the delta vector.
		yaw = math.atan2( delta.x, delta.z )

		#  4. Tell the Avatar to move into position.
		finalPosition = ( moveToPos.x, moveToPos.y, moveToPos.z, yaw )

		def onSeek( success ):
			if success:
				successCallback()
			else:
				errorCallback()

		self.physics.seek( finalPosition, 10.0, 0.40, onSeek )
		self.physics.velocity = ( 0, 0, self.walkFwdSpeed )


	def disagree( self ):
		'''Play the disagree animation.
		'''
		Avatar.disagree( self )
		self.cell.didGesture( 4 )

	# -------------------------------------------------------------------------
	# Section: Items drop
	# -------------------------------------------------------------------------

	def dropTry( self ):
		'''Try to drop currently equipped item.
		'''
		if self._isConnected():
			self.dropOnline()
		else:
			self.dropOffline()


	def dropOnline( self ):
		'''Request item drop to base.
		'''
		self.actionCommence()
		itemClass = self.inventoryMgr.currentItem()
		itemSerial = self.inventoryMgr.currentItemSerial()
		self.base.dropRequest( itemSerial )

		# ... setup cancel timer
		@IgnoreCallbackIfDestroyed
		def cancel( self ):
			if self._waitingDrop:
				self.disagree()
				self.actionComplete()
				self._waitingDrop = False

		self._waitingDrop = True
		BigWorld.callback( self.DROPPICK_TIMEOUT, partial( cancel, self ) )


	def dropOffline( self ):
		'''Simulate server response to drop request:
		create a local item at hand distance.
		'''
		self.actionCommence()

		# compute drop position
		dir = Vector3( math.sin(self.yaw), 0, math.cos(self.yaw) )
		dropPos = Vector3(self.position) + dir.scale( 0.45 )

		upVector = Vector3(0.0, 2.0, 0.0)
		dropRes = BigWorld.findDropPoint( self.spaceID, dropPos + upVector )
		if dropRes != None:
			dropPos = dropRes[0]

		# create DroppedItem
		itemClass = self.inventoryMgr.currentItem()
		itemSerial = self.inventoryMgr.currentItemSerial()
		properties = {
				'itemSerial'	 : itemSerial,
				'classType'		 : itemClass,
				'dropperID'		 : self.id }

		BigWorld.createEntity( 'DroppedItem',
			self.spaceID, 0, dropPos.tuple(),
			( 0.0, self.yaw, 0.0 ), properties )


	def _dropProcedure( self, droppedItem ):
		'''Do the complete drop procedure in three steps: (1) start drop,
		(2) drop/unequip/remove item from inventory and (3) finish drop.
		Overrides method in Avatar. Also invalidates drop cancelation timer.
		Params:
			droppedItem			DroppedItem entity just dropped
		'''
		def doStep1():
			self.lockRightHandModel( True )
			self.dropAnimate( droppedItem, doStep2, doStep3 )

		def doStep2():
			droppedItem.dropComplete()
			self.inventoryMgr.removeItem(droppedItem.itemSerial)
			self.inventoryWindow.updateInventory(
					self.inventoryItems,
					self.inventoryMgr.availableGoldPieces() )
			self.equip( Item.Item.NONE_TYPE, 0 )
			BigWorld.target.caps( Caps.CAP_CAN_USE )
			self.lockRightHandModel( False )

		def doStep3():
			self.actionComplete()

		doStep1()
		self._waitingDrop = False


	def dropDeny( self ):
		'''Server is notifying us that the drop request has been denied.
		'''
		self.actionComplete()
		self.disagree()


	# -------------------------------------------------------------------------
	# Command: Hit the Move Key
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "RightMouseButton" )
	def moveKey( self, isDown ):
		if self.inWoWMode:
			if self.inMouseMove:
				# We're moving the camera with the mouse. React to new button state.
				self._mouseMoveChange( 0, 0 )
			elif isDown:
				self.mouseDown = True
				# Mouse button down. Wait for a move.
				self._cancelMovePlayer()
				self._setupMouseMove()
				self.disableEntityDirCamera()
			else:
				self.mouseDown = False
				if self.isMoving:
					self.enableEntityDirCamera()
				# Mouse button up and we weren't moving the camera. Try to move the player.
				type, target = self.getMouseCollidePos()
				if type == collide.COLLIDE_TERRAIN:
					self._movePlayer( target )
				elif type == collide.COLLIDE_ENTITY:
					self._movePlayer( target.position )
			return


	# -------------------------------------------------------------------------
	# Command: Hit the Use Key
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "LeftMouseButton" )
	def useKey( self, isDown ):
		if self.inWoWMode:
			if self.inMouseMove:
				# We're moving the camera with the mouse. React to new button state.
				self._mouseMoveChange( 0, 0 )
			else:
				# Mouse button up and we weren't moving the camera. Try to move the player.
				type, target = self.getMouseCollidePos()
				if isDown:
					#Mouse down on web screen doesn't do anything (the mouse up will use the web screen)
					if not self.inWebScreenMode() or not isinstance(target, WebScreen) :
						# Mouse button down. Wait for a move.
						self._setupMouseMove()
				else:
					if type == collide.COLLIDE_ENTITY:
						self.onEntityClicked( target )
					else:
						self.onEntityClicked( None )
						#Remove currentWebScreen
						if self.currentWebScreen != None :
							self.removeWebScreenFocus()
			# if we're moving, make sure the EDP is on
			if isDown:
				self.mouseDown = True
				self.disableEntityDirCamera()
				if not self.isPanning or self.isMoving:
					BigWorld.dcursor().yaw = self.yaw
					BigWorld.dcursor().pitch = self.pitch
				self.isPanning = True
			else:
				self.mouseDown = False
				if self.isMoving:
					self.enableEntityDirCamera()
					self.isPanning = True
					BigWorld.dcursor().yaw = self.yaw
					BigWorld.dcursor().pitch = self.pitch
			return

		if isDown:
			if self.mode == Mode.SEATED:
				if not self.doingAction:
					if self.rightHandItem != None and self.rightHand != -1:
						self.rightHandItem.use( self, BigWorld.target() )
					else:
						BigWorld.entity(self.modeTarget).use()

			elif not self.doingAction:
				handled = 0
				if not handled and BigWorld.target() != None and \
					   Caps.CAP_CAN_HIT not in BigWorld.target().targetCaps:
					BigWorld.target().use()
					handled = 1

				#PCWJ - removed 'create new item on use just to check the itemType'
				#because that seems ridiculous to do but why was this in here??
				#and self.rightHandItem.itemType == Item.newItem(self.rightHand).itemType:
				if not handled and self.rightHandItem != None and self.rightHand != -1:
					handled = self.rightHandItem.use( self, BigWorld.target() )
					if handled not in [0,1]:
						print "Warning: No bool from item %d use method" % \
							self.rightHand
						handled = 1

				if not handled and BigWorld.target() != None:
					BigWorld.target().use()
					handled = 1

				if not handled:
					pass

			elif self.doingAction == 1 and self.mode == Mode.COMBAT_CLOSE:
				self.closeCombatSwing()

	def setWebScreenFocus( self, webScreen ):
			self.currentWebScreen = webScreen
			FantasyDemo.rds.inGameFocusedComponent = webScreen
			self.origCursorShape = GUI.mcursor().shape
			GUI.mcursor().shape = 'point'
			self.mode = Mode.WEB_SCREEN
			self.set_mode( Mode.NONE )
			self.actionCommence()
			#show the web controls
			if self.currentWebScreen.isGame():
				FantasyDemo.rds.fdgui.activateWebGameControls(True)
			else:
				FantasyDemo.rds.fdgui.webControls.editField.script.setText(webScreen.url())
				FantasyDemo.rds.fdgui.activateWebControls(True)

	def removeWebScreenFocus( self ):
		FantasyDemo.rds.inGameFocusedComponent = None
		if hasattr(self, 'origCursorShape'):
			GUI.mcursor().shape = self.origCursorShape
		self.currentWebScreen.setFocus(False)
		#Hide the web controls
		if self.currentWebScreen.isGame():
			FantasyDemo.rds.fdgui.activateWebGameControls(False)
		else:
			FantasyDemo.rds.fdgui.activateWebControls(False)
		self.currentWebScreen = None
		self.mode = Mode.NONE
		self.cancelMode( Mode.WEB_SCREEN )
		self.actionComplete()


	def onEntityClicked( self, target ):
		if not self.doingAction:
			if self.rightHandItem != None and self.rightHand != -1:
				self.rightHandItem.use( self, target )
			elif target:
				#Don't change the yaw when clicking on WebScreens as this gives better user experience
				if not hasattr (target, "changeYawWhenUsed") or target.changeYawWhenUsed:
					curr_yaw = (target.position - self.position).yaw
					BigWorld.dcursor().yaw = curr_yaw
				target.use()
		elif self.doingAction == 1 and self.mode == Mode.COMBAT_CLOSE:
			self.closeCombatSwing()
		elif self.doingAction == 1 and self.mode == Mode.WEB_SCREEN:
			if target: 
				target.use()

	# -------------------------------------------------------------------------
	# Command: Use Communipanion
	# -------------------------------------------------------------------------
	def useCommunipanion( self, isDown ):
		if not isDown:
			return
		if self.doingAction == 0 and self.mode == Mode.NONE:
			# Activate Communipanion.
			print "Activating communipanion"
			self.setUsingCurrentItem( 1 )
		elif self.doingAction == 1 and self.mode == Mode.USING_ITEM:
			# Dectivate Communipanion.
			print "Deactivating communipanion"
			self.setUsingCurrentItem( 0 )

	# -------------------------------------------------------------------------
	# Command: Auto move forward
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "AutoMove" )
	def toggleAutoMove( self, isDown):
		if isDown:
			self.autoMove = not self.autoMove
			self._setForwardMagnitude()

	# -------------------------------------------------------------------------
	# Command: Move Forward
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "MoveForward" )
	def moveForward(self, isDown):
		if isDown:
			leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
			rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

			if rightIsDown and not leftIsDown:
				self.moveByStrafe = True
				self.physics.userDirected = True
				self.isMoving = True
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

			self.autoMove = False
			if self.isMovingToDest:
				self._cancelMovePlayer()

			if self.physics.chasing:
				self.physics.stop()

			self._setForwardMagnitude()
			if self.mode == Mode.COMBAT_CLOSE:
				if self.stance == Avatar.STANCE_BACKWARD:
					nst = Avatar.STANCE_NEUTRAL
				else:
					nst = Avatar.STANCE_FORWARD
				self.takeStance( nst )

			if not self.mouseDown:
				self.enableEntityDirCamera()
				self.isPanning = False
			self.isMoving = True
		else:
			self._setForwardMagnitude()
			self.isMoving = False


	def _setForwardMagnitude( self ):
		'''Look at the keys that are down to work out what the forward/backward
		movement should be.
		'''
		leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
		rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

		forwardCount = 1 if self.autoMove else 0
		forwardCount += 1 if (leftIsDown and rightIsDown) else 0

		for keys in self.moveForwardKeys:
			allDown = True
			for key in keys:
				if not BigWorld.isKeyDown( key ):
					allDown = False
			if allDown:
				forwardCount += 1
		for keys in self.moveBackwardKeys:
			allDown = True
			for key in keys:
				if not BigWorld.isKeyDown( key ):
					allDown = False
			if allDown:
				forwardCount -= 1

		if forwardCount > 0:
			self.forwardMagnitude =  1.0
		elif forwardCount < 0:
			self.forwardMagnitude = -1.0
		else:
			self.forwardMagnitude =  0.0


	# -------------------------------------------------------------------------
	# Command: Additional Move Forward, but not when the free camera is on.
	# -------------------------------------------------------------------------
	def conditionalMoveForward(self, isDown):
		if not FantasyDemo.isFreeCamera():
			self.moveForward(isDown)

	# -------------------------------------------------------------------------
	# Command: Move Backward
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "MoveBackward" )
	def moveBackward(self, isDown):
		if isDown:
			leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
			rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

			if rightIsDown and not leftIsDown:
				self.moveByStrafe = True
				self.physics.userDirected = True
				self.isMoving = True
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

			self.autoMove = False
			if self.isMovingToDest:
				self._cancelMovePlayer()

			if self.physics.chasing:
				self.physics.stop()

			self._setForwardMagnitude()
			if self.mode == Mode.COMBAT_CLOSE:
				if self.stance == Avatar.STANCE_FORWARD:
					nst = Avatar.STANCE_NEUTRAL
				else:
					nst = Avatar.STANCE_BACKWARD
				self.takeStance( nst )
		else:
			self._setForwardMagnitude()

	# -------------------------------------------------------------------------
	# Command: Additional Move Back, but not when the free camera is on.
	# -------------------------------------------------------------------------
	def conditionalMoveBackward(self, isDown):
		if not FantasyDemo.isFreeCamera():
			self.moveBackward(isDown)

	# -------------------------------------------------------------------------
	# Command: Move Left
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "TurnLeft" )
	def moveLeft(self, isDown):
		if isDown:
			leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
			rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

			if rightIsDown and not leftIsDown:
				self.moveByStrafe = True
				self.physics.userDirected = True
				self.isMoving = True
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

			if self.isMovingToDest:
				self._cancelMovePlayer()

			if self.physics.chasing:
				self.physics.stop()

			self.rightwardMagnitude = max(self.rightwardMagnitude-1.0,-1.0)

			if self.inWoWMode and not self.moveByStrafe and not leftIsDown:
				self.enableEntityDirCamera()
		else:
			self.rightwardMagnitude = min(self.rightwardMagnitude+1.0,1.0)

	# -------------------------------------------------------------------------
	# Command: Additional Move Left, but not when the free camera is on.
	# -------------------------------------------------------------------------
	def conditionalMoveLeft(self, isDown):
		if not FantasyDemo.isFreeCamera():
			self.moveLeft(isDown)

	# -------------------------------------------------------------------------
	# Command: Move Right
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "TurnRight" )
	def moveRight(self, isDown):
		if isDown:
			leftIsDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
			rightIsDown = BigWorld.isKeyDown( Keys.KEY_RIGHTMOUSE )

			if rightIsDown and not leftIsDown:
				self.moveByStrafe = True
				self.physics.userDirected = True
				self.isMoving = True
				BigWorld.setCursor( BigWorld.dcursor() )
				self._enterMouseMove()

			if self.isMovingToDest:
				self._cancelMovePlayer()

			if self.physics.chasing:
				self.physics.stop()

			self.rightwardMagnitude = min(self.rightwardMagnitude+1.0,1.0)

			if self.inWoWMode and not self.moveByStrafe and not leftIsDown:
				self.enableEntityDirCamera()
		else:
			self.rightwardMagnitude = max(self.rightwardMagnitude-1.0,-1.0)

	# -------------------------------------------------------------------------
	# Command: Additional Move Right, but not when the free camera is on.
	# -------------------------------------------------------------------------
	def conditionalMoveRight(self, isDown):
		if not FantasyDemo.isFreeCamera():
			self.moveRight(isDown)

	# -------------------------------------------------------------------------
	# Command: Jump Up
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "Jump" )
	def jumpUp(self, isDown):
		if isDown:
			if self.isMovingToDest:
				self._cancelMovePlayer()

			self.upwardMagnitude = min(self.upwardMagnitude+1.0,1.0)
		else:
			self.upwardMagnitude = max(self.upwardMagnitude-1.0,-1.0)

	@BWKeyBindingAction( "FlyMode" )
	def toggleFlyMode( self, isDown ):
		if isDown:
			self.flying = 1 - self.flying
			self.physics.fall = 1 - self.flying
			if self.flying:
				FantasyDemo.addChatMsg( -1, "Fly Mode enabled" )
			else:
				FantasyDemo.addChatMsg( -1, "Fly Mode disabed" )

	# -------------------------------------------------------------------------
	# Command: Toggle Running/Walking Mode
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "SwitchToDash" )
	def switchToDash(self, isDown):
		if isDown:
			self.isDashing = 1
		else:
			self.isDashing = 0

	@BWKeyBindingAction( "SwitchToRun" )
	def switchToRun(self, isDown):
		if isDown:
			self.isRunning = 0
		else:
			self.isRunning = 1


	# -------------------------------------------------------------------------
	# Command: Toggle Cell Boundary Visualisation
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "CellBoundaryVisualisation" )
	def toggleCellBoundaryVisualisation(self, isDown=True):
		if isDown:
			self.showCellBoundsModel = not self.showCellBoundsModel
			self.setupCellBoundsModel()

			self.listeners.cellBoundsEnabled( self.showCellBoundsModel )

			if self.showCellBoundsModel:
				FantasyDemo.addChatMsg( -1, "Cell boundary visualisation enabled." )
			else:
				FantasyDemo.addChatMsg( -1, "Cell boundary visualisation disabled." )


	# -------------------------------------------------------------------------
	# Command: Toggle Turbo Movement Mode
	# -------------------------------------------------------------------------
	@BWKeyBindingAction( "TurboMovementMode" )
	def toggleTurboMovementMode(self, isDown):
		if isDown:
			if self.speedMultiplier > 25.0:
				self.speedMultiplier = 1.0
				FantasyDemo.addChatMsg( -1, 'Run Speed: Normal' )
			else:
				self.speedMultiplier = 2.0 * self.speedMultiplier
				FantasyDemo.addChatMsg( -1, 'Run Speed: x%(s)d'%{'s':int(self.speedMultiplier)} )

	# -------------------------------------------------------------------------
	# Command: Changes to Binocular mode on the player.
	# -------------------------------------------------------------------------
	def binocularsMode( self, enable ):
		if enable and self.guiModeSelected != 2:
			self.actionCommence()
			# make the screen look right
			FantasyDemo.handleCameraKey( forceToStandardCamera = True )

			# Change the turning half life to the camera moves into position immediately
			camera = BigWorld.camera()
			turningHalfLife = camera.turningHalfLife
			camera.turningHalfLife = 0.0
			def restoreTurningHalfLife():
				camera.turningHalfLife = turningHalfLife
			BigWorld.callback( 0.1, restoreTurningHalfLife )

			self.guiMode( 2 )

		elif self.guiModeSelected != 0:
			self.actionComplete()
			# make the screen look right
			self.guiMode( 0 )

	def setUsingCurrentItem( self, enable ):
		if enable:
			self.cell.enterMode( Mode.USING_ITEM, Mode.NO_TARGET, 0 )
			omode = self.mode; self.mode = Mode.USING_ITEM
			self.set_mode( omode )
		else:
			self.cell.cancelMode()
			omode = self.mode;	self.mode = Mode.NONE
			self.set_mode( omode )

	# -------------------------------------------------------------------------
	# Command: Toggle Collision Detection
	# -------------------------------------------------------------------------
	def toggleCollisionDetection(self, isDown):
		if isDown:
			self.physics.collide = 1 - self.physics.collide



	@BWKeyBindingAction( "NextPresetModel" )
	def nextPresetModel( self, isDown = True ):
		if isDown:
			newAvatarModel = PlayerModel.nextPresetModel( AvatarModel.unpack( self.avatarModel ) )
			packedNewAvatarModel = AvatarModel.pack( newAvatarModel )
			if self._isConnected():
				self.base.setAvatarModel( packedNewAvatarModel )
			else:
				self.avatarModel = packedNewAvatarModel
				self.set_avatarModel()


	@BWKeyBindingAction( "PreviousPresetModel" )
	def previousPresetModel( self, isDown = True ):
		if isDown:
			newAvatarModel = PlayerModel.previousPresetModel( AvatarModel.unpack( self.avatarModel ) )
			packedNewAvatarModel = AvatarModel.pack( newAvatarModel )
			if self._isConnected():
				self.base.setAvatarModel( packedNewAvatarModel )
			else:
				self.avatarModel = packedNewAvatarModel
				self.set_avatarModel()


	@BWKeyBindingAction( "NewRandomModel" )
	def newRandomModel( self, isDown = True ):
		if isDown:
			newModel = AvatarModel.pack( PlayerModel.randomPlayerModel() )
			if self._isConnected():
				self.base.setAvatarModel( newModel )
			else:
				self.avatarModel = newModel
				self.set_avatarModel()

	@BWKeyBindingAction( "RandomiseModelCustomisations" )
	def randomiseModelCustomisations( self, isDown = True  ):
		if isDown:
			oldModel = AvatarModel.unpack( self.avatarModel )
			newModel = PlayerModel.reCustomisePlayerModel( oldModel )
			if self._isConnected():
				self.base.setAvatarModel( AvatarModel.pack( newModel ) )
			else:
				self.avatarModel = AvatarModel.pack( newModel )
				self.set_avatarModel()


	# -------------------------------------------------------------------------
	# Commands: Switch To Next/Previous Inventory Item
	# -------------------------------------------------------------------------

	@BWKeyBindingAction( "SelectItem" )
	def selectItem( self, isDown, serialNumber ):
		if isDown and not self.doingAction:
			self.inventoryMgr.selectItem( serialNumber )
			self._checkStowAndEquip()

	@BWKeyBindingAction( "NextItem" )
	def nextItem( self, isDown ):
		if isDown and not self.doingAction:
			self.inventoryMgr.selectNextItem( self._filterItem )
			self._checkStowAndEquip()


	@BWKeyBindingAction( "PreviousItem" )
	def previousItem( self, isDown ):
		if isDown and not self.doingAction:
			self.inventoryMgr.selectPreviousItem( self._filterItem )
			self._checkStowAndEquip()


	def _filterItem( self, itemType, itemSerial ):
		'''Do not allow player to select a gun when he is seated
		'''
		return (
				self.mode != Mode.SEATED or
				not Item.lookupItem( itemType ).canShoot )


	def _checkStowAndEquip( self ):
		@IgnoreCallbackIfDestroyed
		def unstowItem( self, stowPlace ):
			if stowPlace == SHOULDER:
				self.stowToShoulderKey( True )
			elif stowPlace == RIGHT_HIP:
				self.stowToRightHipKey( True )
			elif stowPlace == LEFT_HIP:
				self.stowToLeftHipKey( True )

		try:
			itemIndex  = self.inventoryMgr.currentItemIndex()
			itemSerial = self.inventoryMgr.currentItemSerial()
			stowPlace  = self._stowSerial.index( itemSerial )
			self.inventoryMgr.selectItem( Inventory.NOITEM )
			self.equip( Item.Item.NONE_TYPE )
			BigWorld.callback( 0.4, partial( unstowItem, self, stowPlace ) )
		except ValueError:
			self.equip( self.inventoryMgr.currentItem() )

	# -------------------------------------------------------------------------
	# Command: stow items
	# -------------------------------------------------------------------------

	@BWKeyBindingAction( "StowToShoulder" )
	def stowToShoulderKey( self, isDown ):
		if self._stowItem( isDown, self.rightHand, self.shoulder, 'shoulder' ):
			if hasattr(self.model, "right_hand"):
				self.model.right_hand = None
			self.shoulder = self.rightHand
			self.cell.setShoulder( self.shoulder )
			self.set_shoulder()
			self._stowUpdateInventory( SHOULDER )


	@BWKeyBindingAction( "StowToRightHip" )
	def stowToRightHipKey( self, isDown ):
		if self._stowItem( isDown, self.rightHand, self.rightHip, 'right_hip' ):
			if hasattr(self.model, "right_hand"):
				self.model.right_hand = None
			self.rightHip = self.rightHand
			self.cell.setRightHip( self.rightHip )
			self.set_rightHip()
			self._stowUpdateInventory( RIGHT_HIP )


	@BWKeyBindingAction( "StowToLeftHip" )
	def stowToLeftHipKey( self, isDown ):
		if self._stowItem( isDown, self.rightHand, self.leftHip, 'left_hip' ):
			if hasattr(self.model, "right_hand"):
				self.model.right_hand = None
			self.leftHip = self.rightHand
			self.cell.setLeftHip( self.leftHip )
			self.set_leftHip()
			self._stowUpdateInventory( LEFT_HIP )


	def _stowItem( self, isDown, rightHandItem, stowedItem, hardPoint ):
		if not isDown or self.doingAction:# or self.inCombat():
			return False

		# refuse if item can't be stowed
		if rightHandItem != Item.Item.NONE_TYPE:
			try:
				self.getItem( rightHandItem ).model.node( 'HP_%s' % hardPoint )
			except ValueError:
				print 'Item model does not have hardpoint: HP_%s' % hardPoint
				return False

		# refuse if neighter the right hand nor the
		# stow place is vacant. Or if both are vacant
		holdingItem = rightHandItem != Item.Item.NONE_TYPE
		hasItemInSholder = stowedItem != Item.Item.NONE_TYPE
		if holdingItem == hasItemInSholder:
			return False

		return True


	def _stowUpdateInventory( self, stowPlace ):
		assert stowPlace in STOW_PLACES

		# equip old shoulder item
		oldSerial = self._stowSerial[ stowPlace ]
		try:
			self._stowSerial[ stowPlace ] = self.inventoryMgr.currentItemSerial()
		except ValueError:
			self._stowSerial[ stowPlace ] = Item.Item.NONE_TYPE

		itemType = self.inventoryMgr.selectItem( oldSerial )
		self.equip( itemType, 0 )

		# udpate inventory GUI
		itemIndex = self.inventoryMgr.currentItemIndex()

	# -------------------------------------------------------------------------
	# Command: input event handling
	# -------------------------------------------------------------------------

	def handleMouseEvent( self, event ):
		if self.inWoWMode:
			if self.onMouseMove:
				self.onMouseMove( event.dx, event.dy )
			if self.currentWebScreen != None:
				if self.currentWebScreen.handleMouseMove( event ):
					return True
			return 1
		return 0


	def handleKeyEvent( self, event ):
		if not self.inWorld or event.isRepeatedEvent():
			return False

		# If player is on a vehicle, redirect desired input to vehicle.
		if self.vehicle != None and hasattr( self.vehicle, 'handleKeyEvent' ):
			if self.vehicle.handleKeyEvent( event ):
				return True

		# Check key state against key bindings.
		FantasyDemo.rds.keyBindings.callActionForKeyState( event.key )


		# Update our velocity unless we've been dePlayerised
		# If we're not a PlayerAvatar anymore, the player either pressed
		# a key which yielded control to the server, or we were offline
		# and just reset the entityManager.
		if hasattr( self, "updateVelocity" ):
			self.updateVelocity()

		return False

	def setUpMovementSpeedsFromModel( self ):
		"""
		Set up our movement speeds from the animations.
		In future, we may not want to do this for gameplay reasons,
		but for now it looks best when played at the right speed.
		"""

		self.walkFwdSpeed = 1.0
		self.runFwdSpeed = 2.0
		self.dashFwdSpeed = 2.5
		try:
			self.walkFwdSpeed = self.model.WalkForward.displacement[2] / \
				self.model.WalkForward.duration
			self.runFwdSpeed = self.model.RunForward.displacement[2] / \
				self.model.RunForward.duration
			self.dashFwdSpeed = self.model.DashForward.displacement[2] / \
				self.model.DashForward.duration
		except:
			pass

		self.walkBackSpeed = 1.0
		self.runBackSpeed = 2.0
		self.dashBackSpeed = 2.5
		try:
			self.walkBackSpeed = - self.model.WalkBackward.displacement[2] / \
				(self.model.WalkBackward.duration * 1.5)
			self.runBackSpeed = - self.model.RunBackward.displacement[2] / \
				(self.model.RunBackward.duration * 1.5)
			self.dashBackSpeed = - self.model.RunBackward.displacement[2] / \
				(self.model.RunBackward.duration * 1.5)
		except:
			pass

		# Store our full movement rates.
		self.fullWalkFwdSpeed = self.walkFwdSpeed
		self.fullRunFwdSpeed = self.runFwdSpeed
		self.fullDashFwdSpeed = self.dashFwdSpeed
		self.fullWalkBackSpeed = self.walkBackSpeed
		self.fullRunBackSpeed = self.runBackSpeed
		self.fullDashBackSpeed = self.dashBackSpeed

		# Set up our tired movement rates.
		self.tiredWalkFwdSpeed = self.walkFwdSpeed
		self.tiredRunFwdSpeed = self.runFwdSpeed
		self.tiredDashFwdSpeed = self.runFwdSpeed
		self.tiredWalkBackSpeed = self.walkBackSpeed
		self.tiredRunBackSpeed = self.runBackSpeed
		self.tiredDashBackSpeed = self.runBackSpeed


	# Update the velocity set in our physics controller
	def updateVelocity( self ):

		seeking = False
		if hasattr(self, 'physics') and self.physics.seeking == 1:
			seeking = True

		# If we're chasing only allow strafing left and right
		if self.physics.chasing:
			#self.physics.velocity = ( self.rightwardMagnitude, 0, 1.5 )
			self.physics.velocity = ( 0, 0, 1.5 )
			return

		# Find out how fast we can go
		if self.isDashing:
			if self.forwardMagnitude >= 0:
				multiplier = self.dashFwdSpeed
			else:
				multiplier = self.dashBackSpeed
		elif self.isRunning:
			if self.forwardMagnitude >= 0:
				multiplier = self.runFwdSpeed
			else:
				multiplier = self.runBackSpeed
		else:
			if self.forwardMagnitude >= 0:
				multiplier = self.walkFwdSpeed
			else:
				multiplier = self.walkBackSpeed

		# The two magnitude values, forwardMagnitude and leftwardMagnitude
		# should lie between 0.0 and 1.0. The vector sum of their values
		# should also lie between 0.0 and 1.0.
		rightwardMagnitude = max(self.rightwardMagnitude,-1.0)
		rightwardMagnitude = min(rightwardMagnitude,1.0)
		forwardMagnitude = max(self.forwardMagnitude,-1.0)
		forwardMagnitude = min(forwardMagnitude,1.0)
		upwardMagnitude = self.upwardMagnitude
		hypotenuse = math.sqrt( forwardMagnitude * forwardMagnitude +
			rightwardMagnitude * rightwardMagnitude )
		if hypotenuse > 1.0:
			forwardMagnitude /= hypotenuse
			rightwardMagnitude /= hypotenuse

		# Check if the Entity should temporarily discount movement. Currently
		# movement should be disabled for gestures and first-person mode.
		if (self.doingAction and self.doingMovableAction < self.doingAction) or \
				self.mode == Mode.SEATED:
				#self.firstPerson or self.mode == Mode.SEATED:
			forwardMagnitude = 0.0
			rightwardMagnitude = 0.0
			upwardMagnitude = 0.0

			# cancel seeking
			if seeking:
				self.physics.seek( None, 0, 0, None )
				seeking = False

		if seeking:
			return

		turnMultiplier = multiplier * min( self.speedMultiplier, 8.0 )
		multiplier = multiplier * self.speedMultiplier

		self.physics.brake = 0

		if self.inWoWMode and not self.moveByStrafe:
			self.physics.angular = rightwardMagnitude * turnMultiplier / 3.0
			self.physics.velocity = ( 0,
				upwardMagnitude * multiplier,
				forwardMagnitude * multiplier )
		else:
			self.physics.velocity = (
				rightwardMagnitude * multiplier,
				upwardMagnitude * multiplier,
				forwardMagnitude * multiplier )

		if self.flying or upwardMagnitude > 0:
			self.physics.fall = 0
		else:
			#prevent failling if a fly through is running. We want fly through
			#to be flying all the time (to prevent falling into water)
			if not BigWorld.flyThroughRunning():
				self.physics.fall = 1

		# Set joystick velocity override parameters
		if (self.doingMovableAction or not self.doingAction) and \
				self.mode != Mode.SEATED:
				#(not self.firstPerson) and self.mode != Mode.SEATED:

			#AUSTIN GDC - move all matchCaps into items
			#if 6 in self.am.matchCaps:
			#	jspeeds = ( self.runFwdSpeed, self.sneakBackSpeed,
			#				self.dashFwdSpeed, self.sneakBackSpeed )
			#elif 7 in self.am.matchCaps:
			#	jspeeds = ( self.crouchFwdSpeed, self.crouchBackSpeed,
			#				self.crouchFwdSpeed, self.crouchBackSpeed )
			#elif 3 in self.am.matchCaps:
			#	jspeeds = ( self.runFwdSpeed, self.runBackSpeed,
			#				self.runFwdSpeed, self.runBackSpeed )
			#else:
			jspeeds = ( self.runFwdSpeed, self.runBackSpeed,
						self.dashFwdSpeed, self.dashBackSpeed )
		else:
			jspeeds = ( 0, 0, 0, 0 )

		if not self.isDashing:
			self.physics.joystickFwdSpeed = jspeeds[0]
			self.physics.joystickBackSpeed = jspeeds[1]
		else:
			self.physics.joystickFwdSpeed = jspeeds[2]
			self.physics.joystickBackSpeed = jspeeds[3]


	@BWKeyBindingAction( "Gesture00",  0 )
	@BWKeyBindingAction( "Gesture01",  1 )
	@BWKeyBindingAction( "Gesture02",  2 )
	@BWKeyBindingAction( "Gesture03",  3 )
	@BWKeyBindingAction( "Gesture04",  4 )
	@BWKeyBindingAction( "Gesture05",  5 )
	@BWKeyBindingAction( "Gesture06",  6 )
	@BWKeyBindingAction( "Gesture07",  7 )
	@BWKeyBindingAction( "Gesture08",  8 )
	@BWKeyBindingAction( "Gesture09",  9 )
	@BWKeyBindingAction( "Gesture10", 10 )
	@BWKeyBindingAction( "Gesture11", 11 )
	@BWKeyBindingAction( "Gesture12", 12 )
	@BWKeyBindingAction( "Gesture13", 13 )
	@BWKeyBindingAction( "Gesture14", 14 )
	@BWKeyBindingAction( "Gesture15", 15 )
	@BWKeyBindingAction( "Gesture16", 16 )
	@BWKeyBindingAction( "Gesture17", 17 )
	@BWKeyBindingAction( "Gesture18", 18 )
	@BWKeyBindingAction( "Gesture19", 19 )
	@BWKeyBindingAction( "Gesture20", 20 )
	@BWKeyBindingAction( "Gesture21", 21 )
	@BWKeyBindingAction( "Gesture22", 22 )
	@BWKeyBindingAction( "Gesture23", 23 )
	@BWKeyBindingAction( "Gesture24", 24 )
	@BWKeyBindingAction( "Gesture25", 25 )
	@BWKeyBindingAction( "Gesture26", 26 )
	@BWKeyBindingAction( "Gesture27", 27 )
	@BWKeyBindingAction( "Gesture28", 28 )
	@BWKeyBindingAction( "Gesture29", 29 )
	@BWKeyBindingAction( "Gesture30", 30 )
	@BWKeyBindingAction( "Gesture31", 31 )
	@BWKeyBindingAction( "Gesture32", 32 )
	@BWKeyBindingAction( "Gesture33", 33 )
	@BWKeyBindingAction( "Gesture34", 34 )
	@BWKeyBindingAction( "Gesture35", 35 )
	@BWKeyBindingAction( "Gesture36", 36 )
	@BWKeyBindingAction( "Gesture37", 37 )
	@BWKeyBindingAction( "Gesture38", 38 )
	@BWKeyBindingAction( "Gesture39", 39 )
	@BWKeyBindingAction( "Gesture40", 40 )
	@BWKeyBindingAction( "Gesture41", 41 )
	@BWKeyBindingAction( "Gesture42", 42 )
	@BWKeyBindingAction( "Gesture43", 43 )
	@BWKeyBindingAction( "Gesture44", 44 )
	@BWKeyBindingAction( "Gesture45", 45 )
	def playGesture( self, action, isDown = True ):
		if not isDown:
			return

		# If the Player is seated, allow only gestures that can be done while
		# moving. That is, only allow gestures that have an alpha blended
		# portion for the lower body.
		if self.mode == Mode.SEATED:
			if not self.gestureActions[action].canMove:
				return

		if not self.doingAction:
			self.actionCommence()

			# pretend the server told us about it
			self.didGesture( action )
			# and tell the server about it
			self.cell.didGesture( action )


	def didGesture( self, actionID ):
		if self.gestureActions[actionID].canMove:
			self.doingMovableAction += 1

		if not self.gestureActions[actionID].canHoldItem and \
				self.rightHand != Item.Item.NONE_TYPE:

			if not self.inCombat():	# check, for safety
				self.unequipItem()

			BigWorld.callback( 0.5,
				partial( Avatar.didGesture, self, actionID ) )
		else:
			Avatar.didGesture( self, actionID )

	#
	# PlayerAvatar C++ Interface Note:
	# The identifier 'model' refers to the C++ Python Object Model.
	#
	# Hard points for a model can be accessed as if they were a normal variable
	# of type 'Model'. That is, a hard point may be set to a 'Model' object by
	# direct assignment.
	#
	# eg. self.model.right_hand = "objects/models/gun.model" will attach the gun
	#     model to the model's right hand.
	#
	# Sample HardPoint Names:
	#     right_hand, left_hand, shoulder, right_hip
	#
	# The model can be told to do an action (ie. animation) by specifying the
	# action name as listed in the XML file. This is the name listed by the
	# tag <name>.
	#
	# eg1. self.model.Idle() will cause the model to play the
	#      Idle action's animation immediately without a call-back function.
	#
	# eg2. self.model.BendDown( 0, callBackIdle ) will cause the
	#      BendDown action's animation to be played immediately, specifying
	#      callBackIdle() to be called upon completion of the animation.
	#

	# The identifier 'filter' refers to the type of filtering used for the
	# Entity's movement.

	def unequipItem( self ):
		item = self.inventoryMgr.selectItem( -1 )
		self.equip( item )


	def equip( self, itemType, itemChangeAnim = 1 ):
		if self.rightHand == itemType:
			return

		self.rightHand = itemType          # change localy
		self.cell.setRightHand( itemType ) # tell the world
		self.set_rightHand( itemChangeAnim = itemChangeAnim )



	def setCombatStance( self ):
		self.listeners.combatStanceUpdated( self.inCombat() )
		if self.inCombat():
			# change to combat

			# set target caps to type of combat
			if self.inMeleeCombat():
				# set the entity target picker to choose things we can melee attack
				BigWorld.target.caps( Caps.CAP_CAN_MELEE )
			else:
				# set the entity target picker to choose things we can shoot at
				BigWorld.target.caps( Caps.CAP_CAN_HIT )
				self.cell.enterCombat()

			# if we are targeting something, call focus target to update the reticle.
			if BigWorld.target() != None:
				self.targetFocus( BigWorld.target() )

		else:
			self.set_rightHand( itemChangeAnim = 0 )

			# tell server (and thus all other clients) we have changed mode
			if not self.inMeleeCombat():
				self.cell.leaveCombat()

	# Target focus notifier
	def targetFocus( self, entity ):
		if self.tracker.directionProvider == None:
			return
		if not BigWorld.target.isFull:
			return # doesn't fully match the right target.caps

		FantasyDemo.rds.fdgui.targetFocus( entity )

		if self.inCombat():
			self.enableTracker( self.gunAimingNodeInfo )
		else:
			self.enableTracker( self.headNodeInfo )
		try:
			self.tracker.directionProvider = BigWorld.DiffDirProvider(
					self.focalMatrix, entity.focalMatrix )
		except:
			self.tracker.directionProvider = BigWorld.DiffDirProvider(
					self.focalMatrix, entity.model.matrix )


	# Target blur notifier
	def targetBlur( self, entity ):
		FantasyDemo.rds.fdgui.targetBlur( entity )

		if self.tracker.directionProvider == None:
			return

		if not self.doingAction:
			self.enableTracker( self.headNodeInfo )

		if self.mode != Mode.DEAD:
			self.tracker.directionProvider = self.entityDirProvider


	# Handle a console command
	def handleConsoleCommand( self, command, theRest = "" ):
		lcommand = command.lower()
		candidates = [ x for x in ConsoleCommands.__dict__.keys() \
						if x.lower().startswith( lcommand ) ]
		#lcommand = unicode( command.lower() )
		#candidates = [ unicode(x) for x in ConsoleCommands.__dict__.keys() \
		#				if unicode(x).lower().startswith( lcommand ) ]

		if len(candidates) > 1:
			exactCandidates = [ x for x in candidates if x.lower() == lcommand ]
			if len(exactCandidates) >= 1:
				candidates = exactCandidates
				if len(candidates) > 1:
					exactCaseCandidates = [ x for x in candidates \
											if x == command ]
					if len(exactCaseCandidates) == 1:
						candidates = exactCaseCandidates

		if len(candidates) == 1:
			getattr( ConsoleCommands, candidates[0] )( self, theRest )
		elif len(candidates) > 1:
			FantasyDemo.addChatMsg( -1, "Ambiguous command '/" + command + \
									"' matches " + str(candidates) )
		else:
			FantasyDemo.addChatMsg( -1, "Unknown command '/" + command + "'" )

	# Handle this string typed at the console
	def handleConsoleInput( self, string ):
		if len(string) > 0 and string[0] == '/':
			FantasyDemo.addChatMsg( -1, string )
			self.handleConsoleCommand( *(string[1:].split( ' ', 1 )) )
		else:
			self.cell.chat( unicode(string) )
			FantasyDemo.addChatMsg( self.id, string )

	# The user wants to invite someone to the group
	@BWKeyBindingAction( "InviteToGroup" )
	def inviteToGroupKey( self, isDown ):
		if isDown:
			t = BigWorld.target()
			if t == None:
				print "PlayerAvatar::inviteToGroup: Invite who?"
				return

			print "Inviting %s to join my group" % (t.playerName, )
			self.base.inviteToGroup( t.id )

	# The user wants to leave its current group
	@BWKeyBindingAction( "LeaveGroup" )
	def leaveGroupKey( self, isDown ):
		if isDown:
			self.base.leaveGroup()

	# The user wants to shonk
	@BWKeyBindingAction( "ShonkPaper", 0 )
	@BWKeyBindingAction( "ShonkScissors", 1 )
	@BWKeyBindingAction( "ShonkRock", 2 )
	def shonkKey( self, which, isDown = True ):
		if not isDown: return
		if self.doingAction or self.inCombat(): return
		if self.mode == Mode.SEATED: return

		t = BigWorld.target()
		if t == None:
			print "PlayerAvatar::shonkKey: Shonk with who?"
			return

		if not Caps.CAP_CAN_SHONK in t.targetCaps:
			print "PlayerAvatar::shonkKey: not Shonkable"
			return

		# ok, is t already waiting to shonk with us?
		if t.mode == Mode.SHONK and t.modeTarget == self.id:
			self.moveActionCommence()

				# should use some other calc here
			self.physics.seek( t.model.Shake_B_Accept.seekInv, 5.0,
				0.30, partial( self.shonkFound, t, which ) )
			self.physics.velocity = (0,0,self.walkFwdSpeed)
		else:
			# tell the server we want to do this
			self.cell.enterMode( 0, BigWorld.target().id, which )


			# just wait for its reply for now, but should
			#  enter the mode here ourselves anyway, like this:
			# self.mode = Mode.SHONK
			# self.set_mode( Mode.NONE )

	def shonkFound( self, t, which, success ):
		# did we make it?
		if not success:
			self.model.Shrug( 0, self.actionComplete )
			return

		# yay we're there!
		t.cell.answerMode( Mode.SHONK, self.id, which )
		# could do something before server reply here too...


	# The user wants to crouch
	@BWKeyBindingAction( "Crouch" )
	def crouchKey( self, isDown = 1 ):
		if not isDown: return

		if self.mode == Mode.CROUCH:
			self.cell.cancelMode()
			self.mode = Mode.NONE
			self.set_mode( Mode.CROUCH )
		elif self.mode == Mode.NONE and not self.doingAction:
			self.cell.enterMode( Mode.CROUCH, Mode.NO_TARGET, 0 )
			self.mode = Mode.CROUCH
			self.set_mode( Mode.NONE )

		# else do nothing...

	# The user wants to shake hands with someone
	@BWKeyBindingAction( "Handshake" )
	def handshakeKey( self, isDown = 1 ):
		if not isDown: return
		if self.doingAction or self.inCombat(): return
		if self.mode == Mode.SEATED: return

		newMode = Mode.HANDSHAKE

		t = BigWorld.target()
		if t == None:
			print "PlayerAvatar::handshakeKey: Shake hands with who?"
			return

		# ok, is t already waiting to shake hands with us?
		if t.mode == Mode.HANDSHAKE and t.modeTarget == self.id:
			# Has the target started its idle loop yet?
			#~ if not t.inIdle:
				#~ return

			self.moveActionCommence()

			self.physics.seek( t.model.Shake_B_Accept.seekInv, 5.0,
				0.10, partial( self.handshakeFound, t ) )
			self.physics.velocity = (0,0,self.walkFwdSpeed)
		else:
			# tell the server we want to do this
			self.cell.enterMode( newMode, BigWorld.target().id, 0 )

			# just wait for its reply for now, but should
			#  enter the mode here ourselves anyway, like this:
			# self.mode = newMode
			# self.set_mode( Mode.NONE )

	def handshakeFound( self, t, success ):
		# did we make it?
		if not success or not t.mode == Mode.HANDSHAKE:
			self.model.Shrug( 0, self.actionComplete )
			return

		# yay we're there!
		t.cell.answerMode( t.mode, self.id, 0 )


	# The user wants to lift someone up
	@BWKeyBindingAction( "PullUp" )
	def pullUpKey( self, isDown = 1 ):
		if not isDown: return
		if self.doingAction or self.inCombat(): return
		if self.mode == Mode.SEATED: return

		if self.rightHand != Item.Item.NONE_TYPE:
			self.unequipItem()

		t = BigWorld.target()
		if t == None:
			print "PlayerAvatar::pullUpKey: Pull up who?"
			return

		# ok, is t already waiting to lift us up?
		if t.mode == Mode.PULLUP and t.modeTarget == self.id:
			self.pullUpPassive( t )
		else:
			#try:
				sofa = self.pullUpActive( t )
				if sofa and sofa < 0:
					print "pullUp: Got to step ", -sofa
			#except Exception, e
			#	print "pullUp: Got to an exception: ", e


	# This function may throw an exception if all is not right
	def pullUpActive( self, t ):
		# OK, see if we can do a pull up from here...
		FDP = BigWorld.findDropPoint
		bumpy = 0.2		# must be < 20cm difference

		# first find the triangle underneath us
		dir = Vector3( math.sin(self.yaw), 0, math.cos(self.yaw) )

		(rfall,rtri) = FDP( self.spaceID, Vector3(self.position) + Vector3(0,2,0) )

		# now while we haven't gone too far
		distOver = 0
		loopCount = 0
		while distOver < 1.5 and loopCount < 10:

			# find the point we want to jump from
			(edge, edgeYaw) = intersectRayWithPolygon( rfall, dir, rtri )

			# peek just over the edge to see if there's an adjoining polygon
			justOver = edge + dir.scale(0.05) + Vector3(0,2,0)
			(nrfall,nrtri) = FDP( self.spaceID, justOver )

			if abs( nrfall.y - edge.y ) > bumpy:
				break	# there isn't, this looks good then

			# ok, there is, try that then
			justOver.y = rfall.y
			distOver += (rfall - justOver).length

			rfall = nrfall
			rtri = nrtri

			loopCount += 1

		edgeup = Vector3( edge.x, edge.y + 2.0, edge.z )
		edgeunder = Vector3( edge.x, edge.y - 1.1, edge.z )
		topH = rfall.y
		botH = rfall.y - 5.0

		# is there space 1.9m behind the edge?
		if abs( FDP( self.spaceID, edgeup - dir.scale(1.9) )[0].y - topH ) > bumpy: return -1

		# is there space 1m behind the edge?
		if abs( FDP( self.spaceID, edgeup - dir )[0].y - topH ) > bumpy: return -2

		# is there space 10cm behind the edge?
		if abs( FDP( self.spaceID, edgeup - dir.scale(0.1) )[0].y - topH ) > bumpy: return -3

		# is there space 10cm over the edge?
		if abs( FDP( self.spaceID, edgeup + dir.scale(0.1) )[0].y - botH ) > bumpy: return -4

		# is there space 90cm over the edge?
		if abs( FDP( self.spaceID, edgeup + dir.scale(0.9) )[0].y - botH ) > bumpy: return -5

		# is there space 10cm under the edge?
		if abs( FDP( self.spaceID, edgeunder - dir.scale(0.1) )[0].y - botH ) > bumpy: return -6

		# is there space 90cm under the edge?
		if FDP( self.spaceID, edgeunder - dir.scale(0.9) )[0].y > topH - 1.0: return -7

		# ok, that'll have to do then.
		self.moveActionCommence()
		stdist = self.model.PullUpActiveBegin.displacement[2] - 1.80;
		self.physics.seek( tuple( (edge - dir.scale(stdist)).list() + [ edgeYaw ] ),
			5.0, 0.10, partial( self.pullUpActiveFound, t) )
		self.physics.velocity = (0,0,self.walkFwdSpeed)

		# tell the server we want to do it


	def pullUpActiveFound( self, t, success ):
		if not success:
			self.model.Shrug( 0, self.actionComplete )
		else:
			self.cell.enterMode( Mode.PULLUP, t.id, 0 )


	def pullUpPassive( self, t ):
		self.moveActionCommence()

		self.physics.seek( t.model.PullUpActiveBegin.seek,
			5.0, 0.10, partial( self.pullUpPassiveFound, t ) )
		self.physics.velocity = (0,0,self.walkFwdSpeed)


	def pullUpPassiveFound( self, t, success ):
		# did we make it?
		if not success:
			self.model.Shrug( 0, self.actionComplete )
			return

		# yay we're there!
		self.am.matcherCoupled = 0
		#BigWorld.callback( 1.0, partial( t.cell.answerMode,
		#	Mode.PULLUP, self.id, 0 ) )
		t.cell.answerMode( Mode.PULLUP, self.id, 0 )


	# The user wants to bunk someone up
	@BWKeyBindingAction( "PushUp" )
	def pushUpKey( self, isDown = 1 ):
		if not isDown: return
		if self.doingAction or self.inCombat(): return
		if self.mode == Mode.SEATED: return

		if self.rightHand != Item.Item.NONE_TYPE:
			self.unequipItem()

		t = BigWorld.target()
		if t == None:
			print "PlayerAvatar::pushUpKey: Push up who?"
			return

		# ok, is t already waiting to lift us up?
		if t.mode == Mode.PUSHUP and t.modeTarget == self.id:
			self.pushUpPassive( t )
		else:
			#try:
				sofa = self.pushUpActive( t )
				if sofa and sofa < 0:
					print "pushUp: Got to step ", -sofa
			#except Exception, e
			#	print "pullUp: Got to an exception: ", e


	# This function may throw an exception if all is not right
	def pushUpActive( self, t ):
		# OK, see if we can do a pull up from here...
		FDP = BigWorld.findDropPoint
		bumpy = 0.2		# must be < 20cm difference

		# first find the triangle above us
		dir = Vector3( math.sin(self.yaw), 0, math.cos(self.yaw) )

		distBack = 1.5
		loopCount = 0

		droppt = Vector3( self.position ) - dir.scale(distBack) + Vector3(0,7,0)
		(rfall,rtri) = FDP( self.spaceID, droppt )

		# now while we're not too close to the player...
		while distBack > 0.3 and loopCount < 10:

			# find the point we want to grab onto
			(edge, edgeYaw) = intersectRayWithPolygon( rfall, dir, rtri )

			# peek just over the edge to see if there's an adjoining polygon
			justOver = edge + dir.scale(0.05)
			justOver.y += 2.0
			(nrfall,nrtri) = FDP( self.spaceID, justOver )

			if abs( nrfall.y - edge.y ) > bumpy:
				break	# there isn't, this looks good then

			# ok, there is, try that then
			justOver.y = rfall.y
			distBack -= (rfall - justOver).length

			rfall = nrfall
			rtri = nrtri

			loopCount += 1

		edgeup = edge + Vector3( 0, 2.0, 0 )
		edgeunder = edge + Vector3( 0, -1.1, 0 )
		topH = rfall.y
		botH = rfall.y - 5.0

		# is there space 0.9m behind the edge?
		if abs( FDP( self.spaceID, edgeup - dir.scale(0.9) )[0].y - topH ) > bumpy: return -2

		# is there space 10cm behind the edge?
		if abs( FDP( self.spaceID, edgeup - dir.scale(0.1) )[0].y - topH ) > bumpy: return -3

		# is there space 10cm over the edge?
		if abs( FDP( self.spaceID, edgeup + dir.scale(0.1) )[0].y - botH ) > bumpy: return -4

		# is there space 90cm over the edge?
		if abs( FDP( self.spaceID, edgeup + dir.scale(0.9) )[0].y - botH ) > bumpy: return -5

		# is there space 10cm under the edge?
		if abs( FDP( self.spaceID, edgeunder - dir.scale(0.1) )[0].y - botH ) > bumpy: return -6

		# is there space 90cm under the edge?
		if FDP( self.spaceID, edgeunder - dir.scale(0.9) )[0].y > topH - 1.0: return -7

		# ok, that'll have to do then.
		self.moveActionCommence()
		stdist = self.model.PushUpPassiveAccept.displacement[2] - \
			self.model.PushUpActiveBegin.displacement[2] + 0.09;
		tgtpos = Vector3(edge.x, edge.y - 5, edge.z) + dir.scale(stdist)

		print "edge ", edge, ", stdist ", stdist, ", tgtpos ", tgtpos
		self.physics.seek( tuple( tgtpos.list() + [ edgeYaw ] ),
			5.0, 0.10, partial( self.pushUpActiveFound, t) )
		self.physics.velocity = (0,0,self.walkFwdSpeed)


	def pushUpActiveFound( self, t, success ):
		if not success:
			self.model.Shrug( 0, self.actionComplete )
		else:
			self.cell.enterMode( Mode.PUSHUP, t.id, 0 )


	def pushUpPassive( self, t ):
		self.moveActionCommence()

		self.physics.seek( t.model.PushUpActiveBegin.seek,
			5.0, 0.10, partial( self.pushUpPassiveFound, t ) )

		self.physics.velocity = (0,0,self.walkFwdSpeed)


	def pushUpPassiveFound( self, t, success ):
		# did we make it?
		if not success:
			self.model.Shrug( 0, self.actionComplete )
			return
		self.am.matcherCoupled = 0
		# yay we're there!
		#BigWorld.callback( 1.0, partial( t.cell.answerMode,
		#	Mode.PUSHUP, self.id, 0 ) )
		t.cell.answerMode( Mode.PUSHUP, self.id, 0 )


	# Override from Avatar
	def assail( self ):
		# We don't call Avatar's assail method, because we've already
		# swung the sword. We only get here if the swing didn't
		# begin combat. So we just call actionComplete
		self.actionComplete()

	CLOSE_COMBAT_DISTANCE = 1.5

	# Override from Avatar
	def enterCloseCombatMode( self ):
		Avatar.enterCloseCombatMode( self )

		# We may be in close combat mode but the fight doesn't start
		#  until the server says so (by sending the first packet)
		self.ccPlayerFighting = 0

		self.ccDefence = 100

		if self.ccTarget == None: return

		print "Player now chasing", self.ccTarget.name(), \
			"(id %d)" % self.ccTarget.id
		self.physics.chase( self.ccTarget, PlayerAvatar.CLOSE_COMBAT_DISTANCE, 0.05 )
		self.physics.userDirected = 0
		self.updateVelocity()


	# Override from Avatar
	def leaveCloseCombatMode( self ):
		self.physics.chase( None, 0 )
		self.physics.userDirected = 1
		self.updateVelocity()

		print "Player no longer chasing anyone"

		Avatar.leaveCloseCombatMode( self )


	# Override from Avatar:
	def closeCombatGo( self, assailant, weAreInitiator ):
		if not hasattr( self, "ccPlayerFighting" ): return

		Avatar.closeCombatGo( self, assailant, weAreInitiator )

		if not self.ccPlayerFighting and self.ccTarget:
			#~ BigWorld.targetLockOn( self.ccTarget )
			self.ccPlayerFighting = 1

		self.physics.chase( None, 0 )
		self.updateVelocity()

	#Override from Avatar:
	def closeCombatNo( self, assailant, weAreInitiator ):
		if not hasattr( self, "ccPlayerFighting" ): return

		if self.ccPlayerFighting:
			#~ BigWorld.targetLockOn( None )
			self.ccPlayerFighting = 0

			BigWorld.callback( 2.5, partial( self.closeCombatAutoExit, assailant ) )

		Avatar.closeCombatNo( self, assailant, weAreInitiator )

		# Consider putting the chase back in here ... sort all this
		# out when multiple opponents are done

	# This is a very tentative function to exit CC mode if there
	# is no longer any reson for us to be in it: i.e. our opponent
	# has broken or died
	@IgnoreCallbackIfDestroyed
	def closeCombatAutoExit( self, assailant ):
		# see if we're still fighting the same entity
		if self.mode != Mode.COMBAT_CLOSE: return
		if self.modeTarget != assailant.id: return

		# make sure they're not still fighting us
		if assailant.mode == Mode.COMBAT_CLOSE and \
			assailant.modeTarget == self.id: return

		# ok, let's get out of it then
		self.cell.cancelMode()



	#Override from Avatar:
	def ccPassiveAction( self, res ):
		defMove = res & 7
		if defMove == Avatar.CL_DESPERATE:
			self.ccDefence -= 10
		elif defMove == Avatar.CL_HIT:
			self.ccDefence -= 10
		if self.ccDefence < 0: self.ccDefence = 0
		return Avatar.ccPassiveAction( self, res )

	# This method is called when the player is attacked by another entity
	def ccRespond( self, oth ):
		print "Responding to the attack of ", oth.id, "..."
		self.ccLastAttacker = None

		# Ignore it if we're already doing something
		if self.mode != Mode.NONE or self.doingAction != 0:
			if self.mode == Mode.COMBAT_CLOSE and self.modeTarget == oth.id:
				print "... already attacking this entity"
			else:
				print "... doing something else"
				# Remember our attacker and try again later
				self.ccLastAttacker = oth
			return

		# Change to the sword if we have one
		tempRH = self.getItem( self.rightHand )
		if not tempRH or not tempRH.canSwing:
			def isWield( item ):
				return Item.lookupItem( item )[0] == Item.Wield
			if self.inventoryMgr.selectSuitableItem( isWield ):
				self.equip( self.inventoryMgr.currentItem(), 0 )
			else:
				print "... no Wield item found in inventory"
				return

		# Find out where they are
		dir = Vector3( self.position ) - Vector3( oth.position )
		if dir.lengthSquared > 0.01: dir.normalise()
		else: dir = Vector3(0,0,1)
		pos = Vector3( oth.position ) + dir.scale( PlayerAvatar.CLOSE_COMBAT_DISTANCE )
		yaw = math.atan2( dir.x, dir.z )

		# Come after this challenger!
		self.moveActionCommence()

		self.physics.seek( (pos.x,pos.y,pos.z,yaw+math.pi), 5.0, 1.0,
			partial( self.ccRespondOver, oth ) )
		self.physics.velocity = (0,0,self.runFwdSpeed)
		self.updateVelocity()

	def ccRespondOver( self, oth, success ):
		self.actionComplete()

		# If we didn't get there then give up
		if not success:
			print "... could not reach assailant"
			return

		# Otherwise have at them
		print "... target reached."
		tempRH = self.rightHandItem
		if not tempRH: tempRH = self.getItem( self.rightHand )
		self.closeCombatCommence( tempRH, oth )


	def set_avatarModel( self, oldValue = None ):
		def onModelChanged():
			self.setUpMovementSpeedsFromModel()
			self.set_rightHand( itemChangeAnim = 0 )
			self.set_shoulder()
			self.set_rightHip()
			self.set_leftHip()

		Avatar.set_avatarModel( self, oldValue, onModelChanged )


	# Override from Avatar
	def set_rightHand( self, oldRH = None, itemChangeAnim = 1 ):
		Avatar.set_rightHand( self, oldRH, itemChangeAnim )

		#TODO : put back in, PCWJ is removing this for testing loadBG only
		#if itemChangeAnim != 0 and self.physics != None:
		#	ti = Item.newItem( self.rightHand )
		#	if ti != None:
		#		ti.glanceByPlayer( self )

	# Override from Avatar
	def set_rightHandEnd( self, itemChangeAnim ):
		oldCombatStance = self.inCombat()
		Avatar.set_rightHandEnd( self, itemChangeAnim )

		# go in or out of combat stance if we need to
		if oldCombatStance != self.inCombat():
			self.setCombatStance()

		# TODO : this should be a PlayerAvatar override of the
		# setRightHandLock method, just in case an item uses its
		# model in equipByPlayer.
		if self.rightHandItem != None:
			self.rightHandItem.equipByPlayer( self )
		else:
			BigWorld.target.caps( Caps.CAP_CAN_USE )

	def _initHealth( self, oldHealth = None ):
		Avatar.set_healthPercent( self, oldHealth )

	def recoil( self, shooter, lockAccuracy ):
		Avatar.recoil( self, shooter, lockAccuracy )

	# Pressed a stance-changing key in close combat mode
	def takeStance( self, newStance ):
		self.cell.setStance( newStance )
		self.stance = newStance
		self.set_stance()

	# An item is telling us that the player should go into close combat mode
	def closeCombatCommence( self, item, target ):
		item.enact(self,target)				# Play the swing

		return # close combat has been disabled until further notice

		if not self._isConnected(): return

		tid = 0
		if target != None:
			tid = target.id
			self.modeTarget = tid				# modeTarget is an OTHER_CLIENT property
		else:
			self.modeTarget = Mode.NO_TARGET	# modeTarget is an OTHER_CLIENT property

		self.stance = Avatar.STANCE_NEUTRAL	# so is stance
		self.cell.assail( tid )			# Tell server about it

		# TODO: Shouldn't do this if no target...
		self.moveActionCommence()				# Wait for result of swing
											#  (so can't change item)

		# Seek to correct position if target is already attacking us
		if target != None and isinstance( target, Avatar ):
			if target.mode == Mode.COMBAT_CLOSE and target.modeTarget == self.id:
				pos = Vector3( target.position )
				yaw = target.yaw
				dir = Vector3( math.sin( yaw ), 0, math.cos( yaw ) )
				pos += dir.scale( PlayerAvatar.CLOSE_COMBAT_DISTANCE )

				# 5s time out, 1m acceptable height difference, no callback
				self.physics.seek( (pos.x,pos.y,pos.z,yaw+math.pi), 5.0, 1.0 )
				self.physics.velocity = (0,0,self.runFwdSpeed)


	# The player wants to make an attack
	def closeCombatSwing( self ):
		# We now always tell the server when we want to attack,
		# regardless of whether or not the fight has started or
		# we're doing an animation due to the last result message.
		# The server sorts it all out and takes action when it feels like it
		self.cell.setStance( 100 )

		# We need to set a variable here to indicate that we have an attack
		# request outstanding, then do some client tricks to decide when
		# to play the filler: basically, whenever our mode target is also
		# in close combat with us, and we have an attack request in the
		# pipeline, and we're not playing another animation. The tricky
		# bit will be that when the target goes into combat mode (and
		# before the fight has started for real), there'll have to be a
		# method that gets called on us so we can start the filler if
		# we have a swing in the queue... or something.

		#if not self.ccFightStarted: return
		# obv. needs to check previous action finished
		#self.cell.setStance( 100 )
		#self.model.CCFwdActFill()
		#try:
		#	self.ccTarget.model.CCAnyPasFill()
		#except:
		#	pass


	def onNarrowTarget( self, isEnter ):
		pass


	#
	# Returns true if client is connected to BW server
	#
	def _isConnected( self ):
		return self.id < (1<<30)


	#
	# GDC 2007
	#
	# toggle 'fast' Time of Day mode
	@BWKeyBindingAction( "DemoKey1" )
	def demoKey1( self, isDown ):
		if isDown:
			if not hasattr( self, "demoKey1Pressed" ):
				BigWorld.setWatcher( "Client Settings/Secs Per Hour", 1.0 )
				self.demoKey1Pressed = True
			else:
				BigWorld.setWatcher( "Client Settings/Secs Per Hour", 99999.0 )
				BigWorld.setWatcher( "Client Settings/Time of Day", 15.0 )
				del self.demoKey1Pressed


	#
	# GDC 2007
	#
	# teleport to area 1, outside the dungeon
	@BWKeyBindingAction( "DemoKey2" )
	def demoKey2( self, isDown ):
		if isDown:
			self.tryToTeleport( "", "demo1" )


	#
	# GDC 2007
	#
	# teleport to area 2, near the wharf in the fishing village
	@BWKeyBindingAction( "DemoKey3" )
	def demoKey3( self, isDown ):
		if isDown:
			self.tryToTeleport( "", "demo2" )


	#
	# GDC 2007
	#
	# teleport to area 3, near the orc spawner
	@BWKeyBindingAction( "DemoKey4" )
	def demoKey4( self, isDown ):
		if isDown:
			self.tryToTeleport( "", "demo3" )


	#
	# GDC 2007
	#
	# teleport to area 4, the starting point
	@BWKeyBindingAction( "DemoKey5" )
	def demoKey5( self, isDown ):
		if isDown:
			self.tryToTeleport( "", "demo4" )


	#
	# GDC 2008
	#
	# Toggle random weather changes (client-only so as not to interrupt
	# other demo machines)
	@BWKeyBindingAction( "DemoKey0" )
	def demoKey0( self, isDown ):
		if isDown:
			import Weather
			Weather.weather().toggleRandomWeather()


	#
	# GDC 2008
	#
	# Immediately loop to the previous weather system
	@BWKeyBindingAction( "DemoKeyMinus" )
	def demoKeyMinus( self, isDown ):
		if isDown:
			import Weather
			Weather.weather().nextWeatherSystem( False, True )

	#
	# GDC 2008
	#
	# Immediately loop to the next weather system
	@BWKeyBindingAction( "DemoKeyEquals" )
	def demoKeyEquals( self, isDown ):
		if isDown:
			import Weather
			Weather.weather().nextWeatherSystem( True, True )


import ResMgr

# This function loads and parses the XML file describing all the
# ways in which player supermodels can be constructed,
# and stores the result in the global variable AvatarModels.
def buildAvatarModels( cclass = None ):
	global AvatarModels
	AvatarModels = ResMgr.openSection( "scripts/client/AvatarModels.xml" )

	good = 0
	try:
		amp = ResMgr.openSection( "scripts/client/AvatarModelPresets.xml" )
		if not cclass or not amp.has_key( cclass ):	cclass = "presets"
		Avatar.modelPresets = eval( amp.readString( cclass ) )
		good = (type(Avatar.modelPresets) == type([]))
	except:
		pass
	if not good: Avatar.modelPresets = []

buildAvatarModels()


# Return a model from the given model number
def makeModel( num, oldModel ):
	#print "makeModel(",num,")"
	global AvatarModels

	mnames = []
	dspecs = {}
	# use the bottom n values of num at each stage

	# first decide which skeleton
	skelsec = AvatarModels
	skelcount = len(skelsec)
	skelid = num % skelcount
	num = (num-skelid) / skelcount
	skel = AvatarModels.values()[ skelid ]

	#print " skelid", skelid

	# now for each of the parts:
	for partsec in skel.values():

		# decide which model variation to use
		partcount = len(partsec)
		partid = num % partcount
		num = (num-partid) / partcount
		part = partsec.values()[ partid ]
		mnames.append( part.asString )

		#print "  part", partsec.name, partid

		# and for each of its matters:
		for tintsec in part.values():

			# decide what tint to use
			tintcount = len(tintsec) + 1
			tintid = num % tintcount
			num = (num-tintid) / tintcount
			if tintid > 0:
				tint = tintsec.keys()[ tintid-1 ]
			else:
				tint = ""
			dspecs[ tintsec.name ] = tint

			#print "   tint", tintsec.name, tintid

	# make the model
	#print "mnames: ", mnames
	if oldModel != None and oldModel.sources == tuple(mnames):
		m = oldModel
	else:
		m = BigWorld.Model( *mnames )

	# apply any dyes
	#print "dspecs: ", dspecs
	for dye in dspecs.items():
		setattr( m, dye[0], dye[1] )

	# and that's it
	return m


# Return a tree describing all model combinations
# A node in the tree is a list of choices which must be made at that
# node. The elements of the list are either tuples of more tree nodes
# or a number that must be selected.
def treeModelNumbers():
	global AvatarModels

	tr = []			# tuple => choose one of these
	for skel in AvatarModels.values():
		ts = []			# list => choose in each of these
		for partsec in skel.values():
			tps = []		# tuple => choose one of these
			for part in partsec.values():
				tp = []			# list => choose in each of these
				for tintsec in part.values():
					tt = len(tintsec)+1	# int => choose one of these
					tp.append( tt )
				tps.append( tp )
			ts.append( tuple(tps) )
		tr.append( ts )
	return [tuple(tr)]


# Return a list of all valid model numbers
def listModelNumbers():
	return listModelNode( treeModelNumbers() )

# Return a list of valid model numbers from this node
def listModelNode( node ):
	if node == []: return [0]

	b = []

	# go over all the elts in the list, and add them to b
	for elt in node:
		l = []

		# see if it's a tuple
		if type(elt) == type((0,)):
			lenelt = len(elt)
			for ei in range(lenelt):
				for i in listModelNode( elt[ei] ):
					l.append( ei + lenelt * i )
		# it must be an integer
		else:
			l = range(elt)

		b.append( l )

	# now flatten our list of numbers, by zipping it up
	nums = [0]
	for i in range( len(b)-1, -1, -1 ):
		nn = []
		for j in b[i]:
			for val in nums:
				nn.append( j + len(b[i]) * val )
		nums = nn

	return nums


def create():
	player = BigWorld.player()
	return BigWorld.createEntity('Avatar', player.spaceID, 0, player.position, (0,0,0), {})


# Helper function to calculate the intersection of a ray with a
#  convex polygon. Used with triangles from the collision scene.
# If passed a non-convex polygon it will return the furthest intersection
#  in the direction of rayDir.
# @args Vector3 raySrc, Vector3 rayDir, Sequence( Vector3 ) polygon
# @returns a tuple of the position of intersection, and the yaw of the
#	vector perpendicular to the edge of the poly
#  rayDir should probably be normalised

def intersectRayWithPolygon( raySrc, rayDir, polygon ):
	# shift the origin of the polygon to the ray's start
	spoly = map( lambda pt, raySrc=raySrc: Vector3( pt - raySrc ), polygon )

	# find the edges which are cut by dir (only 2 for a convex polygon)
	cands=[]
	for i in xrange(len(spoly)):
		apt = spoly[i]
		bpt = spoly[(i+1)%len(spoly)]
		across = rayDir.cross2D( apt )
		bcross = rayDir.cross2D( bpt )
		if (across > 0) != (bcross >= 0 ):
			cpt = bpt - apt
			numer = apt.cross2D( cpt )
			denom = rayDir.cross2D( cpt )
			cands.append((apt,cpt,numer/denom))

	# find the one with the biggest (positive) projection
	cands.sort( lambda s,t: -cmp( s[2], t[2] ) )

	# and that's the edge
	edge = raySrc + rayDir.scale( cands[0][2] )

	# find the vector perpendicular to the poly
	edgeParallel = cands[0][1]
	edgePerpendicular = Vector3(-edgeParallel.z, 0, edgeParallel.x)
	if edgePerpendicular.dot(rayDir) < 0:
		edgePerpendicular = -edgePerpendicular
	edgeYaw = math.atan2(edgePerpendicular.x, edgePerpendicular.z)

	return (edge, edgeYaw)


#Avatar.py



