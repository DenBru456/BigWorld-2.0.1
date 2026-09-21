# --------------------------------------------------------------------------
# This is an Application Personality Script.  It contains classes to control
# and maintain various user interface components, such as the Direction
# Cursor settings and the console, followed by a small number of
# miscellaneous helper functions.  Finally a series of BigWorld Client
# callback functions are implemented that allow the game's 'personality' to
# be configured, executed and terminated.  These are the main methods to
# interact with the BigWorld Client engine.
# --------------------------------------------------------------------------

import time
import string
import BigWorld
import FMOD
from Math import *
import math
from functools import partial
from Keys import *
import GUI
import types
import ResMgr
import os
import Account
import Avatar
from GraphicsPresets import GraphicsPresets
from Helpers import PyGUI
__import__('__main__').PyGUI = PyGUI
import FDGUI
__import__('__main__').FDGUI = FDGUI
import MainMenuGUI
__import__('__main__').MainMenuGUI = MainMenuGUI
import weakref
import MenuScreenSpace
import MenuScreenAvatar
import AvatarModel
import PlayerModel
from Helpers.BWCoroutine import *
from Helpers import BWKeyBindings
from Helpers import Region
from bwdebug import *
import Listener
import CameraNode
import Weather
from GameData import FantasyDemoData
import PostProcessing
from WebScreen import WebScreen
import OpenAutomate

import FDFX

#Load-time XML file storage
underWaterDS = ResMgr.openSection( "system/post_processing/chains/underwater.ppchain" )

############################################################################
# The following classes implement various aspects of the user interface.   #
# They are used internal to this script.  Neither BigWorld Components, nor #
# any other script needs to make use of them.                              #
############################################################################

MENU_ENTRIES = {
	'MAINMENU'   : (
		'Main Menu',
		'gui/maps/main_title_main.tga',
		'gui/maps/main_help_main.tga'),
	'LANSERVERS' : (
		'Search for Servers on Local Network...',
		'gui/maps/main_title_lan.tga',
		'gui/maps/main_help_menu.tga'),
	'ENTERUSERNAME'	: (
		'Enter Username',
		'gui/maps/main_title_login.tga',
		'gui/maps/main_help_menu_noback.tga'),
	'REALMSELECT'	: (
		'Select Realm',
		'gui/maps/main_title_realm_select.tga',
		'gui/maps/main_help_menu.tga'),
	'CHARACTERSELECT'   : (
		'Select Character',
		'gui/maps/main_title_character_select.tga',
		'gui/maps/main_help_menu.tga'),
	'CHARACTERCREATE'   : (
		'Select Character',
		'gui/maps/main_title_character_create.tga',
		'gui/maps/main_help_char_create.tga'),
	'XMLSERVERS' : (
		'Connect to Standard Server...',
		'gui/maps/main_title_servers.tga',
		'gui/maps/main_help_menu.tga'),
	'OFFLSPACES' : (
		'Explore Space Offline...',
		'gui/maps/main_title_offline.tga',
		'gui/maps/main_help_menu.tga'),
	'SETTINGS' : (
		'Change Display Settings...',
		'gui/maps/main_title_display.tga',
		'gui/maps/main_help_menu.tga'),
	'RESTART' : ('Restart Client', '', ''),
	'QUITGAME'   : ('Quit Game', '', '') }

HELP_EDIT        = 'gui/maps/main_help_edit.tga'
HELP_EDIT_NOBACK = 'gui/maps/main_help_edit_noback.tga'
MAX_ERROR_LEN    = 29

FIRST_PERSON_NEAR_CLIP_PLANE = 0.15


# --------------------------------------------------------------------------
# Class:  DCSettings
# Description:
#	- Reads and stores direction cursor settings.
# --------------------------------------------------------------------------
class DCSettings:

	# --------------------------------------------------------------------------
	# Method:  __init__
	# Description:
	#	- Initialises all required attributes.
	# --------------------------------------------------------------------------
	def __init__(self):
		self.invertVerticalMovement = 0
		self.mouseSensitivity = 0
		self.mouseHVBias = 0
		self.maxPitch = 0
		self.minPitch = 0

	# -------------------------------------------------------------------------
	# Method:  load
	# Description:
	#	- Reads data taken from the BigWorld Client Configuration Script.
	# -------------------------------------------------------------------------
	def load(self, sect):
		self.invertVerticalMovement = sect.readBool('invertVerticalMovement',
													self.invertVerticalMovement)
		self.mouseSensitivity = sect.readFloat('mouseSensitivity',
											   self.mouseSensitivity)
		self.mouseHVBias = sect.readFloat('mouseHVBias', self.mouseHVBias)
		self.maxPitch = sect.readFloat('maxPitch', self.maxPitch)
		self.minPitch = sect.readFloat('minPitch', self.minPitch)

	# -------------------------------------------------------------------------
	# Method:  copy
	# Description:
	#	- Copies data from this class into another class.
	# -------------------------------------------------------------------------
	def copy(self, oth):
		self.__dict__.update(oth.__dict__)

###########################
# End of class DCSettings #
###########################



# -----------------------------------------------------------------------------
# Class: RDShare
# Description:
#	- Maintains all shared personality data.
# -----------------------------------------------------------------------------
class RDShare(Listener.Listenable):

	# -------------------------------------------------------------------------
	# Method: __init__
	# Description:
	#	- Initialises shared personality data.
	# -------------------------------------------------------------------------
	def __init__(self):
		Listener.Listenable.__init__( self )
		self.outsidePivotMaxDist = 0
		self.insidePivotMaxDist = 0
		self.reversePivotMaxDist = 0
		self.overridePivotMaxDist = 0

		self.useWoWMode = True
		self.mouseMoveThreshold = 5

		self.currFov = 0
		self.fovs = [60,20]

		self.fixedMatrix = Matrix()

		self.cc = None
		self.flc = None
		self.fic = None
		self.frc = None

		# Indexes by which the above 4 cameras are referred to from the outside
		self.CURSOR_CAMERA = 0
		self.FLEXI_CAM = 1
		self.FIXED_CAMERA = 2
		self.FREE_CAMERA = 3

		self.gameCamIdx = 0		# for free camera mode
		self.cameraKeyIdx = 0

		self.firstPersonDCSettings = DCSettings()
		self.thirdPersonDCSettings = DCSettings()

		self.inside = 0

		self.console = None

		self.maxBandwidth = 20000 # default of FantasyDemo

		self.spaceNameMap = {}
		self.deviceListeners = {}
		self.environmentChangeListeners = {}
		self.cameraSpaceChangeListeners = {}
		self.lastWeatherSpaceID = None
		self.cameraSpaceID = 0
		self.flyThroughMode = False

		self.selfDisconnect = False
		self.__flyThroughStartNodeName = 'camera node0'
		self.inGameFocusedComponent = None
		
		self.underWaterChain = None
		

	def init( self ):
		BigWorld.addWatcher('Comms/Max bandwidth per second', self.getMaxBps, self.setMaxBps)
		self.region = Region.Region()


	def fini( self ):
		BigWorld.delWatcher('Comms/Max bandwidth per second')
		self.region.fini()
		if hasattr( self, "waterListenerID" ):
			BigWorld.delWaterVolumeListener( self.waterListenerID )
		# unfortunately, we cannot have a weakref to a
		# [un]bound method. This is why we need to explicitly
		# break the cyclic references before exiting
		self.console.script.fini()
		del self.console
		self.selfDisconnect = False
		self.underWaterChain = None

		
	def initUnderwaterPP( self ):
		listener = self.onPostProcessingGraphicsSettingChanged
		PostProcessing.registerGraphicsSettingListener( listener )
		self.onPostProcessingGraphicsSettingChanged( BigWorld.getGraphicsSetting( "POST_PROCESSING" ) )

		
	def onPostProcessingGraphicsSettingChanged( self, optionIdx ):
		#print "onPostProcessingGraphicsSettingChanged", optionIdx
		if optionIdx == 0: #VERY HIGH
			self.underWaterChain = PostProcessing.load( underWaterDS )
		else:
			self.underWaterChain = None		
		
		
	def cameraWaterCallback(self, entering, volume):
		if entering == True:
			self.underwaterFogEmitter = BigWorld.addFogEmitter( (0,0,0), 10, -10, 100, 0x6060c0, False )
			if self.underWaterChain is not None:
				self.outOfWaterChain = PostProcessing.chain()
				PostProcessing.chain( self.underWaterChain )
		else:
			BigWorld.delFogEmitter( self.underwaterFogEmitter )
			if hasattr(self, "outOfWaterChain"):
				PostProcessing.chain( self.outOfWaterChain )
				del self.outOfWaterChain

	def initConsole(self):
		if self.console is None:
			# create fantasy demo console
			self.console = GUI.load("gui/fd_console.gui")
			self.console.script.active(True)
			self.console.script.showNow()

	def getMaxBps(self):
		return str(self.maxBandwidth)

	def setMaxBps(self, bps):
		self.maxBandwidth = int(bps)
		BigWorld.player().base.setBandwidthPerSecond(int(bps))

	def camera(self, idx):
		return (self.cc, self.flc, self.fic, self.frc)[ idx % 4 ]


	def baseFOV(self):
		return self.fovs[ self.currFov % len(self.fovs) ]


	def changeBaseFOV(self):
		self.currFov = self.currFov + 1
		self.currFov = self.currFov % len(self.fovs)
		self.fovs = [60,20]


	def updatePivotDist(self):
		self.cc.maxDistHalfLife = 1.5
		if self.overridePivotMaxDist > 0:
			self.cc.pivotMaxDist = self.overridePivotMaxDist
			self.cc.maxDistHalfLife = 0.15
		elif self.cc.reverseView:
			self.cc.pivotMaxDist = self.reversePivotMaxDist
		else: # m6rad changes
#		elif self.inside:
			self.cc.pivotMaxDist = self.insidePivotMaxDist
#		else:
#			self.cc.pivotMaxDist = self.outsidePivotMaxDist

	def toggleFlyThroughMode( self ):
		self.setFlyThroughMode( not self.flyThroughMode )
		return self.flyThroughMode

	def setFlyThroughMode( self, enabled ):
		if self.isFlightPathLoaded() == False or self.flyThroughMode == enabled:
			return

		if enabled:
			BigWorld.runFlyThrough( self.__flyThroughStartNodeName , True)
		else:
			BigWorld.cancelFlyThrough()
		self.flyThroughMode = enabled
		self.listeners.flyThroughModeActivated( enabled, None )


	def isFlightPathLoaded( self ):
		"""
		Returns True if all the UDO CameraNodes in the flight path have finished loading, otherwise returns false.
		"""
		cameraNodes = [udo for udo in BigWorld.userDataObjects.values() if isinstance( udo, CameraNode.CameraNode )]
		startCamera = [cn for cn in cameraNodes if cn.name == self.__flyThroughStartNodeName]
		if len( startCamera ) != 1:
			if len( startCamera ) > 1:
				ERROR_MSG( "There are %d fly-through camera	start nodes.  Please make sure there is only 1" % (len(startCamera),))
			return False
		else:
			startCamera = startCamera[0]
		try:
			nextCamera = startCamera.next
			while True:
				if nextCamera is None or nextCamera == startCamera:
					return True
				else:
					nextCamera = nextCamera.next
		except BigWorld.UnresolvedUDORefException:
			pass
		return False

	def flyThroughFinished( self, resultList ):
		if self.flyThroughMode:
			self.flyThroughMode = False
			self.listeners.flyThroughModeActivated( False, resultList )

########################
# End of class RDShare #
########################


# -----------------------------------------------------------------------------
# Class: LoginInfo
# Description:
#	- Stores login information.
# -----------------------------------------------------------------------------
class LoginInfo:
	def __init__(self):
		self.username = ''
		self.password = 'a'
		self.inactivityTimeout = 60
		try:
			global rds
			self.username          = rds.userPreferences.readWideString('lastUsedAccountName')
			self.password          = rds.scriptsConfig._login._password.asString
			self.inactivityTimeout = rds.scriptsConfig._login._inactivityTimeout.asInt
		except:
			pass

##########################
# End of class LoginInfo #
##########################


############################################################################
# The following are miscellaneous functions/commands for internal use or   #
# use by other scripts.                                                    #
############################################################################


# -----------------------------------------------------------------------------
# Method: v4col
# Description:
#		- Helper function to turn a vector3 into a full-on vector4 colour
# -----------------------------------------------------------------------------
def v4col(v3col, alpha = 255):
	return (v3col[0], v3col[1], v3col[2], alpha)


# These commands will be executed when the script is run by BigWorld.


# Stores whether or not the use key is down
isUseKeyDown = 0


# Set the camera type. Used to be in script_bigworld.cpp
def cameraType(idx):
	global rds
	newcam = rds.camera(idx)
	newcam.set(BigWorld.camera().matrix)
	BigWorld.camera(newcam)
	if idx < 3: rds.gameCamIdx = idx


