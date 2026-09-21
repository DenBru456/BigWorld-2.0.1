import BigWorld
import ResMgr
import FDConfig
import TradingSupervisor
import AuctionHouse
import HierarchyCheck
from GameData import FantasyDemoData

# This is imported here to avoid loading in the main thread.
import UserDataObjectRef

import NoteDataStore

import xmpp.Service as XMPPService
import XMPPEventNotifier

import gc
import pprint


NOTE_STORE_CONFIG = "server/config/note_data_store.xml"
XMPP_CONFIG = "server/config/xmpp.xml"

# ------------------------------------------------------------------------------
# Section: Callbacks
# ------------------------------------------------------------------------------

def onInit( isReload ):
	""" Callback function when scripts are loaded. """

	# Check that the entitydef inheritance hierarchy strictly
	# matches the Python class hierarchy.

	# HierarchyCheck.checkTypes()

	if NoteDataStore.init( NOTE_STORE_CONFIG ):
		print "Note Data Store example enabled"
	else:
		print "Note Data Store example disabled"

	xmppStatus, reason = XMPPService.init( XMPP_CONFIG )
	if xmppStatus:
		print "XMPP Chat example enabled"
	else:
		print "XMPP Chat example disabled (%s)" % reason


def onFini():
	gc.set_debug( gc.DEBUG_SAVEALL )
	numLeaks = gc.collect()

	if gc.garbage:
		print "FantasyDemo.onFini: Potential circular references"
		print "Number of leaks:", numLeaks

		#for object in gc.garbage:
		#	print type( object )
		#	pprint.pprint( object )


def onBaseAppReady( isBootstrap, didAutoLoadEntitiesFromDB ):
	# Load all the runscript watchers for this baseapp
	Watchers.addWatchers()

	if not isBootstrap:
		return

	if didAutoLoadEntitiesFromDB:
		print "Bootstrap: auto-loaded entities from DB"

	else:
		print "Bootstrap: did not autoload entities from DB"
		TradingSupervisor.wakeupTradingSupervisor()
		AuctionHouse.wakeup()

		# create space loader for each space
		for realmID, realm in FantasyDemoData.REALMS.iteritems():
			# The first space in a realm is considered the default space.
			# Players will initially be created here.
			isDefault = True

			for space in realm.spaces:
				entity = BigWorld.createBaseLocally( "SpaceLoader",
							spaceDir = space.path,
							isDefault = isDefault,
							realm = realmID,
							wasAutoLoaded = False,
							startPosition = space.startPosition )
				isDefault = False

	if XMPPService.isEnabled():
		XMPPEventNotifier.wakeupXMPPEventNotifier()


def onBaseAppShutDown( state ):
	if state == 0:
		XMPPEventNotifier.destroyXMPPEventNotifier()
		NoteDataStore.fini()


def onCellAppDeath( addr ):
	XMPPEventNotifier.broadcast( "CellApp %s died" % addr )

# ------------------------------------------------------------------------------
# Section: Common base class
# ------------------------------------------------------------------------------

class Base( BigWorld.Base ):
	def __init__( self ):
		BigWorld.Base.__init__( self )

		# This is useful if using disaster recovery.
		# if not self.databaseID:
		#	self.writeToDB()

		if hasattr( self, "cellData" ):
			try:
				cell = self.createOnCell
				self.createOnCell = None
			except AttributeError, e:
				cell = None

			if cell != None:
				self.createCellEntity( cell )
			elif self.cellData["spaceID"]:
				self.createCellEntity()

	def onLoseCell( self ):
		rsm = None
		if hasattr( self, 'respawnInterval' ) and self.respawnInterval != 0:
			gb = BigWorld.globalBases
			if not gb.has_key( 'RespawnManager' ):
				rsm = BigWorld.createEntity( 'RespawnManager' )
			else:
				rsm = gb['RespawnManager']
			rsm.registerForRespawn( self.__module__, self.entityData, self.respawnInterval )
		self.destroy()

# At the bottom to avoid circular import issue
import Watchers

# FantasyDemo.py
