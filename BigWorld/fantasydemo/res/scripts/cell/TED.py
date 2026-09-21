# Import required BigWorld modules
import BigWorld
import math

# Import required Python modules
import random

# Import common modes that TED may be in
import TEDModes

# Import required FantasyDemo modules
import Avatar


# TED demonstrates the use of a variety of Entity Extras,
# including navigation, vision and proximity triggers.

# To create TED, telnet to a BigWorld Base:
#	telnet <host> 40001
# and type:
#	BigWorld.createBase( "TED" )
class TED( BigWorld.Entity ):


	###########################
	# Definition of Constants #
	###########################

	# Behavioural data
	NONE = 0		# Indicates no behaviour registered (used to initialise)
	PATROL = 1		# When patrolling uses vision controller to identify another
					# entity
	INVESTIGATE = 2	# When another Entity is comes into vision, TED will
					# approach to investigate
	FLEE = 3		# When investigation gets too close, TED will flee and hide
	WAIT = 4		# When TED has hidden, it will wait for a time using scan
					# vision
	FOLLOW = 5		# If TED targeted by player, it will follow
	PROTECT = 6		# When TED FLEES and screams, any other nearby TEDs will run
					# to him
	USED = 7		# When TED is used, all other behaviours become irrelevant
					# until he is unUSED

	# Visual Controller data
	FOV = math.pi / 3			# Field-Of-View (in radians)
	VISUAL_RANGE = 200			# Visual range in metres
	VIEW_HEIGHT = 2				# Height of vantage point in metres
	SCAN_RADIUS = math.pi / 3	# Radius of scan (amplitude in radians)
	SCAN_DURATION = 10			# Scan duration in ticks (game cycles)
	SCAN_TIMEGAP = 10			# Time between scans in ticks
	VISION_UPDATE = 10			# Vision updated every 10 ticks

	# Move Contoller data
	HIDE_RADIUS = 50		# Radius in which TED will look for hiding place
	NO_HIDE_RADIUS = 20		# Radius within HIDE_RADIUS in which TED will
							# overlook cover
	COVER_TYPE = 1			# Type of cover to use (0: low cover, 1: anything)
	WALK_VELOCITY = 1.9		# Velocity at which TED will walk in m/s
	RUN_VELOCITY = 5.9		# Velocity at which TED will walk in m/s
	FOLLOW_ANGLE = 0		# Angle at which TED should follow target in radians
	FOLLOW_DIST = 1.0		# Distance at which TED should follow target in metres
	FOLLOW_MAXDIST = 10		# Distance for which TED should follow target in metres
	FACE_MOVEMENT = -1		# BOOL to indicate whether TED should be required to face movement direction
	TURN_VELOCITY = 1.9		# Rate at which TED can turn to face a screaming TED
	TURN_PERIOD = 10		# Period between checks for tracked Entity position in game ticks

	PATROL_RANGE = 20		# Determines permissable range of random patrol point
	MAX_WAIT = 10			# Maximum time for waiting (afterwards, will skip to PATROL)

	# Trigger data
	SIZEOF_TRAP = 2		# Spherical area of interest around TED

	# Noise data
	SCREAM_NOISE_LEVEL = 5		# Volume of TED's scream, multiplied by value in bw.xml
	SCREAM_RANGE = 10			# Informs players within this range that TED has screamed
	SCREAM_EVENT = 0			# Event for TED screaming - Each noise event should have its own unique tag


	# Initialise any required attributes
	def __init__( self ):
		BigWorld.Entity.__init__( self )

		# Handle to movement controller
		self.movementController = 0

		# Handle to vision controller
		self.visionController = 0

		# Handle to track current behaviour
		self.behaviour = self.WAIT

		# Initial action is WAIT
		self.changeBehaviour()

		# Set range of main Trap (sphere of awareness) in metres
		self.addProximity( self.SIZEOF_TRAP )


	# --------------------------------------------------------------------------
	# Method: use
	# Description:
	#	- If not in use, create ChatRoom on Base
	#	- If already in use, join entity to ChatRoom
	# --------------------------------------------------------------------------
	def use( self, clientPlayerID ):

		# If TED not in use
		if not self.mode == TEDModes.TED_INUSE:

			# Propagate change in state to all clients
			self.mode = TEDModes.TED_INUSE

			# TODO:  Inform Base TED to create ChatRoom

		# TED was already in use
		else:

			# Propagate change in state to all clients
			self.mode = TEDModes.NONE

			# TODO:  Inform Base to add this clientPlayerID to the ChatRoom


	# --------------------------------------------------------------------------
	# Method: changeBehaviour
	# Description:
	#	- Changes vision and movement controllers as required
	# --------------------------------------------------------------------------
	def changeBehaviour( self, oldBehaviour = None, targetEntity = None ):

		# No need to change anything if behaviour is the same
		if self.behaviour == oldBehaviour:
			return

		# Register a callback to be called once after given time period
		if self.behaviour == self.WAIT:

			# Timer will call onTimer() after given time (and will not repeat)
			# with PATROL data
			self.addTimer( random.random() * self.MAX_WAIT, 0, self.PATROL )


		#
		# Switching Vision Controllers
		#

		# If changing to WAIT mode, must switch to scan vision controller
		if self.behaviour == self.WAIT:

			# Cancel ordinary vision if present (may not be if WAIT is initial
			# behaviour)
			if not self.visionController == 0:
				self.cancel( self.visionController )

			# Use scan vision controller (parameters would match head movement)
			self.visionController = self.addScanVision( self.FOV,
				self.VISUAL_RANGE, self.VIEW_HEIGHT, self.SCAN_RADIUS,
				self.SCAN_DURATION, self.SCAN_TIMEGAP, self.VISION_UPDATE )

		# If changing from WAIT mode, must switch to normal vision controller
		elif oldBehaviour == self.WAIT:

			# Cancel scan vision if present (something wrong if it isn't)
			self.cancel( self.visionController )

			# Use normal vision controller
			self.visionController = self.addVision( self.FOV,
				self.VISUAL_RANGE, self.VIEW_HEIGHT, self.VISION_UPDATE )

		# If vision hasn't been created yet (and not WAIT), must create normal
		# vision
		elif self.visionController == 0:

			# Use normal vision controller
			self.visionController = self.addVision( self.FOV,
				self.VISUAL_RANGE, self.VIEW_HEIGHT, self.VISION_UPDATE )


		#
		# Switching Movement Controllers
		#

		# Cancel movement if present (every behaviour has different movement
		# pattern)
		if not self.movementController == 0:
		   self.cancel( self.movementController )

		# If behaviour is to WAIT, no movement, so pass
		if self.behaviour == self.WAIT:
			pass

		# If behaviour is to FLEE, then hide from target
		elif self.behaviour == self.FLEE:

			# Try to find some cover within range
			coverPos = self.findCover(
				self.HIDE_RADIUS, targetEntity.position,
				self.COVER_TYPE )

			# If cover is outside NO_HIDE_RADIUS
			if coverPos.distTo( targetEntity.position ) > self.NO_HIDE_RADIUS:

				# Run to cover
				self.movementController = self.navigate(
					coverPos, self.RUN_VELOCITY,
					self.FACE_MOVEMENT )

			# Otherwise...
			else:

				# Determine random point within HIDE_RADIUS
				x = random.uniform( -self.HIDE_RADIUS, self.HIDE_RADIUS )
				y = random.uniform( -self.HIDE_RADIUS, self.HIDE_RADIUS )
				z = random.uniform( -self.HIDE_RADIUS, self.HIDE_RADIUS )

				# Run to random point
				self.movementController = self.navigate(
					(x, y, z), self.RUN_VELOCITY,
					self.FACE_MOVEMENT )

		# If behaviour is to INVESTIGATE, then move towards target
		elif self.behaviour == self.INVESTIGATE:

			# Walk to entity, stopping when close to target
			self.movementController = self.moveToEntity(
				targetEntity.id, self.WALK_VELOCITY )

		# If behaviour is to FOLLOW or PROTECT, then run towards target
		elif self.behaviour == self.FOLLOW:

			# Follow entity at a run
			self.movementController = self.navigateFollow(
				targetEntity, self.FOLLOW_ANGLE, self.FOLLOW_DIST,
				self.RUN_VELOCITY, self.FOLLOW_MAXDIST,
				self.FACE_MOVEMENT )

		elif self.behaviour == self.PROTECT:

			# Face target
			# Note that a Tracker will have to be implemented on the client to
			# rotate model to the new direction
			self.trackEntity( targetEntity.id,
					self.TURN_VELOCITY, self.TURN_PERIOD )

		# If behaviour is to PATROL, pick a random position and navigate there
		elif self.behaviour == self.PATROL:

			# Determine random point within PATROL_RANGE
			x = random.uniform( -self.PATROL_RANGE, self.PATROL_RANGE )
			y = random.uniform( -self.PATROL_RANGE, self.PATROL_RANGE )
			z = random.uniform( -self.PATROL_RANGE, self.PATROL_RANGE )

			# If navigation is possible
			if self.canNavigateTo( (x, y, z) ):

				# Walk to random point
				self.movementController = self.navigate(
					(x, y, z), self.WALK_VELOCITY,
					self.FACE_MOVEMENT )

			# Otherwise...
			else:

				# Return to WAIT state
				oldBehaviour = self.behaviour
				self.behaviour = self.WAIT
				self.changeBehaviour( oldBehaviour, targetEntity )


	###################################
	# Navigation Controller Callbacks #
	###################################

	def onNavigate( self, controllerID, userData ):

		# Controller handle is now invalid, so reset
		self.movementController = 0

		# When movement is complete, return to WAIT
		oldBehaviour = self.behaviour
		self.behaviour = self.WAIT
		self.changeBehaviour( oldBehaviour )


	def onNavigateFailed( self, controllerID, userData ):

		# Controller handle is now invalid, so reset
		self.movementController = 0

		# If any movement failed, return to WAIT
		oldBehaviour = self.behaviour
		self.behaviour = self.WAIT
		self.changeBehaviour( oldBehaviour )


	def onMove( self, controllerID, userData ):

		# Controller handle is now invalid, so reset
		self.movementController = 0

		# When movement is complete, return to WAIT
		oldBehaviour = self.behaviour
		self.behaviour = self.WAIT
		self.changeBehaviour( oldBehaviour )


	def onMoveFailed( self, controllerID, userData ):

		# Controller handle is now invalid, so reset
		self.movementController = 0

		# If any movement failed (particularly PATROL), return to WAIT
		oldBehaviour = self.behaviour
		self.behaviour = self.WAIT
		self.changeBehaviour( oldBehaviour )


	###############################
	# Vision Controller Callbacks #
	###############################

	def onStartSeeing( self, entity ):

		# If TED is not functioning as a chat service
		if not self.behaviour == self.USED:

			# TODO: This is not safe in a multiple cell space. It won't work if
			# the entities are in different cells
			# When a Player Entity comes into view
			if entity.__class__ == Avatar.Avatar and \
					entity.isReal():

				# Say hello to that client only
				entity.clientEntity( self.id ).chat( u"G'day mate!" )

			# If Entity is not another TED
			if not entity.__class__ == TED:

				# Start investigating it
				oldBehaviour = self.behaviour
				self.behaviour = self.INVESTIGATE
				self.changeBehaviour( oldBehaviour, entity )


	def onStopSeeing( self, entity ):

		# If TED is not functioning as a chat service
		if not self.behaviour == self.USED:

			# Unless TED is already fleeing, when a Player Entity leaves view
			if not self.behaviour == self.FLEE and \
				   entity.__class__ == Avatar.Avatar and \
				   entity.isReal():

				# Say goodbye to that client only
				entity.clientEntity( self.id ).chat( u"See ya later!" )

			# If Entity is not another TED
			if not entity.__class__ == TED:

				# Return to wait state
				oldBehaviour = self.behaviour
				self.behaviour = self.WAIT
				self.changeBehaviour( oldBehaviour, entity )


	################################
	# Trigger Controller Callbacks #
	################################

	def onEnterTrap( self, entity, trapRange, trapID ):

		# If TED is not functioning as a chat service
		if not self.behaviour == self.USED:

			# Unless TED is already fleeing, when a non-TED Entity gets too
			# close
			if not self.behaviour == self.FLEE and \
				   not entity.__class__ == TED:

				# Inform BigWorld that TED has screamed for AI purposes
				self.makeNoise( self.SCREAM_NOISE_LEVEL, self.SCREAM_EVENT )

				self.otherClients.chat( u"AAArrrggghhh!!!!" )

				# Change behaviour to FLEE
				oldBehaviour = self.behaviour
				self.behaviour = self.FLEE
				self.changeBehaviour( oldBehaviour, entity )


	def onLeaveTrap( self, entity, trapRange, trapID ):

		# Leave behaviour as it is...
		pass


	#############################
	# Noise Controller Callback #
	#############################

	def onNoise( self, entity, propRange, distance, event, info ):

		# If a nearby TED Entity screamed (ie, not this one)
		if event == self.SCREAM_EVENT and \
		   not entity.id == self.id:

			self.otherClients.chat( u"What the...?" )

			# Make this TED Entity face the one that screamed
			oldBehaviour = self.behaviour
			self.behaviour = self.PROTECT
			self.changeBehaviour( oldBehaviour, entity )


	############################
	# Time Controller Callback #
	############################

	def onTimer( self, controllerID, userData ):

		# If userData matches our PATROL after WAIT flag
		if userData == self.PATROL:

			# Then switch the behaviour
			oldBehaviour = self.behaviour
			self.behaviour = self.PATROL
			self.changeBehaviour( oldBehaviour )

		# Alternatively, we could store the returned Timer Control Handle
		# and identify its function that way.  We would do that if we had
		# multiple Timer Controls to track for the PATROL mechanism and
		# definately for those that are repeating so they can be cancelled


	#############################
	# Turn Controller Callbacks #
	#############################

	def onTurn( self, controllerID, userData ):

		# This isn't used in this example, but would be called if we had a
		# need for turnToYaw
		pass

# TED.py