# Change to the fixed camera, and set it to the given points
def setFixedCamera(camPos, lookPos):
	global rds
	if not hasattr(camPos, 'x'):  camPos = Vector3(*camPos)
	if not hasattr(lookPos, 'x'): lookPos = Vector3(*lookPos)
	lookDir = lookPos - camPos
	lookDir.normalise()

	# could move out -1 * lookDir if we wanted no movement at all
	# in the fixed camera (-1 because of preferredPos setting)
	# like this is probably better for collision scene issues

	rds.fixedMatrix.lookAt(camPos, lookDir, (0,1,0))
	rds.fic.set(rds.fixedMatrix)

	rds.fixedMatrix.invert()
	BigWorld.camera(rds.fic)
	rds.gameCamIdx = 2


def camera(idx):
	global rds
	return rds.camera(idx)


# Change to the next camera
def nextCamera():
	global rds
	curcam = BigWorld.camera()
	if curcam == rds.cc:
		newcam = 1
	elif curcam == rds.flc:
		newcam = 2
	else:
		newcam = 0
	cameraType(newcam)


# Set free camera mode
def freeCamera(ison):
	resetCameraOffset()
	if ison:
		cameraType(3)
	else:
		cameraType(rds.gameCamIdx)


# Set first person mode
def firstPerson(ison):
	global rds

	rds.cc.firstPerson = ison

	if ison:
		dcSet = rds.firstPersonDCSettings
	else:
		dcSet = rds.thirdPersonDCSettings

	dc = BigWorld.dcursor()
	#dc.invertVerticalMovement = dcSet.invertVerticalMovement
	dc.mouseSensitivity       = dcSet.mouseSensitivity
	dc.mouseHVBias            = dcSet.mouseHVBias
	dc.maxPitch               = dcSet.maxPitch * math.pi / 180.0
	dc.minPitch               = dcSet.minPitch * math.pi / 180.0

	# stop any fov ramp in progress
	# (don't ask... app.cpp did this)
	p = BigWorld.projection()
	p.fov = p.fov


def setCursorCameraPivot(px, py, pz):
	global rds
	rds.cc.pivotPosition = (px, py, pz)


def cameraDistanceOverride(val):
	global rds
	rds.overridePivotMaxDist = val
	rds.updatePivotDist()


def cameraDistance(val):
	global rds
	rds.insidePivotMaxDist = val
	rds.updatePivotDist()


def cameraTarget(entity):
	global rds

	# Wow this function is so much easier than in C++!

	if entity == BigWorld.player():
		matrix = BigWorld.PlayerMatrix()
	else:
		matrix = entity.matrix

	rds.cc.target = matrix
	rds.flc.target = matrix


def fov(degs):
	BigWorld.projection().fov = degs * math.pi / 180.0


def changeFOV(degs, t):
	BigWorld.projection().rampFov(degs * math.pi / 180.0, t)


def initConsole():
	global rds
	rds.initConsole()

def htmlChatWindow():
	# add to chat console
	return weakref.proxy(rds.fdgui.htmlChatWindow.script)

def chatConsole():
	global rds

	# add to chat console
	if hasattr(rds, "fdgui") and rds.fdgui is not None:
		return weakref.proxy(rds.fdgui.chatWindow)

	assert rds.console is not None
	return weakref.proxy(rds.console)


def addChatMsg( id, msg, colour = FDGUI.TEXT_COLOUR_SYSTEM ):
	cc = chatConsole()

	if cc:
		if BigWorld.player() and id == BigWorld.player().id:
			msg = 'you say: ' + msg
			colour = FDGUI.TEXT_COLOUR_YOU_SAY
		elif id != -1:
			msg = getEntityName(id) + ': ' + msg
			colour = FDGUI.TEXT_COLOUR_OTHER_WISHPER

		cc.script.addMsg( msg, colour )
		window = htmlChatWindow()
		window.addChatMsg( msg )

def appendChatMsg( id, msg, colour = FDGUI.TEXT_COLOUR_SYSTEM ):
	cc = chatConsole()

	if cc:
		if BigWorld.player() and id == BigWorld.player().id:
			msg = 'you say: ' + msg
			colour = FDGUI.TEXT_COLOUR_YOU_SAY
		elif id != -1:
			msg = getEntityName(id) + ': ' + msg
			colour = FDGUI.TEXT_COLOUR_OTHER_WISHPER

		cc.script.appendMsg( msg, colour )

def addMsg( msg, colour = FDGUI.TEXT_COLOUR_SYSTEM ):
	addChatMsg( -1, msg, colour )


def appendMsg( msg, colour = FDGUI.TEXT_COLOUR_SYSTEM ):
	appendChatMsg( -1, msg, colour )

def getEntityName(id):
	e = BigWorld.entity(id, 1)
	if not e:					# no such entity
		en = 'Nonexistent Entity'
	elif not hasattr(e, 'name'):			# no name attr
		en = e.__class__.__name__
	elif type(e.name) == types.StringType:		# it's a string attr
		en = e.name
	else:						# try as a callable attr
		try:	en = e.name()
		except:	en = '[error in entity[%d].name()]' % id
	return en


# A couple of helper functions to add and remove key bindings.
def addBindingForAction( actionName, binding ):
	rds.keyBindings.addBindingForAction( actionName, binding )
	rds.keyBindings.buildBindList()
	rds.keyBindings.writePreferenceKeyBindings( rds.userPreferences )
	BigWorld.savePreferences()


def removeBindingForAction( actionName, binding ):
	rds.keyBindings.removeBindingForAction( actionName, binding )
	rds.keyBindings.buildBindList()
	rds.keyBindings.writePreferenceKeyBindings( rds.userPreferences )
	BigWorld.savePreferences()



############################################################################
# The following functions implement the callbacks that BigWorld uses to    #
# initiate and maintain an application's 'personality'.                    #
############################################################################

# -----------------------------------------------------------------------------
# Method: init
# Description:
#	- The init function is called as part of the BigWorld Client
#	initialisation process.
#	- It receives the configuration script in a parsable format.
#	- This is the best place to configure all the application-specific
#		components, like initial Camera view, etc...
#	- init() creates a BigWorld Space and adds the parsed universe to it.
#	- It then creates a camera, configuring it using the values from the
#		appropriate xml data section.
#	- It also creates the Console class, again using the xml data.
# -----------------------------------------------------------------------------
def init(scriptsConfig, engineConfig, userPreferences, loadingScreenGUI = None):
	global rds

	rds.userPreferences = userPreferences

	rds.middleMouseButtonDown = False
	rds.cameraCloseUpTrigger = 0.65

	rds.scriptsConfig = scriptsConfig
	rds.clientSpace = None
	rds.clientSpaceMapping = None

	rds.loadingScreen = loadingScreenGUI

	rds.keyBindings = BWKeyBindings.BWKeyBindings()

	# TODO: should be read by a module in scripts/common/GameData
	keyBindingData = ResMgr.openSection( "scripts/data/default_key_bindings.xml" )
	rds.keyBindings.readInDefaultKeyBindings( keyBindingData )

	if rds.userPreferences.has_key( "keyBindings" ):
		keyBindingData = rds.userPreferences._keyBindings
		rds.keyBindings.readInPreferenceKeyBindings( keyBindingData )

	rds.keyBindings.buildBindList()
	#rds.keyBindings.printBindList()

	# An action handler for FantasyDemo module level actions
	rds.fantasyDemoActionHandler = FantasyDemoActionHandler()
	rds.keyBindings.addHandler( rds.fantasyDemoActionHandler )

	# One for the DSLR module
	import DSLR
	rds.dslrActionHandler = DSLR.DSLRActionHandler()
	rds.keyBindings.addHandler( rds.dslrActionHandler )

	actionToolTipsSection = ResMgr.openSection( "scripts/data/action_tooltips.xml" )
	rds.fdgui = FDGUI.FDGUI()
	rds.fdgui.setupGUI( actionToolTipsSection, rds.keyBindings )

	#setLanguage(scriptsConfig.readString('ui/language', 'english'))

	cc = BigWorld.CursorCamera()
	cc.source = BigWorld.dcursor().matrix
	cc.target = BigWorld.PlayerMatrix()
	BigWorld.dcursor().yawReference = cc.invViewMatrix
	BigWorld.dcursor().minYaw = -2
	BigWorld.dcursor().maxYaw =  2

	cc.pivotPosition = scriptsConfig.readVector3(
		'camera/defTargetOffset', (0.0, 1.8, 0.0))

	rds.outsidePivotMaxDist = scriptsConfig.readFloat(
		'camera/maxDistanceFromPivot', cc.pivotMaxDist)
	rds.insidePivotMaxDist = scriptsConfig.readFloat(
		'camera/indoorDistanceFromPivot', rds.outsidePivotMaxDist)
	rds.reversePivotMaxDist = scriptsConfig.readFloat(
		'camera/faceDistanceFromPivot', rds.outsidePivotMaxDist)

	rds.useWoWMode = userPreferences.readBool('useWoWMode', rds.useWoWMode)
	rds.mouseMoveThreshold = scriptsConfig.readInt(
		'camera/mouseMoveThreshold', rds.mouseMoveThreshold)

	cc.pivotMaxDist = rds.outsidePivotMaxDist
	cc.pivotMinDist = scriptsConfig.readFloat(
		'camera/minDistanceFromPivot', cc.pivotMinDist)
	cc.terrainMinDist = scriptsConfig.readFloat(
		'camera/minDistanceFromTerrain', cc.terrainMinDist)
	cc.maxVelocity = scriptsConfig.readFloat(
		'camera/maxVelocity', cc.maxVelocity)
	cc.movementHalfLife = scriptsConfig.readFloat(
		'camera/movementHalfLife', cc.movementHalfLife)
	cc.turningHalfLife = scriptsConfig.readFloat(
		'camera/turningHalfLife', cc.turningHalfLife)

	rds.cc = cc
	rds.defaultPivotMaxDist = rds.outsidePivotMaxDist
	rds.defaultNearPlane = BigWorld.projection().nearPlane

	# flexi cam
	flc = BigWorld.FlexiCam()
	flc.target = cc.target
	flc.preferredPos = (0.0, 3.2, -2.5)
	flc.viewOffset = (0.0, 1.8, 0.0)
	flc.timeMultiplier = 8

	rds.flc = flc

	# fixed cam
	fic = BigWorld.FlexiCam()
	fic.target = rds.fixedMatrix
	fic.preferredPos = (0,0,-1)
	fic.viewOffset = (0,0,0)
	fic.timeMultiplier = 8

	rds.fic = fic

	# free cam
	rds.frc = BigWorld.FreeCamera()


	# compute matrix to translate camera position to near plane
	m = MatrixProduct()
	m.a = Matrix()
	m.a.setTranslate( (0, 0, BigWorld.projection().nearPlane) )
	m.b = rds.cc.invViewMatrix

	# hook up the cameras to water
	rds.waterListenerID = BigWorld.addWaterVolumeListener( m, rds.cameraWaterCallback )

	# start off with
	# cursor camera
	BigWorld.camera(cc)

	# now load direction
	# cursor details
	try:
		rds.thirdPersonDCSettings.load(engineConfig._directionCursor)
	except:
		pass

	try:
		rds.firstPersonDCSettings.copy(rds.thirdPersonDCSettings)
		rds.firstPersonDCSettings.load(scriptsConfig._dcFirstPersonOverrides)
	except:
		pass

	# make the console
	initConsole()

	# time of day when offline
	rds.offlineTimeOfDay = scriptsConfig.readString('offline/timeOfDay', '14:00')
	rds.offlineSpaces = None

	rds.lastWeatherSync = {}
	Weather.weather()

	# load the logo gui
	rds.logoGui = None

	#__import__('Helpers').alertsGui.instance.init()
	#__import__('Helpers').Inventory.instance.init()

	# for GDC 2010 - preload the spell effect
	#import FX
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/staff_spell.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/staff_spell.xml", 10 ) )
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/staff_explosion.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/staff_explosion.xml", 10 ) )
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/person_explosion.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/person_explosion.xml", 10 ) )
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/air_explosion.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/air_explosion.xml", 10 ) )
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/ground_explosion.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/ground_explosion.xml", 10 ) )
	#BigWorld.loadResourceListBG(FX.prerequisites("sfx/staff_lightning.xml" ), partial( FX.getBufferedOneShotEffect, "sfx/staff_lightning.xml", 10 ) )

	# and we're done
	print 'fantasydemo personality selected.'

