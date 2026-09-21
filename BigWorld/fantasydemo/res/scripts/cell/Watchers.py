import BigWorld
import Math
import util


def numInAoI():
	return float( BigWorld.getWatcher( "stats/numInAoI" ) )


def numWitnesses():
	return float( BigWorld.getWatcher( "stats/numWitnesses" ) )


def avgAoI():
	try:
		return numInAoI()/numWitnesses()
	except ZeroDivisionError:
		return 0


def getWatcherTime( entry ):
	return float( BigWorld.getWatcher( entry ) ) / \
		float( BigWorld.getWatcher( "stats/stampsPerSecond" ) )


def updateClientTime():
	return getWatcherTime( "profiles/details/updateClient/sumTime" )


def updateClientSendTime():
	return getWatcherTime( "profiles/details/updateClientSend/sumTime" )


def runningTime():
	return getWatcherTime( "stats/runningTime" )


def idleTime():
	return getWatcherTime( "nub/timing/totalSpareTime" )


def busyTime():
	return runningTime() - idleTime()

def findEntity( id ):
	try:
		if BigWorld.entities.has_key( id ):
			e = BigWorld.entities[ id ]
			print "Entity[%s]: %s" % (id, str( e ))
			print " - Space   :", e.spaceID
			print " - Position:", e.position
			print " - isReal  :", e.isReal()
			return "I own this entity"
	except:
		pass

	return "Couldn't find entity", id

def entitiesOfType( type ):
	return len( util.entitiesOfType( type ) )

def onlinePlayers():
	players = util.entitiesOfType( "Avatar" )

	if players:
		print "%-6s | %-10s | %-3s" % ("ID", "Name", "Space ID")
		print '------------------------------'
		for e in players:
			print "%6d | %-10s | %3s" % (e.id, e.playerName, e.spaceID)

	numPlayers = len( players )
	return "%d player%s" % (numPlayers, 's' if numPlayers != 1 else '')

def teleportEntity( id, x, y, z ):

	vector = Math.Vector3( x, y, z )

	if BigWorld.entities.has_key( id ):
		e = BigWorld.entities[ id ]
		if e.isReal():
			e.position = vector

			return "Teleported entity %d to %s" % (id, vector)

	return


def addWatchers():
	BigWorld.addWatcher( "python/avgAoI", avgAoI )
	BigWorld.addWatcher( "python/updateClient", updateClientTime )
	BigWorld.addWatcher( "python/updateClientSend", updateClientSendTime )
	BigWorld.addWatcher( "python/idleTime", idleTime )
	BigWorld.addWatcher( "python/runningTime", runningTime )
	BigWorld.addWatcher( "python/busyTime", busyTime )

	addPercent( "avatarUpdate" )
	addPercent( "ghostAvatarUpdate" )
	addPercent( "deliverGhosts" )
	addPercent( "boundaryCheck" )
	addPercent( "gameTick",     "1   " )
	addPercent( "calcBoundary", "1.1 " )
	addPercent( "callTimers",   "1.2 " )
	addPercent( "callUpdates",  "1.3 " )
	addPercent( "updateClient", "1.3.1 " )

	BigWorld.addFunctionWatcher( "command/hasEntity", findEntity,
		[("Entity ID", int)], BigWorld.EXPOSE_ALL,
		"Check if the entity exists on a CellApp.")

	BigWorld.addFunctionWatcher( "command/entitiesOfType", entitiesOfType,
		[("Name of Entity Type", str)], BigWorld.EXPOSE_ALL,
		"Count the number of entities of a given type." )

	BigWorld.addFunctionWatcher( "command/onlinePlayers", onlinePlayers,
		[], BigWorld.EXPOSE_ALL,
		"Display the players that are online." )

	BigWorld.addFunctionWatcher( "command/teleportEntity", teleportEntity,
		[("Entity ID", int), ("X Position", float),
		 ("Y Position", float), ("Z Position", float)], BigWorld.EXPOSE_ALL,
		"Teleport an entity to the requested position.")


class PercentageOfBusy( object ):
	def __init__( self, entry, prefix = "" ):
		self.name = "python/percent/" + prefix + entry
		self.profile = "profiles/details/" + entry + "/sumTime"

	def __call__( self ):
		t1 = getWatcherTime( self.profile )
		t2 = busyTime()
		return "%.4f" % (t1/t2,)


def addPercent( entry, prefix = "" ):
	watcher = PercentageOfBusy( entry, prefix )
	BigWorld.addWatcher( watcher.name, watcher )

