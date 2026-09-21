import BigWorld
import FDConfig
import FantasyDemo

from GameData import FantasyDemoData

nameSeparator = "/"

class SpaceLoader( FantasyDemo.Base ):
	def __init__( self ):
		print "SpaceLoader", self.id, "spaceDir =", self.spaceDir

		FantasyDemo.Base.__init__( self )

		if not hasattr( self, "cell" ):
			self.createInNewSpace()
		
		self.cell.addGeometryMappingIfNeeded( self.spaceDir )

	def onGetCell( self ):
		if FDConfig.LOAD_ENTITIES_FROM_CHUNKS:
			print "SpaceLoader.onGetCell loading space", self.spaceDir
			BigWorld.fetchEntitiesFromChunks( self.spaceDir,
					EntityLoader( self, self.wasAutoLoaded ) )

		self.writeToDB( shouldAutoLoad = True )


AUTO_LOAD_TYPES = set( ("Merchant", "SpaceLoader") )

class EntityLoader:
	def __init__( self, spaceLoader, wasAutoLoaded ):
		self.spaceLoader = spaceLoader
		self.wasAutoLoaded = wasAutoLoaded

		# Create and register the initial teleport point as soon as possible
		# instead of in onFinish as it may take a while for us to get there on 
		# larger spaces.
		if spaceLoader.isDefault:
			BigWorld.createBaseLocally( 'TeleportPoint',
					realm = spaceLoader.realm,
					createOnCell = spaceLoader.cell,
					dstPos = spaceLoader.startPosition,
					position = spaceLoader.startPosition,
					spaceName = "default",
					label = "default",
					direction = (0,0,0) )

	def onSection( self, entity, matrix ):
		entityType = entity.readString( "type" )
		properties = entity[ "properties" ]
		pos = matrix.applyToOrigin()

		if self.wasAutoLoaded and entityType in AUTO_LOAD_TYPES:
			return

		extraArgs = {}

		if entityType == "TeleportPoint":
			extraArgs = dict( realm = self.spaceLoader.realm,
						spaceName = self.spaceLoader.spaceDir,
						dstPos = pos )

		BigWorld.createBaseAnywhere( entityType,
			properties,
			createOnCell = self.spaceLoader.cell,
			position = pos,
			direction = (matrix.roll, matrix.pitch, matrix.yaw),
			**extraArgs )

	def onFinish( self ):

		print "Finished loading entities for space", \
						self.spaceLoader.realm, self.spaceLoader.spaceDir

# SpaceLoader.py