# -----------------------------------------------------------------------------
# Method: start
# Description:
#	- The start function is called after the BigWorld Client has initialised
#	and is used	to begin the game.
#	- Although it receives no data, it uses the shared personality data to
#	initiate the login process.
#	- Other instances may display an introduction or initiate some other game
#	flow process...
# -----------------------------------------------------------------------------
def start():
	import sys
	if len(sys.argv) >= 4 and sys.argv[1] == 'profile':
		# fantasydemo.exe -sa profile -sa spaces/highlands -sa gf8800
		runProfiler( sys.argv[2], sys.argv[3], True )
		return
	elif len(sys.argv) >= 3 and sys.argv[1] == 'loadtimer':
		# fantasydemo.exe -sa loadtimer -sa spaces/highlands
		print "Starting load timer run ..."
		_loadTimerStart( sys.argv[2] )
		return
	elif (len(sys.argv) == 3 or len(sys.argv) == 4) and sys.argv[1] == '-openautomate':
		OpenAutomate.startOpenAutomate()
	internalStart()


# -----------------------------------------------------------------------------
# Method: internalStart
# Description:
#	- The internalStart function is called after start has finished to begin 
#   the game.
#	- Although it receives no data, it uses the shared personality data to
#	initiate the login process.
#	- Other instances may display an introduction or initiate some other game
#	flow process...
# -----------------------------------------------------------------------------
def internalStart():
	global rds
	BigWorld.worldDrawEnabled(False)
	rds.startupGUI = GUI.load('gui/main_menu.gui')

	rds.mainMenuGUI = rds.startupGUI.mainmenu
	rds.mainMenuGUI.script.scrollUp = rds.startupGUI.scrollUp
	rds.mainMenuGUI.script.scrollDown = rds.startupGUI.scrollDown

	rds.mainMenuGUI.script.parent   = rds.startupGUI
	rds.mainMenuGUI.script.isActive = True
	rds.mainMenuGUI.script.active(False)

	rds.menuCaptionsGUI = rds.startupGUI.captions

	rds.usernameGUI = rds.startupGUI.username

	rds.editField = rds.usernameGUI.edit
	rds.editField.script.parent   = rds.usernameGUI
	rds.editField.script.isActive = True

	rds.advertisingScreen = None

	rds.li = LoginInfo()

	_showLogoScreen(False)
	_showLoadingBar(False)

	if not OpenAutomate.openAutomateMode:
		setMainMenuActive( True ).run()

	onRecreateDevice()
	BigWorld.callback(0.1, _testEngineFeatures)

	PostProcessing.init()
	rds.initUnderwaterPP()


_mainMenuActiveCount = 0
_mainMenuChanging = False

@BWCoroutine
def setMainMenuActive( active ):
	global _mainMenuActiveCount
	global _mainMenuChanging

	yield BWWaitForCondition( lambda: _mainMenuChanging == False )

	if active:
		_mainMenuActiveCount += 1
		if _mainMenuActiveCount == 1:
			_mainMenuChanging = True
			yield BWWaitForCoroutine( _startMainMenu() )
			_mainMenuChanging = False
	else:
		_mainMenuActiveCount -= 1
		if _mainMenuActiveCount == 0:
			_mainMenuChanging = True
			yield BWWaitForCoroutine( _finishMainMenu() )
			_mainMenuChanging = False



############################################################################
# Main menu, server discovery and login related functions.
############################################################################

@BWCoroutine
def _startMainMenu():
	'''Activates the game menu. The game menu is a two level menu.
	Calling 	this method, activates the first level. The second
	level menus are activated by callback functions attached to
	the first level menu items.
	'''

	rds.startupGUI.script.active(True)
	rds.startupGUI.fader.alpha = 1.0
	rds.startupGUI.fader.reset()

	yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( False, 0 ) )

	_setRootMenuMenuItems()

	logoFadeTime = _showLogoScreen( False )
	disableWorldDrawing()

	if not MenuScreenSpace.g_loaded:
		yield BWWaitForCoroutine( MenuScreenSpace.init() )


def _setRootMenuMenuItems():
	rds.menuStack = []
	_pushMainMenu()

	if rds.scriptsConfig.readBool( 'login/connectOnStartup', False ):
		xmlServers  = rds.scriptsConfig.readStrings('login/host')
		_setMainMenu([], 'ENTERUSERNAME')
		_inputUserNameAndConnect( xmlServers[0], xmlServers[0], 0, None, False )
	else:
		mainMenuItems = [
			(MENU_ENTRIES[ 'XMLSERVERS' ][0], _showXMLServersMenu),
			(MENU_ENTRIES[ 'LANSERVERS' ][0], _showLanServersMenu),
			(MENU_ENTRIES[ 'OFFLSPACES' ][0], _showOfflineSpacesMenu),
			(MENU_ENTRIES[ 'SETTINGS'   ][0], _showSettingsMenu),
			(MENU_ENTRIES[ 'QUITGAME'   ][0], _quitGame) ]

		_setMainMenu(mainMenuItems, 'MAINMENU')
		_showUserNameEdit(False)

def _quitGame():
	global rds
	# When someone choose to exit when running from OpenAutomate they should just get back to the game
	if OpenAutomate.runFromOpenAutomate:
		OpenAutomate.setupOpenAutomateMainLoop(10, False, True).run()
		return
	_showLoadingBar(False)
	showAdvertisingScreen( 30.0, BigWorld.quit )

def _testEngineFeatures():
	allOkay = True
	for featureKey, active, options, desc in BigWorld.graphicsSettings():
		if options and not options[0][1]:
			allOkay = False
			feature = desc
			if options[0][0] == 'On' and options[1][0] == 'Off':
				addMsg('%s not supported (turning it off)' % feature)
			else:
				addMsg('%s not fully supported (using %s)' % (feature, options[active][0]))
	if allOkay:
		addMsg('Engine features fully supported on this system')


@BWCoroutine
def _finishMainMenu():
	'''Clears the menu stack.
	'''

	gui = rds.startupGUI
	gui.fader.alpha = 0
	yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( False, 0 ) )
	gui.script.active(False)

	rds.mainMenuGUI.script.active(False)

	try:
		yield BWWaitForCoroutine( MenuScreenSpace.fini(), timeout = 120 )
	except BWCoroutineTimeoutException:
		disconnectFromServer()
		return


# this function tries to get the current menu index
# if there is no current menu index it returns 0
def _indexInMenu():
	global rds
	try:
		return rds.mainMenuGUI.script.selection
	except:
		return 0

def _pushMainMenu(indexInPrevMenu = -1):
	'''Pushes the current menu into the menu stack.
	Params:
		indexInPrevMenu		index of item to be selected when returning
									from this menu to parent menu
	'''
	global rds
	if indexInPrevMenu == -1:
		indexInPrevMenu = _indexInMenu()

	rds.menuStack.append((None, [], indexInPrevMenu, None, lambda x: None))


def _setMainMenu(
	menuItems, caption, backFunc = lambda: True, selectedItem = 0, selectItemCallback = lambda x: None):
	'''Sets and shows current main menu items.
	'''
	global rds

	def chainedBackFunc():
		if backFunc():
			_popMainMenu()

	if len(rds.menuStack) > 1 and backFunc is not None:
		callbackFunc = chainedBackFunc
	else:
		callbackFunc = None

	# a menu may wish not to change the caption set by it's previous
	# menu (by passing it None). In this case, save the caption of the
	# previous menu so it can be restored (if None was saved, it would
	# use the same caption of the forecoming menu when poping back.
	if caption is not None:
		pushedCaption = caption
	else:
		assert len(rds.menuStack) > 1
		pushedCaption = rds.menuStack[-2][3]

	rds.menuStack[-1] = (callbackFunc, menuItems,
						rds.menuStack[-1][2], pushedCaption, selectItemCallback)

	_createMainMenu( callbackFunc, menuItems, selectedItem, caption, selectItemCallback )


def _popMainMenu():
	'''Pops the topmost menu from the menu stack and shows it.
	'''
	global rds
	previousMenu = rds.menuStack.pop()
	# selection index to go to is on the top of the stack,
	# so modify the current menu so it goes back to the right selection
	currentMenu  = list(rds.menuStack[-1][:])
	currentMenu[2] = previousMenu[2]
	_createMainMenu( *currentMenu )


def _createMainMenu(callbackFunc, menuItems, itemIndex, caption, selectItemCallback ):
	'''Creates the main menu from the given parameters.
	'''
	global rds

	# append a back option if menu is not the
	# root and if first option is selectable
	items = menuItems[:]
	if len(rds.menuStack) > 1 and items[0][1]:
		items.append(('<back>', callbackFunc))

	rds.mainMenuGUI.script.selectItemCallback = selectItemCallback
	rds.mainMenuGUI.script.active(True)
	rds.mainMenuGUI.script.setupItems(callbackFunc, items)
	rds.mainMenuGUI.items.script.scrollTo(0, 0)
	rds.mainMenuGUI.items.script.scrollTransform.setIdentity()
	rds.mainMenuGUI.items.transform.reset()
	rds.mainMenuGUI.script.selectItem(itemIndex, animate=False, forceReselect=True)
	rds.startupGUI.script.doLayout( None )
	if caption:
		BigWorld.worldDrawEnabled( False )
		rds.menuCaptionsGUI.title.textureName = MENU_ENTRIES[ caption ][1]
		rds.menuCaptionsGUI.help.textureName = MENU_ENTRIES[ caption ][2]
		BigWorld.worldDrawEnabled( True )


def _showXMLServersMenu():
	'''Shows menu with all hosts listed in
	scripts_config.xml file under the <login>/<host> field.
	'''
	xmlServers  = rds.scriptsConfig.readStrings('login/host')
	menuEntries = _createHostsItems(zip(xmlServers, xmlServers))

	_pushMainMenu()
	_setMainMenu(menuEntries, 'XMLSERVERS')


def _showLanServersMenu():
	'''Activates menu with list of lan servers. The menu is
	populated using bigWorld server discovery feature. Uses
	the _serversDiscovered function to actually build the menu.
	'''
	global rds
	rds.menuUpdatesAllow = False

	def _startSearchingForServers():
		_setMainMenu(
			[('Searching for servers on local network', None)],
			'LANSERVERS', _stopSearchAndGoPreviousMenu)

		BigWorld.serverDiscovery.searching = 1
		BigWorld.serverDiscovery.changeNotifier = _serversDiscovered
		BigWorld.callback(0.5, _menuUpdatesAllow)

	def _stopSearchAndGoPreviousMenu():
		rds.menuUpdatesAllow = False
		BigWorld.serverDiscovery.searching = 0
		return True

	def _serversDiscovered():
		'''Callback function called by BigWorld server discovery mechanism
		(from _lanServersMenu). Each time it is triggered, the lan servers
		menu is recreated with the updated servers information.
		'''
		if not rds.menuUpdatesAllow:
			return

		lastUsedServerUID = rds.userPreferences.readInt('lastServer/uid')

		lanServers = [
			(_serverNiceName(server), _serverNetName(server))
			for server in BigWorld.serverDiscovery.servers if server.uid == lastUsedServerUID ]

		lanServers = lanServers + [
			(_serverNiceName(server), _serverNetName(server))
			for server in BigWorld.serverDiscovery.servers if server.uid != lastUsedServerUID ]

		_setMainMenu(
			_createHostsItems(lanServers, _startSearchingForServers), 'LANSERVERS',
			_stopSearchAndGoPreviousMenu)

	def _menuUpdatesAllow():
		if BigWorld.serverDiscovery.searching:
			rds.menuUpdatesAllow = True
			if len(BigWorld.serverDiscovery.servers) > 0:
				_serversDiscovered()
			else:
				BigWorld.callback(1.5, _noServersFound)

	def _noServersFound():
		if rds.menuUpdatesAllow and \
				BigWorld.serverDiscovery.searching and \
					len(BigWorld.serverDiscovery.servers) == 0:
			_setMainMenu(
				[('No servers found on local network', None)],
				'LANSERVERS')
			BigWorld.serverDiscovery.searching = 0
			rds.menuUpdatesAllow = False

	_pushMainMenu()
	_startSearchingForServers()

def _createHostsItems(servers_list, abortCallback=None):
	'''Creates list of host menu items from a list of
	2-tuples (human readable label, connection callback).
	'''
	server_items = []
	for i, (label, host) in enumerate(servers_list):
		server_items.append((label,
				partial(_inputUserNameAndConnect, host, label, i, abortCallback)))
	return server_items


def _showUserNameEdit(visible):
	'''Shows/hides a edit field for input of username.
	'''
	global rds
	rds.usernameGUI.visible = visible
	rds.editField.script.active(visible)
	if visible:
		#set the key focus to the edit field.
		PyGUI.setFocusedComponent( rds.editField )

