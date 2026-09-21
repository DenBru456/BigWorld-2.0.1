import math
import BigWorld
from Helpers import Caps
import Keys
from FDGUI import Minimap


spawnersList = []


# ------------------------------------------------------------------------------
# Section: class GuardSpawner
# ------------------------------------------------------------------------------
class GuardSpawner( BigWorld.Entity ):
	def __init__( self ):
		BigWorld.Entity.__init__( self )


	def prerequisites( self ):
		return ['characters/npc/fd_orc_guard/statue.model']
		#return [ self.modelName ]


	def onEnterWorld( self, prereqs ):
		self.model = prereqs.values()[0]
		self.model.Idle()
		BigWorld.addShadowEntity( self )
		self.targetCaps = [ Caps.CAP_CAN_USE ]
		self.filter = BigWorld.DumbFilter()
		self.focalMatrix = self.model.node("biped Head")
		global spawnersList
		spawnersList.append( self )
		Minimap.addEntity( self )


	def onLeaveWorld( self ):
		Minimap.delEntity( self )
		global spawnersList
		spawnersList.remove( self )
		BigWorld.delShadowEntity( self )
		self.model = None


	def set_spawning( self, oldValue ):
		if self.spawning and not oldValue:
			self.model.Activate().ActivateHold()
		elif oldValue and not self.spawning:
			self.model.Deactivate().Idle()


	def use( self ):
		if BigWorld.isKeyDown( Keys.KEY_LSHIFT ) or \
				BigWorld.isKeyDown( Keys.KEY_RSHIFT ):
			self.cell.spawnGuardsLocally( 100, 1000, 100.0 )
		else:
			self.cell.spawnGuardsLocally( 100, 500, 100.0 )


	def name( self ):
		return self.nameProperty + ' Total:' + str( self.numberOfGuards )


def spawnGuardsEverywhere( num = 100, duration = 100.0, maxCount = 500 ):
	if len(spawnersList) == 0:
		return False

	numAtEach = num // len(spawnersList)
	for s in spawnersList:
		s.cell.addLoadDemoGuards( numAtEach )

	return True


def destroyGuardsEverywhere( num = 100 ):
	if len(spawnersList) == 0:
		return False

	#try to get rid of them from everywhere
	numAtEach = num / len(spawnersList)
	for s in spawnersList:
		s.cell.delLoadDemoGuards( numAtEach )

	return True

# GuardSpawner.py
