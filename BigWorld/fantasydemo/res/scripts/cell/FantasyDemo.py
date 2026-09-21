import BigWorld
import HierarchyCheck
import Watchers


# Called when new space data has been added.
def onSpaceData( spaceID, entryID, key, value ):
	pass
	# print "onSpaceData: spaceID", spaceID, \
	#	"entryID", entryID, "key", key, "value", len(value)


def onInit( isReload ):
	""" Callback function when scripts are loaded. """

	# Check that the entitydef inheritance hierarchy strictly
	# matches the Python class hierarchy.

	# Load all the runscript watchers for this cellapp
	Watchers.addWatchers()

	# HierarchyCheck.checkTypes()
	pass


def onAllSpaceGeometryLoaded( spaceID, isBootstrap, mapping ):
	for i, e in BigWorld.entities.items():
		if e.isReal() and \
				hasattr( e, 'onAllSpaceGeometryLoaded' ) and \
				e.spaceID == spaceID:
			e.onAllSpaceGeometryLoaded( spaceID, isBootstrap, mapping )

	print "onAllSpaceGeometryLoaded: %s in space %d at game time %s" % \
	   (mapping, spaceID, str( BigWorld.time() ))


# FantasyDemo.py