def _inputUserNameAndConnect( host, label, index, abortCallback = None, allowEscape=True ):
	'''Asks for username. Try to connect to
	given host after <enter> key is pressed.
	'''
	global rds
	rds.menuUpdatesAllow = False

	def _saveNameAndConnect(username):
		username = string.strip( username )
		if username != '':
			rds.userPreferences.writeWideString('lastUsedAccountName', unicode(username))

			rds.userPreferences.write( 'lastServer', '' )

			for i in BigWorld.serverDiscovery.servers:
				if _serverNetName( i ) == host:
					'''
					Although only the uid is currently used. The full server
					info is saved for completeness and to assist in debugging.
					'''
					rds.userPreferences.writeString(	'lastServer/hostName',		i.hostName )
					rds.userPreferences.writeString(	'lastServer/ip',			_serverDottedHost( i.ip ) )
					rds.userPreferences.writeString(	'lastServer/ownerName',		i.ownerName )
					rds.userPreferences.writeInt(		'lastServer/port',			i.port )
					rds.userPreferences.writeString(	'lastServer/spaceName',		i.spaceName )
					rds.userPreferences.writeInt(		'lastServer/uid',			i.uid )
					rds.userPreferences.writeString(	'lastServer/universeName',	i.universeName )
					rds.userPreferences.writeInt(		'lastServer/usersCount',	i.usersCount )

			BigWorld.savePreferences()
			_connectToServer(host, label, str(username))
			_showUserNameEdit(False)

	def _goBackToServersMenu():
		_popMainMenu()
		_showUserNameEdit(False)
		if abortCallback:
			abortCallback()

	BigWorld.worldDrawEnabled( False )
	if len(rds.menuStack) == 1:
		rds.menuCaptionsGUI.help.textureName = HELP_EDIT_NOBACK
	else:
		rds.menuCaptionsGUI.help.textureName = HELP_EDIT
	BigWorld.worldDrawEnabled( True )
		
	_pushMainMenu()
	_setMainMenu([('Enter a new or existing Account name:', None)], None, None)
	
	rds.editField.script.setText( rds.li.username )
	rds.editField.script.onEnter  = _saveNameAndConnect
	rds.editField.script.onEscape = _goBackToServersMenu if allowEscape else None
	_showUserNameEdit(True)


@BWCoroutine
def _showRealmSelectionScreen():

	# Wait until we have a player.
	try:
		yield BWWaitForCondition( lambda: BigWorld.player() != None, timeout = 120 )
	except BWCoroutineTimeoutException, e:
		disconnectFromServer()
		return

	# If it's already an avatar, then go straight into the game
	if isinstance( BigWorld.player(), Avatar.Avatar ):
		_proceedTooLevel().run()
		return

	assert isinstance( BigWorld.player(), Account.Account )

	BigWorld.player().selectedRealm = ""

	@BWCoroutine
	def onRealmSelect( selectedRealm ):
		BigWorld.player().base.selectRealm( selectedRealm )

		_setMainMenu( [ ('Retrieving Character List', None ) ], None, None )

		try:
			yield BWWaitForCondition( lambda: BigWorld.player().selectedRealm == selectedRealm, timeout = 120 )
		except BWCoroutineTimeoutException, e:
			disconnectFromServer()
			return

		_showCharacterSelectionScreen().run()

	# If we only have one realm, then proceed directly to the character selection list.
	if len(FantasyDemoData.REALMS) == 1:
		onRealmSelect( FantasyDemoData.REALMS.keys()[0] ).run()
	else:
		menuList = [ (realm.displayName, onRealmSelect( realm.name ).run ) for realm in FantasyDemoData.REALMS.values() ]
		_setMainMenu( menuList, 'REALMSELECT', disconnectFromServer )

@BWCoroutine
def _showCharacterSelectionScreen():

	if isinstance( BigWorld.player(), Avatar.Avatar ):
		_proceedTooLevel().run()
		return

	assert BigWorld.player() == None or isinstance( BigWorld.player(), Account.Account )

	@BWCoroutine
	def onCharacterSelect( characterName ):
		if BigWorld.server() is None:
			disconnectFromServer()
			return

		_setMainMenu( [ ('Retrieving Character', None ) ], None, None )
		rds.userPreferences.writeString('lastPlayedAvatar', characterName )

		yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( False ) )

		BigWorld.player().characterBeginPlay( str( characterName ) )

		_proceedTooLevel().run()


	@BWCoroutine
	def onCancel():
		# Only go back to the realm selection screen if we have more than one realm.
		if len(FantasyDemoData.REALMS) > 1:
			yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( False ) )
			_showRealmSelectionScreen().run()
		else:
			disconnectFromServer()


	def onChangeCurrentSelection( avatarModels, index ):
		try:
			if index >= 1 and index <= len( avatarModels ):
				MenuScreenSpace.setRealmAvatarModel( BigWorld.player().selectedRealm, avatarModels[index - 1] )
			else:
				MenuScreenSpace.setRealmAvatarModel( BigWorld.player().selectedRealm, AvatarModel.defaultModel() )
		except Exception, e:
			print e


	_setMainMenu( [ ('Waiting for Character List', None ) ], 'CHARACTERSELECT', None )

	try:
		yield BWWaitForCondition( lambda: BigWorld.player() != None, timeout = 120 )
	except BWCoroutineTimeoutException, e:
		disconnectFromServer()
		return

	if BigWorld.server() is None:
		return
		
	yield BWWaitForCondition( lambda: MenuScreenSpace.g_loaded )
	MenuScreenSpace.setRealmCamera( BigWorld.player().selectedRealm )
	yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( True ) )

	initialSelection = 0
	lastPlayedAvatar = rds.userPreferences.readString('lastPlayedAvatar')
	menuList = [ ('<Create Character>', _showCharacterCreationScreen) ]
	for characterInfo in BigWorld.player().characterList:
		menuList.append( (characterInfo['name'], onCharacterSelect( characterInfo['name'] ).run) )
		if characterInfo['name'] == lastPlayedAvatar:
			initialSelection = BigWorld.player().characterList.index( characterInfo ) + 1

	unpackedCharacterModels = [AvatarModel.unpack( character['characterModel'] ) for character in BigWorld.player().characterList]
	selectionCallbackObject = partial( onChangeCurrentSelection, unpackedCharacterModels )
	_setMainMenu( menuList, 'CHARACTERSELECT', onCancel().run, initialSelection, selectionCallbackObject)


def _showCharacterCreationScreen():
	'''Asks for a character name. Try to add a new character to the account.
	'''
	def _createCharacter( characterName ):
		characterName = string.strip( characterName )
		if characterName != '':
			def finishCharacterCreate( succeded, msg ):
				if succeded:
					_popMainMenu()
					_setMainMenu([(msg, None)], None, None)
				else:
					_displayErrorInMenu( msg )

				if not succeded:
					BigWorld.callback( 3.0, _showCharacterSelectionScreen().run )
				else:
					_showCharacterSelectionScreen().run()

			BigWorld.player().createNewCharacter( str(characterName), finishCharacterCreate )
			_showUserNameEdit(False)

	def _cancelCharacterCreate():
		_popMainMenu()
		_showUserNameEdit(False)

	_pushMainMenu()
	_setMainMenu([('Character name:', None)], 'CHARACTERCREATE', None)

	rds.editField.script.setText( '' )
	rds.editField.script.onEnter  = _createCharacter
	rds.editField.script.onEscape = _cancelCharacterCreate
	_showUserNameEdit(True)


def onCreateAvatarFailed():
	print 'Avatar.clientOnCreateCellFailure'
	_setMainMenu( [ ( 'Failed to Retrieve Character', None ),
					( 'Logging Out', None ) ], None, None )
	BigWorld.callback( 5.0, disconnectFromServer )


def _connectToServer(host, label, username):
	'''Callback triggered when the user choses a server
	from the servers menu. Tries to connect to it.
	'''
	global rds

	message1 = 'Server: %s ' % label
	message2 = 'Account name: %s' % username
	_setMainMenu([(message1, None), (message2, None)], None, None)
	addMsg(message1 + message2)

	if BigWorld.server() is not None:
		disconnectFromServer()

	rds.li.username = username
	rds.li.password = "pass" 	# this has an even number of characters to pass
								# the stub billing request: see the
								# AsyncBillingRequest class in the
								# base/Account.py module.
	BigWorld.serverDiscovery.searching = 0

	def doConnect():
		BigWorld.resetEntityManager( False, True )
		BigWorld.clearAllSpaces( True )
		BigWorld.connect(host, rds.li, _connectionCallback)

	BigWorld.callback(1.5, doConnect)


def _showOfflineSpacesMenu():
	'''Shows menu with all spaces listed in
	the space root directory (res/spaces).
	'''
	_pushMainMenu()
	_setMainMenu(enumOfflineSpaces(), 'OFFLSPACES')


def enumOfflineSpaces():
	'''Enumerates all spaces listed in the space root
	directory (res/spaces). Return them as menu-item
	2-tuples (human readable label, connection callback).
	'''
	global rds

	@BWCoroutine
	def _onSpaceChosen( spaceDescriptor ):
		BigWorld.serverDiscovery.searching = 0

		message = 'Exploring offline space: %s' % spaceDescriptor[0]
		_setMainMenu([(message, None)], None, None)

		yield BWWaitForCondition( lambda: MenuScreenSpace.g_loaded )
		BigWorld.resetEntityManager( False, True )
		BigWorld.clearAllSpaces( True )
		BigWorld.connect('', '', _connectionCallback)
		BigWorld.callback(1.0, lambda: _exploreOffline( spaceDescriptor[1] ))

	# list spaces
	if rds.offlineSpaces is None:
		spacesRoot = 'spaces'
		rds.offlineSpaces = []
		for direct in ResMgr.openSection(spacesRoot).values():
			if direct.has_key('space.settings'):
				# since resmgr does not support
				name = '%s/%s' % (spacesRoot, direct.name)
				printName = name

				# if the printName can not be converted to unicode, we give it the value Invalid Characters
				# the space will still work, we just don't know how to display its name
				try:
					unicode(printName)
				except UnicodeDecodeError:
					printName = '%s/%s' % (spacesRoot,'<Invalid Characters>')

				if name not in FantasyDemoData.OFFLINE_MODE_IGNORED_SPACES:
					rds.offlineSpaces.append( (printName, name) )

	spaces = []
	for space in rds.offlineSpaces:
		spaces.append( (space[0], _onSpaceChosen( space ).run) )

	return spaces


@BWCoroutine
def _proceedTooLevel():
	'''Put up the loading screen and wait for the level to load.
	'''

	if BigWorld.server() is None:
		disconnectFromServer()
		return


	_showLogoScreen( True, False )
	yield BWWaitForPeriod( 2.0 )


	yield BWWaitForCoroutine( setMainMenuActive( False ) )

	try:
		yield BWWaitForCondition( lambda: BigWorld.player() and BigWorld.player().inWorld, timeout = 120 )
	except BWCoroutineTimeoutException:
		disconnectFromServer()
		return

	def loadFinished():
		# connection may have been
		# cancelled half way through
		if BigWorld.server() is None:
			setMainMenuActive( True ).run()

		_showLoadingBar( False )
		_showLogoScreen( False )

	_startChunkLoadingBar( loadFinished )
	_showLoadingBar( True )
	rds.selfDisconnect = False


def _exploreOffline(spaceName, doConnectionCallback = True):
	'''Callback triggered when the user choses a space from
	the offline spaces menu. Loads the space and run offline.
	'''
	global rds

	message = 'Exploring offline space: %s' % spaceName
	addMsg(message)

	if rds.clientSpace is not None:
		BigWorld.releaseSpace(rds.clientSpace)
		rds.clientSpace = None

	rds.clientSpaceName = spaceName
	rds.clientSpace = BigWorld.createSpace()

	try:
		rds.clientSpaceMapping = BigWorld.addSpaceGeometryMapping(
			rds.clientSpace, None, rds.clientSpaceName)
	except ValueError:
		message = 'Could not load space: %s' % spaceName
		addMsg(message)
		BigWorld.releaseSpace(rds.clientSpace)
		rds.clientSpace = None
		_popMainMenu()
		return

	startPosition = rds.scriptsConfig._player._startPosition.asVector3
	startDirection = rds.scriptsConfig._player._startDirection.asVector3
	try:
		ssect = ResMgr.openSection(spaceName + '/space.settings')
		startPosition = ssect._startPosition.asVector3
		startDirection = ssect._startDirection.asVector3
	except:
		pass

	playerModel = PlayerModel.defaultPlayerModel()

	etype = rds.scriptsConfig._player._class.asString
	BigWorld.createEntity( etype, rds.clientSpace, 0,
		startPosition, startDirection, {'avatarModel':AvatarModel.pack( playerModel )})

	BigWorld.timeOfDay(rds.offlineTimeOfDay)

	# we have 'connected' now ... locally as it were
	if doConnectionCallback == True:
		_connectionCallback(1, 'CUSTOM_MSG', 'Single user mode')

	# pretend we did get data too.
	# C01: stage = 2 / status = 'OFFLINE' is never generated by BigWorld
	# It's been used here to signed the connection callback that
	# we're running offline, so it changes the time of day just
	# before hiding the loading screen (I'd prefer setting it
	# here, but this is crashing the client).
	if doConnectionCallback == True:
		BigWorld.callback(2, lambda: _connectionCallback(2, 'OFFLINE', ''))

	BigWorld.player().onChangeEnvironments( False )

