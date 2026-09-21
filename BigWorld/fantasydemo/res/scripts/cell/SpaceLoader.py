import BigWorld

START_TIME_OF_DAY = 7.5 * 60 * 60 # 7:30
GAME_SECONDS_PER_SECOND = 6 # 4 real hours for a day

class SpaceLoader( BigWorld.Entity ):
	def __init__( self ):
		BigWorld.Entity.__init__( self )

	def addGeometryMappingIfNeeded( self, geometryToMap ):
		"""
		Add the given space geometry at the origin.
		"""

		# If space data was archived, it would have already been mapped.
		if not BigWorld.getSpaceGeometryMappings( self.spaceID ):
			BigWorld.addSpaceGeometryMapping(
					self.spaceID, None, geometryToMap )

		BigWorld.setSpaceTimeOfDay( self.spaceID, 
			START_TIME_OF_DAY, GAME_SECONDS_PER_SECOND )

# SpaceLoader.py