#########################
# The settings menues   #
#########################

# this function sets up and shows the settings menu
def _showSettingsMenu(selectedItem = 0):
	'''????
	'''
	def _getGraphicDetailStatus():
		presets = GraphicsPresets()
		if presets.selectedOption >= 0:
			return "[" + presets.entryNames[ presets.selectedOption ] + "]"
		else:
			return "[Custom]"


	_pushMainMenu()

	menuitems = [ ('Video...', _showVideoSettingsMenu),
				('Graphics Detail...', _showDetailSettingsMenu, _getGraphicDetailStatus),
				('Auto-Detect Graphics Detail', _autoDetectGraphicsSettings)]

	_setMainMenu( menuitems, 'SETTINGS', partial(_updateSettingsForceRestart, _refreshDetailSettingsMenu), selectedItem )

# This function sets up and displays the detail settings menu
def _showDetailSettingsMenu(selectedItem = 0):
	'''
	'''
	def _togglePresets(presets, optionIndex):
		presets.selectGraphicsOptions( optionIndex )
		_updateSettings( callback = _refreshDetailSettingsMenu )

	def _exitSettingsMenu():
		BigWorld.savePreferences()
		return True, selectedItem

	_pushMainMenu()

	presets = GraphicsPresets()

	advancedMsg = 'Advanced Settings...'
	if presets.selectedOption == -1:
		advancedMsg += ' *'

	menuitems = []

	for i in range(0, len(presets.entryNames)):
		presetMsg = presets.entryNames[i]
		if i == presets.selectedOption:
			presetMsg += ' *'
		menuitems.append( ( presetMsg,
							partial( _togglePresets, presets, i )))

	menuitems.append( (advancedMsg,   _showAdvancedSettingsMenu) )

	_setMainMenu( menuitems,
				'SETTINGS', _exitSettingsMenu, selectedItem)

# This funtion refreshes the contents of the of the detail settings menu
def _refreshDetailSettingsMenu():
	indexInPrevMenu = _indexInMenu()
	_popMainMenu()
	_showDetailSettingsMenu(indexInPrevMenu)

# This function refreshes the contents of the graphic settings menu
def _refreshSettingsMenu():
	indexInPrevMenu = _indexInMenu()
	_popMainMenu()
	_showSettingsMenu(indexInPrevMenu)

# This funtion refreshes the contents of the of the detail settings menu
def _refreshDetailSettingsMenu():
	indexInPrevMenu = _indexInMenu()
	_popMainMenu()
	_showDetailSettingsMenu(indexInPrevMenu)

# This function commits any pending graphics settings
def _commitSettings(callback):
	BigWorld.commitPendingGraphicsSettings()
	callback()

# This function checks for pending graphics settings
def _checkPending(callback):
	if BigWorld.hasPendingGraphicsSettings():
		_setMainMenu([('Applying new settings...', None)], None)
		BigWorld.callback(0.1, partial(_commitSettings, callback))
	else:
		callback()

# This function updates the graphics settings
def _updateSettings(callback):
	BigWorld.savePreferences()
	if BigWorld.graphicsSettingsNeedRestart():
		menu = [
			('New settings require restarting game ', None),
			('Restart now', BigWorld.restartGame),
			('Restart later', partial(_checkPending, callback) )]
		_setMainMenu(menu, None, lambda: True, 1)
	else:
		_checkPending(callback)

def _updateSettingsForceRestart(callback):
	BigWorld.savePreferences()
	if BigWorld.graphicsSettingsNeedRestart():
		global rds
		menu = [
			('New settings require restarting game ', None),
			(MENU_ENTRIES[ 'SETTINGS' ][0], _showSettingsMenu),
			(MENU_ENTRIES[ 'RESTART'  ][0], BigWorld.restartGame),
			(MENU_ENTRIES[ 'QUITGAME' ][0], _quitGame) ]

		rds.menuStack = []
		_pushMainMenu()
		_setMainMenu(menu, 'RESTART', lambda: False, 1)
		return False
	else:
		_checkPending(callback)
		return True

# This function sets up and shows the video settings menu
def _showVideoSettingsMenu(selectedItem = 0):
	def _refreshVideoSettingsMenu():
		indexInPrevMenu = _indexInMenu()
		_popMainMenu()
		delDeviceListener(rds.refreshMenu)
		_showVideoSettingsMenu(indexInPrevMenu)


	# Local functions used by the settings menu
	def _toggleWindowed():
		curModeIdx = BigWorld.videoModeIndex()
		BigWorld.changeVideoMode(curModeIdx, not BigWorld.isVideoWindowed())
		_refreshVideoSettingsMenu()

	def _exitSettingsMenu():
		BigWorld.savePreferences()
		delDeviceListener(rds.refreshMenu)
		return True, selectedItem

	def _selectOnOffText( boolFn ):
		return ["[Off]", "[On]"][int(boolFn())]

	def _getAspectRatioStatus():
		ratios, current = _enumAspectRatios()
		if current >= 0:
			return "[" + ratios[current][0] + "]"
		else:
			return ""

	def _getResolutionStatus():
		return "[%dx%d]" % BigWorld.screenSize()

	# resolution strings
	if BigWorld.isVideoWindowed():
		toggleWindowedMsg = 'Switch to Full Screen'
		resolutionText    = 'Select Window Size...'
	else:
		toggleWindowedMsg = 'Switch to Windowed Mode'
		resolutionText    = 'Select Resolution...'

	_pushMainMenu()

	menuitems = [ (toggleWindowedMsg,     _toggleWindowed),
				(resolutionText,        _showVideoModesMenu, _getResolutionStatus),
				('Select Fullscreen Aspect Ratio...', _showAspectRatioMenu, _getAspectRatioStatus),
				('Vertical Sync...', _showVSyncMenu, partial( _selectOnOffText, BigWorld.isVideoVSync) ),
				('Triple Buffering...', _showTripleBufferMenu, partial( _selectOnOffText, BigWorld.isTripleBuffered ) ),
				]

	_setMainMenu( menuitems,
				'SETTINGS', _exitSettingsMenu, selectedItem)

	class RefreshMenu:
		def __init__(self):
			self.enabled = True

		def onRecreateDevice(self):
			if self.enabled:
				_refreshVideoSettingsMenu()
			else:
				self.enabled = True

		def disableOnce(self):
			self.enabled = False

	global rds
	rds.refreshMenu = RefreshMenu()
	addDeviceListener(rds.refreshMenu)

def _setAspectRatio(ratio):
	BigWorld.changeFullScreenAspectRatio(ratio)
	rds.fdgui.chooseResolutionBracket()
	_popMainMenu()

def _enumAspectRatios():
	ratios = [
		(16, 9, None),
		(4, 3, None),
		(16, 10, 'Dell'),
		(5, 4, None)]

	ratiosMenu = []
	currentlySelected = 0
	current = 0
	currentAspectRatio = BigWorld.getFullScreenAspectRatio()
	for x, y, comment in ratios:
		desc = '%d:%d' % (x, y)
		if comment:
			desc += ' (%s)' % comment
		ratio = float(x)/y
		ratiosMenu.append((desc, partial(_setAspectRatio, ratio)))
		if abs(ratio - currentAspectRatio) < 0.01:
			currentlySelected = current
		current += 1
	return (ratiosMenu,currentlySelected)

def _showAspectRatioMenu():
	_pushMainMenu()
	menu, current = _enumAspectRatios()
	_setMainMenu( menu, 'SETTINGS', lambda: True, current)


def _showVSyncMenu():
	def _selectVSync( enable ):
		BigWorld.setVideoVSync( enable )
		_popMainMenu()

	_pushMainMenu()
	menuitems = [ ("Off",     partial( _selectVSync, False ) ),
				  ("On",     partial( _selectVSync, True ) ) ]
	_setMainMenu( menuitems,
				'SETTINGS', lambda: True, int(BigWorld.isVideoVSync()) )


def _showTripleBufferMenu():
	def _selectTripleBuffered( enable ):
		BigWorld.setTripleBuffering( enable )
		_popMainMenu()

	_pushMainMenu()
	menuitems = [ ("Off",    partial( _selectTripleBuffered, False ) ),
				  ("On",     partial( _selectTripleBuffered, True ) ) ]
	_setMainMenu( menuitems,
				'SETTINGS', lambda: True, int(BigWorld.isTripleBuffered()) )

def _showVideoModesMenu():
	_pushMainMenu()
	modes, current = enumVideoModes()
	_setMainMenu(modes, 'SETTINGS', lambda: True, current)


def enumVideoModes():
	def _changeMode(mode):
		if not OpenAutomate.openAutomateMode:
			rds.refreshMenu.disableOnce()
			if BigWorld.isVideoWindowed():
				BigWorld.resizeWindow(mode[1], mode[2])
			else:
				BigWorld.changeVideoMode(mode[0], False)
			_popMainMenu()
		else:
			#For open automate we set both mode as we might be running a test on a different mode soon
			#also no need to change menus
			OpenAutomate.changeMode(mode)

	modes = []
	current = 0
	#if we can't find the current mode (as on some screens a 
    #WindowedMode gives us a window which is a bit smaller than what we ask)
	#we use the closest mode.
	bestModeFound = 0
	minimalModeDifference = 10000
	foundCurrentMode = False
	for mode in BigWorld.listVideoModes():
		if mode[3] == 32:
			modes.append((mode[4], partial(_changeMode, mode)))
			if BigWorld.isVideoWindowed():
				w, h = BigWorld.windowSize()
				modeDifference = abs(mode[1]-int(w)) + abs(mode[2]-int(h))
				if modeDifference == 0:
					current = len(modes)-1
					foundCurrentMode = True
				if modeDifference < minimalModeDifference:
					bestModeFound = len(modes)-1
					minimalModeDifference = modeDifference
			else:
				if mode[0] == BigWorld.videoModeIndex():
					current = len(modes)-1
					foundCurrentMode = True
	if not foundCurrentMode:
		current = bestModeFound

	return modes, current


def _autoDetectGraphicsSettings():
	BigWorld.autoDetectGraphicsSettings()
	rds.console.script.addMsg( "The most optimal settings have been selected for your video card to balance performance and fidelity.", 0 )
	_updateSettings( callback = _refreshSettingsMenu )


def _showAdvancedSettingsMenu():
	def _showAdvSubMenu(settingIndex, settingId):
		def _setGraphicsSetting(settingId, optionIndex):
			BigWorld.setGraphicsSetting(settingId, optionIndex)
			_popMainMenu()

		def _makeCallBack(optionIndex, supported):
			if supported:
				return lambda: _setGraphicsSetting(settingId, optionIndex)
			else:
				return None

		_pushMainMenu()
		setting = BigWorld.graphicsSettings()[settingIndex]
		active  = setting[1]
		options = setting[2]
		desc = setting[3]
		settingsSubMenu = [
			(desc, _makeCallBack(index, supported))
			for index, (option, supported, desc)
			in enumerate(options)]

		_setMainMenu(settingsSubMenu, 'SETTINGS', lambda: True, active)

	def _exitAdvancedSettings():
		_popMainMenu()
		_updateSettings( callback = _refreshDetailSettingsMenu )
		return False

	def _getStatusString( settingIndex ):
		graphicSetting = BigWorld.graphicsSettings()[settingIndex]
		activeIdx = graphicSetting[1]
		return "[" + graphicSetting[2][activeIdx][2] + "]"

	_pushMainMenu()
	graphicSettings = BigWorld.graphicsSettings()
	settingsMenu = [
		(str(desc)+"...", partial(_showAdvSubMenu, index, settingId), partial( _getStatusString, index ) )
		for index, (settingId, active, options, desc)
		in enumerate(graphicSettings)]

	_setMainMenu(settingsMenu, 'SETTINGS', _exitAdvancedSettings)


def _displayErrorInMenu(msg):
	errorMsg = []
	while len(msg):
		if len(msg) <= MAX_ERROR_LEN:
			errorMsg.append((msg, None))
			break

		spcPos = msg.rfind(' ', 0, MAX_ERROR_LEN)
		if spcPos == -1:
			spcPos = MAX_ERROR_LEN

		errorMsg.append((msg[:spcPos], None))
		msg = msg[spcPos+1:]

	for i, (msg, func) in enumerate(errorMsg[1:]):
		errorMsg[i+1] = (msg, func)
	_setMainMenu(errorMsg, 'MAINMENU', disconnectFromServer)


def _connectionCallback(stage, status, serverMsg):
	'''Callback trig by BigWorld to report on the status of the connection.
	Logs the status in the console and update the GUI accordingly.
	'''
	loginErrorStrs = {
		'NOT_SET'										: 'Not set',
		'LOGGED_ON'										: 'Account Login succeeded',
		'CONNECTION_FAILED'							: 'Login failed: Unable to contact login server',
		'DNS_LOOKUP_FAILED'							: 'Login failed: DNS lookup failed',
		'UNKNOWN_ERROR'								: 'Login failed: Unknown local client error',
		'CANCELLED'										: 'Login failed: Login cancelled',
		'ALREADY_ONLINE_LOCALLY'					: 'Login failed: Already online',
		'PUBLIC_KEY_LOOKUP_FAILED'					: 'Login failed: Public key lookup failed',
		'LOGIN_MALFORMED_REQUEST'					: 'Login failed: Malformed login request',
		'LOGIN_BAD_PROTOCOL_VERSION'				: 'Login failed: Wrong protocol version',
		'LOGIN_REJECTED_NO_SUCH_USER'				: 'Login failed: No such user: %(username)s',
		'LOGIN_REJECTED_INVALID_PASSWORD'		: 'Login failed: Invalid password',
		'LOGIN_REJECTED_ALREADY_LOGGED_IN'		: 'Login failed: Someone with account name %(username)s already logged in',
		'LOGIN_REJECTED_BAD_DIGEST'				: "Login failed: Client .def files do not match server's",
		'LOGIN_REJECTED_DB_GENERAL_FAILURE'		: 'Login failed: Misc database rejection',
		'LOGIN_REJECTED_DB_NOT_READY'				: 'Login failed: Unable to contact server database',
		'LOGIN_REJECTED_ILLEGAL_CHARACTERS'		: 'Login failed: Illegal characters in user name/password',
		'LOGIN_REJECTED_SERVER_NOT_READY'		: 'Login failed: Server not ready',
		'LOGIN_REJECTED_UPDATER_NOT_READY'		: 'Login failed: Unable to contact Updater',
		'LOGIN_REJECTED_NO_BASEAPPS'				: 'Login failed: Unable to contact BaseApps',
		'LOGIN_REJECTED_BASEAPP_OVERLOAD'		: 'Login failed: BaseApp overloaded',
		'LOGIN_REJECTED_CELLAPP_OVERLOAD'		: 'Login failed: CellApp overloaded',
		'LOGIN_REJECTED_BASEAPP_TIMEOUT'			: 'Login failed: BaseApp timed-out',
		'LOGIN_REJECTED_BASEAPPMGR_TIMEOUT'		: 'Login failed: BaseAppMgr overloaded',
		'LOGIN_REJECTED_DBMGR_OVERLOAD'			: 'Login failed: Database overloaded',
		'LOGIN_REJECTED_LOGINS_NOT_ALLOWED'		: 'Login failed: Logins not allowed',
	}

	global rds
	if stage == 1 :
		defaultMsg = serverMsg if serverMsg else 'Unknown server error'
		errorMsg = loginErrorStrs.get(status, defaultMsg)
		errorMsg = errorMsg % rds.li.__dict__
		_displayErrorInMenu(errorMsg)
		addMsg(errorMsg)

	elif stage == 2:
		if status == 'OFFLINE':
			_proceedTooLevel().run()
		else:
			_showRealmSelectionScreen().run()

	elif stage == 6:
		handleDisconnectionFromServer().run()


@BWCoroutine
def handleDisconnectionFromServer():
	rds.fdgui.handleDisconnectionFromServer()
	rds.setFlyThroughMode( False )
	_showLoadingBar(False)
	_showLogoScreen( True, False )

	_deactivateChatWindow()

	rds.startupGUI.fader.alpha = 1.0
	yield BWWaitForCoroutine( rds.startupGUI.script.showCharacterScreen( False, 2.0 ) )

	if not OpenAutomate.openAutomateMode:
		_pushMainMenu()
		_setMainMenu( [ ('Disconnected from Server', None ) ], None, None )

		yield BWWaitForPeriod( 2.0 )

		while _mainMenuActiveCount > 0:
			yield BWWaitForCoroutine( setMainMenuActive( False ) )

		if rds.selfDisconnect:
			addMsg('Client disconnected itself from server')
		else:
			addMsg('Client lost connection to server')
	else:
		yield BWWaitForPeriod( 2.0 )
		#called from setMainMenuActive
		BigWorld.worldDrawEnabled( True )

	BigWorld.resetEntityManager( False, False )
	BigWorld.clearAllSpaces( False )

	yield BWWaitForPeriod( 0.5 )

	if not OpenAutomate.openAutomateMode:
		_setRootMenuMenuItems()

		yield BWWaitForCoroutine( setMainMenuActive( True ) )

	_showLogoScreen( False, True )
	disableWorldDrawing()


def disconnectFromServer():
	'''Disconnect client from server.
	'''

	if BigWorld.server() is not None:
		global rds
		rds.selfDisconnect = True
		# Temporary solution until there is an official function that
		# gets rid of the proxy on the base.
		if BigWorld.player() is not None:
			try:
				BigWorld.player().base.logOff()
			except:
				pass

		if rds.clientSpace != None:
			BigWorld.resetEntityManager()
			BigWorld.releaseSpace(rds.clientSpace)
			rds.clientSpaceMapping = None
			rds.clientSpace = None

		_showLogoScreen( True, False )

		BigWorld.disconnect()
	else:
		handleDisconnectionFromServer().run()

	Weather.weather().toggleRandomWeather( False )

def _serverNetName(details):
	'''Given a ServerDiscoveryDetails object,
	returns the network name for it.
	'''
	name = _serverDottedHost(details.ip)
	if details.port:
		name += ':%d' % details.port
	return name


def _serverNiceName(details):
	'''Given a ServerDiscoveryDetails object,
	returns a human readable name for it.
	'''
	name = details.hostName
	if not name:
		name = _serverDottedHost(details.ip)
	if details.port:
		name += ':%d' % details.port
	if details.ownerName:
		name += ' (' + details.ownerName + ')'
	return name


def _serverDottedHost(ip):
	'''Given a numeric IP address, returns a
	four digit, dot notation IP address.
	'''
	return '%d.%d.%d.%d' % (
		(ip>>24) & 0xFF,
		(ip>>16) & 0xFF,
		(ip>>8)  & 0xFF,
		(ip>>0)  & 0xFF)

############################################################################
# The following functions implement a loading screen overlay to hide the
# initial chunk loading phase.
############################################################################

def disableWorldDrawing():
	BigWorld.worldDrawEnabled(False)
	if BigWorld.player() and hasattr(BigWorld.player(), 'hud') and BigWorld.player().hud:
		GUI.delRoot(BigWorld.player().hud)

def enableWorldDrawing():
	BigWorld.worldDrawEnabled(True)
	if BigWorld.player() and hasattr(BigWorld.player(), 'hud') and BigWorld.player().hud:
		GUI.addRoot(BigWorld.player().hud)

def _exitAdvertisingScreen( callback ):
	global rds
	if rds.advertisingScreen != None:
		GUI.delRoot(rds.advertisingScreen)
		rds.advertisingScreen = None
		callback()

def showAdvertisingScreen( time, callback ):
	if BigWorld.isEval():
		global rds
		if rds.advertisingScreen == None:
			rds.advertisingScreen = GUI.load("gui/advertising_graphic.gui")
			disableWorldDrawing()
			rds.advertisingScreen.script.isActive = True
			rds.advertisingScreen.script.active(True)
			rds.advertisingScreen.script.onEscape = partial(_exitAdvertisingScreen, callback)
			GUI.addRoot(rds.advertisingScreen)
			BigWorld.callback( time-0.001, rds.advertisingScreen.script.onEscape )
	else:
		callback()


def _showLogoScreen( active, fadeIn = True ):
	'''Shows/hide the BigWorld logo screen.
	'''
	if fadeIn:
		fadeTime = rds.loadingScreen.fader.speed
	else:
		fadeTime = 0.0

	if active:
		rds.loadingScreen.fader.value = 1.0
		BigWorld.callback( fadeTime, disableWorldDrawing )
	else:
		rds.loadingScreen.fader.value = 0.0
		enableWorldDrawing()

	# If we're fading out, allow mouse clicks into the menu etc immediately.
	# Otherwise capture input.
	rds.loadingScreen.focus = active
	rds.loadingScreen.moveFocus = active

	BigWorld.callback( fadeTime, partial( rds.loadingScreen.script.active, active ) )
	if not fadeIn:
		rds.loadingScreen.fader.reset()

	return fadeTime



def _showLoadingBar(active):
	'''Shows/hide the loading bar.
	'''
	global rds
	rds.loadingScreen.bar.visible  = active
	rds.loadingScreen.back.visible = active
	if not active:
		rds.loadingScreen.script.cancel()


def _recommendSettings():
	# if timed out and a lower graphics setting exists then print out a message
	# to indicate this, unless the user cancelled the loading screen.

	if rds.loadingScreen.fader.value == 0.0:
		return

	presets	= GraphicsPresets()
	doNotify = False

	if presets.selectedOption == -1:
		doNotify = True
	else:
		for i in range(0, len(presets.entryNames)):
			presetMsg = presets.entryNames[i]
			if presetMsg != "Low" and presets.selectedOption == i:
				doNotify = True
				break

	if doNotify == True:
		addMsg("FantasyDemo loading timeout please try a lower graphics setting")


def _startChunkLoadingBar(finishedCallback):
	'''Starts the chunk loaing progress bar.
	'''
	global rds
	if rds.loadingScreen == None:
		rds.loadingScreen = GUI.load('gui/loading_screen.gui')

	rds.loadingScreen.script.setProgress(0)
	rds.loadingScreen.script.reset(0)

	def _finishedLoading( timedOut = False ):
		if timedOut:
			_recommendSettings()
		BigWorld.worldDrawEnabled(True)

		_activateChatWindow()

		rds.loadingScreen.script.reset(0)
		finishedCallback()

	# Loading progress bar measures first 500 metres
	rds.loadingScreen.script.start(500.0, _finishedLoading)
	addMsg('Loading World Data')

############################################################################
# The following functions implement a feature that times the loading of a
# space.
############################################################################

def _loadTimerStart( spaceName ):
	# Start loading requested space without loading screen
	startTime = time.time()
	_exploreOffline( spaceName, False )
	_showLogoScreen( False )

	# Start the callback chain to do the timing
	print "Load timer: Processing space '", spaceName, "'"
	BigWorld.callback( 1.0, partial( _loadTimerTick, spaceName, startTime ) )

def _loadTimerTick( spaceName, startTime ):
	s = BigWorld.spaceLoadStatus()
	if s < 1.0:
		# Tick
		print "Load timer: Space load status =", s
		BigWorld.callback( 1.0, partial( _loadTimerTick, spaceName, startTime ) )
	else:
		# End
		timeNow = time.time()
		elapsed = timeNow - startTime
		_loadTimerFinish( spaceName, elapsed )

def _loadTimerFinish( spaceName, elapsedTime ):

	# declare filename and default mode
	filename = "load_timer.csv"
	mode = "a"

	print "Load timer: Space loaded in", elapsedTime, "seconds. Writing results to", filename

	# open file and write
	f = open( filename, mode )
	try:
		f.write( '"' + spaceName + '","' + str(elapsedTime) + '",\n' )
	finally:
		f.close()

	# ... and quit so we can run again.
	BigWorld.quit()

############################################################################
# The following functions implement the automatic profiling
############################################################################

def runProfiler( spaceName, csvPrefix, exitOnComplete):
	# Start loading requested space without loading screen
	_exploreOffline( spaceName, False )
	_showLogoScreen( False )

	def _loadTick( spaceName, csvPrefix):
		if BigWorld.isBackgroundWorking() == True or _isFlightPathLoaded() == False:
			BigWorld.callback(1.0,partial(_loadTick,spaceName, csvPrefix))
		else:
			BigWorld.callback(1.0,partial(_runProfilerStart, spaceName, csvPrefix, exitOnComplete ) )

	BigWorld.callback(1.0,partial(_loadTick, spaceName, csvPrefix))

def _runProfilerStart ( spaceName, csvPrefix, exitOnComplete ):
	global rds
	rds.flyThroughMode = True
	BigWorld.runProfiler('camera node0', 1 , csvPrefix, exitOnComplete)

def _isFlightPathLoaded( ):
	"""
	Returns True if all the UDO CameraNodes in the flight path have finished loading, otherwise returns false.
	"""
	cameraNodes = [udo for udo in BigWorld.userDataObjects.values() if isinstance( udo, CameraNode.CameraNode )]
	startCamera = [cn for cn in cameraNodes if cn.name == 'camera node0']
	if len( startCamera ) != 1:
		if len( startCamera ) > 1:
			ERROR_MSG( "There are %d fly-through camera start nodes.  Please make sure there is only 1" % (len(startCamera),))
		return False
	else:
		startCamera = startCamera[0]
	try:
		nextCamera = startCamera.next
		while True:
			if nextCamera is None or nextCamera == startCamera:
				return True
			else:
				nextCamera = nextCamera.next
	except BigWorld.UnresolvedUDORefException:
		pass
	return False


# -----------------------------------------------------------------------------
# Method: onChangeEnvironments
# Description:
#	- This is called automatically when player moves from inside to outside
#	environment, or vice versa.
#	- It should be used to adapt any personality related data (eg, camera
#	position/nature, etc).
# -----------------------------------------------------------------------------
def onChangeEnvironments(inside):
	global rds
	rds.inside = inside
	rds.updatePivotDist()
	for listener in rds.environmentChangeListeners.keys():
		listener(inside)


def addChangeEnvironmentsListener(listener):
	global rds
	rds.environmentChangeListeners[listener] = ''


def delChangeEnvironmentsListener(listener):
	try:
		if 'rds' in globals():
			del rds.environmentChangeListeners[listener]
	except:
		pass


def onGeometryMapped(spaceID, spacePath):
	# If we are mapping urban, set the texture quality to medium so we don't run out of address space
	# This only gets done if we are currently running high texture quality
	if spacePath.lower() == 'spaces/urban' and BigWorld.getGraphicsSetting('TEXTURE_QUALITY') == 0:
		WARNING_MSG( 'Setting texture quality to medium as we are loading the Urban space' )
		oldWorldDraw = BigWorld.worldDrawEnabled()
		BigWorld.worldDrawEnabled(False)
		BigWorld.setGraphicsSetting( 'TEXTURE_QUALITY', 1 )
		BigWorld.commitPendingGraphicsSettings()
		BigWorld.worldDrawEnabled(oldWorldDraw)
		
	rds.spaceNameMap[spaceID] = spacePath
	onChangeEnvironments(False)
	if rds.clientSpace == spaceID:
		rds.clientSpaceName = spacePath
		online = BigWorld.server() if BigWorld.server() else 'offline'
		print 'Entering space: %s (server: %s)' % (spacePath, online)


def spaceName(spaceID):
	try:
		return rds.spaceNameMap[spaceID]
	except KeyError:
		return ""


# -----------------------------------------------------------------------------
# Method: onCameraSpaceChange
# Description:
#	- This is called automatically when the camera moves from one space to
#	another.
#	- The space ID and space.settings datasection is passed in to this function
# -----------------------------------------------------------------------------
def onCameraSpaceChange(spaceID, spaceSettings):
	global rds
	rds.cameraSpaceID = spaceID
	for listener in rds.cameraSpaceChangeListeners.keys():
		listener(spaceID,spaceSettings)


def addCameraSpaceChangeListener(listener):
	global rds
	rds.cameraSpaceChangeListeners[listener] = ''


def delCameraSpaceChangeListener(listener):
	global rds
	try:
		if 'rds' in globals():
			del rds.cameraSpaceChangeListeners[listener]
	except:
		pass


# -----------------------------------------------------------------------------
# Method: onRecreateDevice
# Description:
#	- This is called automatically when the D3D device is reset.
# -----------------------------------------------------------------------------
def onRecreateDevice():
	'''Called by BigWorld whenever the graphics device is reset
	(usually, after a screen resise or switching full screen mode).
	'''
	for listener in rds.deviceListeners.keys():
		listener.onRecreateDevice()

	rds.startupGUI.script.doLayout( None )
	if rds.advertisingScreen is not None:
		rds.advertisingScreen.script.doLayout( None )

	PyGUI.onRecreateDevice()


def addDeviceListener(listener):
	global rds
	rds.deviceListeners[listener] = ''


def delDeviceListener(listener):
	try:
		if 'rds' in globals():
			del rds.deviceListeners[listener]
	except:
		pass

# -----------------------------------------------------------------------------
# Method: onFlyThroughFinished
# Description:
#	- This is called when the camera fly-through has completed
# -----------------------------------------------------------------------------
def onFlyThroughFinished(resultList):
	global rds
	rds.flyThroughFinished(resultList)


# -----------------------------------------------------------------------------
# Method: enableEnvironmentSync
# Description:
#	- This method is a demo-only and enables environment synchronisation.
#	Server time of day and weather updates will be displayed on the client.
# -----------------------------------------------------------------------------
def enableEnvironmentSync():
	if hasattr( BigWorld, 'setEnvironmentSync' ):
		BigWorld.setEnvironmentSync( True )
		addMsg("Environment sync enabled")
		spaceID = BigWorld.player().spaceID
		BigWorld.player().cell.resyncServTime( spaceID )
		import Weather
		Weather.weather().summon( rds.lastWeatherSync[spaceID], \
											immediate = True, serverSync = True )


# -----------------------------------------------------------------------------
# Method: disableEnvironmentSync
# Description:
#	- This method is a demo-only and disables environment synchronisation.
#	Server time of day and weather updates will be ignored.
# -----------------------------------------------------------------------------
def disableEnvironmentSync():
	if hasattr( BigWorld, 'setEnvironmentSync' ):
		BigWorld.setEnvironmentSync( False )
		addMsg("Environment sync disabled")


# -----------------------------------------------------------------------------
# Method: onWeatherChange
# Description:
#	- This method is called when the weather space data is updated from the
#	server.  This feature is demo-only and is not compiled into the consumer
#	client release build.
# -----------------------------------------------------------------------------
def onWeatherChange( spaceID, weather ):
	import Helpers.ConsoleCommands

	global rds
	rds.lastWeatherSync[spaceID] = weather

	#If this is a weather change for the current space, then update the
	#weather gracefully (i.e. not immediate)
	if rds.cameraSpaceID == spaceID:
		try:
			apply = BigWorld.getEnvironmentSync()
		except KeyError:
			apply = True

		if apply:
			import Weather
			Weather.weather().summon( weather, immediate = False, serverSync = True )


# -----------------------------------------------------------------------------
# Method: fini
# Description:
#	- The fini function is called when the client is about to shutdown.  It
#		should be used to clean up the game.
# -----------------------------------------------------------------------------
def fini():
	global rds

	if BigWorld.player() != None:
		try:
			BigWorld.player().base.logOff()
		except:	pass
	BigWorld.disconnect()
	BigWorld.savePreferences()

	rds.fdgui.fini()

	import Weather
	Weather.fini()

	PostProcessing.fini()

	BigWorld.resetEntityManager()
	BigWorld.clearAllSpaces()

	rds.fini()

	del rds


# -----------------------------------------------------------------------------
# Method: onTimeOfDayLocalChange
# Description:
#	- This is called automatically when Time of Day changes on the client
#	- It should only be used to sync game time from client to server
# -----------------------------------------------------------------------------
def onTimeOfDayLocalChange( gameTimeInHrs, secondsPerGameHour ):
	global rds

	if hasattr( BigWorld, 'getEnvironmentSync' ):
		if not BigWorld.getEnvironmentSync():
			return

	if secondsPerGameHour > 0.0:
		gameSecondsPerSecond = 3600.0/secondsPerGameHour
	else:
		gameSecondsPerSecond = 0.0
	gameTimeInSeconds = gameTimeInHrs * 3600.0

	try:
		BigWorld.player().cell.syncServTime(
			BigWorld.player().spaceID,
			gameTimeInSeconds, gameSecondsPerSecond )
	except:
		pass


# -----------------------------------------------------------------------------
# Method: handleKeyEvent
# Description:
#	- This is called automatically when a key is pressed.
# -----------------------------------------------------------------------------
def handleKeyEvent( event ):
	global rds
	down = event.isKeyDown()
	#check for system event
	if down and event.key == KEY_F4 and event.isAltDown() and not BigWorld.isEmbedded:
		if BigWorld.player() != None:
			try:
				BigWorld.player().base.logOff()
			except:	pass

		_quitGame()
		return True
	elif down and event.key == KEY_RETURN and event.isAltDown() and not BigWorld.isEmbedded:
		BigWorld.changeVideoMode( BigWorld.videoModeIndex(), not BigWorld.isVideoWindowed() )
		return True

	PyGUI.handleKeyEvent( event )
	handled = GUI.handleKeyEvent( event )

	if handled:
		#remove focus from the inGameFocusedComponent so that if it grabs keyboard (mozilla) it will release the grab
		if rds.inGameFocusedComponent:
			rds.inGameFocusedComponent.setKeyFocus(False)
		return True
	#in this case, the GUI didn't grab the focus, therefore we cancel the GUI key focus status
	focusedComponent = PyGUI.getFocusedComponent()
	if down and event.isMouseButton() and focusedComponent is not None:
		if not hasattr( focusedComponent.script, "allowAutoDefocus" ) or focusedComponent.script.allowAutoDefocus():
			PyGUI.setFocusedComponent( None )

	#focused component is after GUI as a GUI element might be closer to the camera than the
	#inGameFocusedComponent
	if rds.inGameFocusedComponent:
		handled = rds.inGameFocusedComponent.handleKeyEvent( event )
		if handled:
			return True

	# try the camera
	cam = BigWorld.camera()
	if cam is not None:
		handled = cam.handleKeyEvent( event )

	if handleChatKeyEvent( event ):
		return True
	return handled

def handleChatKeyEvent( event ):
	# scroll player chat console if we can
	down = event.isKeyDown()
	chatConsole = rds.fdgui.chatWindow
	if chatConsole and chatConsole.script.isActive:
		if down and (event.key == KEY_RETURN and not event.isModifierDown()):
			# check if the in game menu is active
			if not rds.fdgui.inGameMenu.script.isActive and not chatConsole.script.editing:
				chatConsole.script.edit(1)  # if already editing then
				return True		    #  it'll catch return above
		elif down and (event.key == KEY_SLASH and not event.isModifierDown()):
			# check if the in game menu is active
			if not rds.fdgui.inGameMenu.script.isActive and not chatConsole.script.editing:
				chatConsole.script.edit(1,initialEditText = "/")  # if already editing then
				return True		    #  it'll catch return above
		elif down and (event.key == KEY_ESCAPE and not event.isModifierDown()) and chatConsole.script.isShowing():
			chatConsole.script.hideNow()
			return True
	return False

# -----------------------------------------------------------------------------
# Method: handleInputLangChangeEvent
# Description:
#	- This is called automatically when the current input language has changed.
# -----------------------------------------------------------------------------
def handleInputLangChangeEvent():
	return PyGUI.handleInputLangChangeEvent()

# -----------------------------------------------------------------------------
# Method: handleIMEEvent
# Description:
#	- This is called automatically when the IME UI state has changed.
# -----------------------------------------------------------------------------
def handleIMEEvent( event ):
	return PyGUI.handleIMEEvent( event )



class FantasyDemoActionHandler( BWKeyBindings.BWActionHandler ):

	# handle the change camera mode key event
	@BWKeyBindings.BWKeyBindingAction( "CameraKey" )
	def cameraKey( self, isDown ):
		if isDown:
			handleCameraKey()

	@BWKeyBindings.BWKeyBindingAction( "DisconnectFromServer" )
	def disconnectFromServer( self, isDown ):
		if isDown and BigWorld.server() is not None and BigWorld.player().inWorld:
			disconnectFromServer()
			return True
		else:
			return False

	@BWKeyBindings.BWKeyBindingAction( "CancelLoading" )
	def cancelLoading( self, isDown ):
		if isDown and BigWorld.player() is not None and not BigWorld.worldDrawEnabled():
			addMsg("User cancelled loading screen.")
			BigWorld.worldDrawEnabled(True)
			_showLogoScreen(False)
			_showLoadingBar(False)

			_activateChatWindow()

			return True
		else:
			return False

	@BWKeyBindings.BWKeyBindingAction( "EnableEnvironmentSync" )
	def enableEnvironmentSync( self, isDown ):
		if isDown:
			enableEnvironmentSync()
			return True
		else:
			return False

	@BWKeyBindings.BWKeyBindingAction( "DisableEnvironmentSync" )
	def disableEnvironmentSync( self, isDown ):
		if isDown:
			disableEnvironmentSync()
			return True
		else:
			return False

	@BWKeyBindings.BWKeyBindingAction( "ChatWindow" )
	def toggleChatWindow( self, isDown ):
		chatConsole = rds.fdgui.chatWindow
		if isDown and chatConsole:
			if chatConsole.script.isShowing():
				chatConsole.script.hideNow()
			else:
				chatConsole.script.edit(1)
			return True
		else:
			return False


	@BWKeyBindings.BWKeyBindingAction( "DefaultWebScreens" )
	def defaultWebScreens( self, isDown ):	
		if isDown:
			for entity in BigWorld.entities.values():
				if isinstance(entity, WebScreen):
					entity.setDefault()	

# -----------------------------------------------------------------------------
# Method: setCursorCameraSource
# Description:
#	- This is called to override the source matrix provider for the cursor camera.
# -----------------------------------------------------------------------------
def setCursorCameraSource( source ):
	rds.cc.source = source

# -----------------------------------------------------------------------------
# Method: handleCameraKey
# Description:
#	- This is called in response to the 'next camera' key being pressed.
# -----------------------------------------------------------------------------
def handleCameraKey( forceToStandardCamera = False ):
	if isinstance( BigWorld.player(), Avatar.Avatar) and BigWorld.player().firstPerson:
		resetCameraOffset()
		cameraDistanceOverride(rds.defaultPivotMaxDist)
		BigWorld.projection().nearPlane = rds.defaultNearPlane
		BigWorld.player().toggleFirstPersonMode(False)
		return

	if forceToStandardCamera:
		rds.cameraKeyIdx = 0
	else:
		rds.cameraKeyIdx = (rds.cameraKeyIdx + 1) % 3
	BigWorld.target.isEnabled = 1

	pivotMaxDist = 2
	import Ripper
	if isinstance( BigWorld.player(), Ripper.PlayerRipper):
		pivotMaxDist = 3.5

	if rds.cameraKeyIdx == 0:
		rds.cc.inaccuracyProvider=None
		rds.cc.reverseView = False
		rds.updatePivotDist()
		cameraType(0)

	elif rds.cameraKeyIdx == 1:
		cameraType(0)
		#disable targeting system
		BigWorld.target.clear()
		BigWorld.target.isEnabled = 0
		#enable orbit camera
		v1 = Vector4LFO()
		v1.waveform = 'SAWTOOTH'
		v1.period = 20.0
		v1.amplitude = (3.141592654*2.0)
		v2 = Vector4(1,0,0,0)
		v = Vector4Product()
		v.a=v1
		v.b=v2
		rds.cc.inaccuracyProvider=v
		rds.cc.pivotMaxDist = pivotMaxDist
		rds.cc.maxDistHalfLife = 1.5

	elif rds.cameraKeyIdx == 2:
		cameraType(3)
		resetCameraOffset()
		rds.cc.inaccuracyProvider=None
		rds.cc.reverseView = False
		rds.updatePivotDist()

# -----------------------------------------------------------------------------
# Method: handleMouseEvent
# Description:
#	- This is called automatically when a mouse event is generated.
# -----------------------------------------------------------------------------
def handleMouseEvent( event ):
	global rds

	# try the gui
	handled = PyGUI.handleMouseEvent( event )
	if not handled:
		handled = GUI.handleMouseEvent( event )
	if handled:
		return True

	# try the camera
	player = BigWorld.player()
	camMouseMove = True
	if isinstance( player, Avatar.PlayerAvatar ) and not getattr( player, "inMouseMove", True ):
		camMouseMove = False
	if camMouseMove is True:
		cam = BigWorld.camera()
		handled = cam.handleMouseEvent( event )

	if BigWorld.camera() != rds.frc and (isinstance( player, Avatar.PlayerAvatar ) and not player.inWebScreenMode()):
		if rds.middleMouseButtonDown and hasattr(rds.cc.source,'yaw'):
			msens = BigWorld.dcursor().mouseSensitivity * BigWorld.projection().fov / 1.04719755 #60 degrees
			newYaw = rds.cc.source.yaw + event.dx * BigWorld.dcursor().mouseHVBias * msens
			if BigWorld.dcursor().invertVerticalMovement:
				newPitch = rds.cc.source.pitch + event.dy * (1.0 - BigWorld.dcursor().mouseHVBias) * msens
			else:
				newPitch = rds.cc.source.pitch - event.dy * (1.0 - BigWorld.dcursor().mouseHVBias) * msens

			if newPitch > BigWorld.dcursor().maxPitch:
				newPitch = BigWorld.dcursor().maxPitch
			elif newPitch < BigWorld.dcursor().minPitch:
				newPitch = BigWorld.dcursor().minPitch

			# set the camera yaw and pitch
			rds.cc.source.setRotateYPR((newYaw, newPitch, rds.cc.source.roll))
			# we want to make the player 'looking' at the same direction as the camera
			BigWorld.dcursor().yawPitch(BigWorld.dcursor().yaw, newPitch)

		elif hasattr(rds, 'dYaw'):
			# fix the camera offset based on current player direction
			msens = BigWorld.dcursor().mouseSensitivity * BigWorld.projection().fov / 1.04719755 #60 degrees
			if BigWorld.dcursor().invertVerticalMovement:
				newPitch = rds.cc.source.pitch + dy * (1.0 - BigWorld.dcursor().mouseHVBias) * msens
			else:
				newPitch = rds.cc.source.pitch - dy * (1.0 - BigWorld.dcursor().mouseHVBias) * msens
			if newPitch > BigWorld.dcursor().maxPitch:
				newPitch = BigWorld.dcursor().maxPitch
			elif newPitch < BigWorld.dcursor().minPitch:
				newPitch = BigWorld.dcursor().minPitch

			rds.cc.source.setRotateYPR((BigWorld.dcursor().yaw + rds.dYaw,
										newPitch,
										rds.cc.source.roll))

		# don't try to move camera if player
		# is not the standard Player Avatar.
		if isinstance(BigWorld.player(), Avatar.PlayerAvatar):
			if event.dz != 0:
				clicks = event.dz/120.0	# add 20% for each notch... or something
				nextDist = math.exp(math.log(rds.cc.targetMaxDist) - clicks*math.log(1.2))
			if event.dz > 0:
				if nextDist < 0.5 and rds.cc.pivotMaxDist > 0.75:
					nextDist = 0.5	# don't go to first person until smoothly moved in close
				if nextDist >= 0.5:
					cameraDistanceOverride(nextDist)
					if nextDist <= rds.cameraCloseUpTrigger:
						BigWorld.projection().nearPlane = FIRST_PERSON_NEAR_CLIP_PLANE
				else:
					if player and player.inWorld and not player.firstPerson:
						player.toggleFirstPersonMode(True)
			elif event.dz < 0:
				if nextDist > 15.0: nextDist = 15.0
				if player and player.inWorld and hasattr( player, 'firstPerson' ) and player.firstPerson:
					if player.toggleFirstPersonMode(False):
						resetCameraOffset()
				else:
					cameraDistanceOverride(nextDist)
				if nextDist > rds.cameraCloseUpTrigger:
					BigWorld.projection().nearPlane = rds.defaultNearPlane

	if player and player.inWorld and hasattr(player, 'handleMouseEvent'):
		player.handleMouseEvent( event )

	if rds.middleMouseButtonDown:
		return 1

	return 0


# -----------------------------------------------------------------------------
# Method: resetCameraOffset
# Description:
#	- Reset the camera facing at the back of player
# -----------------------------------------------------------------------------
def resetCameraOffset():
	global rds

	if id(rds.cc.source) != id(BigWorld.dcursor().matrix):
		rds.cc.source = BigWorld.dcursor().matrix
	if hasattr(rds, 'dYaw'):
		delattr(rds, 'dYaw')


# -----------------------------------------------------------------------------
# Method: resetCamera
# Description:
#	- Reset the camera
# -----------------------------------------------------------------------------
def resetCamera():
	global rds

	resetCameraOffset()
	cameraDistanceOverride(rds.defaultPivotMaxDist)
	BigWorld.projection().nearPlane = rds.defaultNearPlane
	BigWorld.player().toggleFirstPersonMode(False)


# -----------------------------------------------------------------------------
# Method: handleAxisEvent
# Description:
#	- This is called automatically when an axis event is generated.
# -----------------------------------------------------------------------------
def handleAxisEvent( event ):
	# try the gui
	handled = GUI.handleAxisEvent( event )

	cam = BigWorld.camera()
	if cam is not None and handled is False:
		handled = cam.handleAxisEvent( event )

	return handled


def _activateChatWindow():
	global rds

	rds.console.script.active(False)

	chatConsole = rds.fdgui.chatWindow
	if chatConsole:
		chatConsole.script.active(True)

def _deactivateChatWindow():
	global rds

	rds.console.script.active(True)

	chatConsole = rds.fdgui.chatWindow
	if chatConsole:
		chatConsole.script.clear()
		chatConsole.script.active(False)




############################################################################
# Resource Updater notification handlers								   #
############################################################################

# -----------------------------------------------------------------------------
# Method: onResUpdateDownloadBegin
#
# A download has started, aiming to bring the given version point to the
# given version number. The download will occur in the background, even
# if these resources are required to enable entities, i.e. required to
# receive player data from the server. The first 3 elements of the
# progressV4Provider will indiciate the progress of the download:
# x: version number currently being downloaded
# y: files progress within current version number
# z: byte progress within file
# Note: If through script action, directly or indirectly, resources
# need to be loaded in the main from a non-root version point that is
# not up-to-date, then the main thread will block until those resources have
# been downloaded. The game will not progress except for processing messages
# from the server. This would be very bad! However, since scripts should
# never be loading resources in the main thread anyway - for the relatively
# small loading pause that would result - avoiding this is no extra burden.
# -----------------------------------------------------------------------------
def onResUpdateDownloadBegin(version, point, progressV4Provider):
	print 'onResUpdateDownloadBegin', version, point

# -----------------------------------------------------------------------------
# Method: onResUpdateDownloadEnd
#
# A download signalled above has ended. There may be a short time
# (up to one frame) when progressV4Provider.x is -1 before this function
# is called.
# Note: onResUpdateAutoRelaunch might be called before this function
# if an auto relaunch is going to occur.
# -----------------------------------------------------------------------------
def onResUpdateDownloadEnd(version, point, progressV4Provider):
	print 'onResUpdateDownloadEnd', version, point

# -----------------------------------------------------------------------------
# Method: onResUpdateLoadin
#
# It is time to begin loading in the updated resources in the client.
# Since the client doesn't yet have this capability for some resources,
# for now we must relaunch the client here. But give the user some
# notice first. (If we don't disconnect after a few minutes, the server
# will kick us off.)
# -----------------------------------------------------------------------------
def onResUpdateLoadin():
	print 'onResUpdateLoadin'
	BigWorld.callback(30, relaunchNow)

# The user has had enough time to prepare for the relaunch, so do it
def relaunchNow():
	try:
		BigWorld.player().base.logOff()
	except:	pass

	print 'Relaunching now'
	BigWorld.resUpdateInstallAndRelaunch()

# -----------------------------------------------------------------------------
# Method: onResUpdateAutoRelaunch
#
# We logged in but didn't enable entities / create a player, because
# out resources were out of date. We now have the new resources and they
# have been installed. The client is going to relaunch so it can use them
# as soon as this call returns.
# Note: onResUpdateDownloadBegin might not yet have been received if the update
# was very small or was a rollback. If it was received, then the corresponding
# onResUpdateDownloadEnd might not yet have been received before this call.
# -----------------------------------------------------------------------------
def onResUpdateAutoRelaunch():
	print 'onResUpdateAutoRelaunch'


def create(type):
	player = BigWorld.player()
	return BigWorld.createEntity(type, player.spaceID, 0, player.position, (0,0,0), {})


# ------------------------------------------------------------------------------
# Section: Macro expansion
# ------------------------------------------------------------------------------

# These are the python console macro expansions supported by FantasyDemo
PYTHON_MACROS = {
	"p":"BigWorld.player()",
	"t":"BigWorld.target()",
	"B":"BigWorld",
	"G":"doppleganger()",
	"a":"BigWorld.createEntity(\"Avatar\", BigWorld.player().spaceID, 0, BigWorld.player().position,(0,0,0),{})",
	"r":"BigWorld.entity(BigWorld.createEntity(\"Ripper\", BigWorld.player().spaceID, 0, BigWorld.player().position,(0,0,0),{}))",
	"s":"BigWorld.createEntity(\"Seat\", BigWorld.player().spaceID, 0,BigWorld.player().position,(0,0,0),{\"seatType\":1})",
	"e":"BigWorld.createEntity(\"Effect\", BigWorld.player().spaceID, 0,BigWorld.player().position,(0,0,BigWorld.player().yaw),{\"effectType\":6})",
	"o":"BigWorld.createEntity(\"Effect\", BigWorld.player().spaceID, 0,BigWorld.player().position,(0,0,0),{\"effectType\":3})",
	"S":"BigWorld.createEntity(\"Effect\", BigWorld.player().spaceID, 0,BigWorld.player().position,(0,0,0),{\"effectType\":4})",
	"v":"BigWorld.createEntity(\"Effect\", BigWorld.player().spaceID, 0,(-79.4,78.6,298.4),(0,0,0),{\"effectType\":6})",
	"V":"BigWorld.createEntity(\"VideoScreen\", BigWorld.player().spaceID, 0, BigWorld.player().position,(0,0,0),{})",
	"A":"m=BigWorld.Model('sets/items/xbow_bolt.model'); m.position=(0,1.2,-5); m.yaw = -1.55; BigWorld.player().addModel(m); h=BigWorld.Homer(); h.target=BigWorld.player().model; h.offset=(0,1.2,0); h.speed=1; h.turnRate=1; h.tripTime=8"
}

import re

# Implementation for BWPersonality.expandMacros() callback
def expandMacros( line ):

	# Glob together the keys from the macros dictionary into a pattern
	patt = "\$([%s])" % "".join( PYTHON_MACROS.keys() )

	def repl( match ):
		return PYTHON_MACROS[ match.group( 1 ) ]

	return re.sub( patt, repl, line )


rds = RDShare()
rds.init()
