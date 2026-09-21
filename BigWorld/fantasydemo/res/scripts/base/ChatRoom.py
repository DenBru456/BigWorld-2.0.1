import BigWorld

def getListOfRooms():
	rooms = []
	for entity in BigWorld.entities.values():
		if entity.className == "ChatRoom":
			rooms += [entity.name]
	return rooms

def getRoom(whichRoom):
	for entity in BigWorld.entities.values():
		if entity.className == "ChatRoom" and entity.name == whichRoom:
			return entity
	return None

class ChatRoom( BigWorld.Base ):
	def __init__( self ):
		self.members = {}
		self.name = self.cellData["name"]
		BigWorld.Base.__init__( self )

	def broadcast( self, message ):
		for entity in self.members.values():
			entity.client.chat( message )

	def enter( self, playerName, entity ):
		self.members[playerName] = entity
		self.broadcast( u"%s: %s has entered" % (self.name, playerName) )

	def leave( self, playerName, entity ):
		self.broadcast( u"%s: %s is leaving" % (self.name, playerName) )
		del self.members[playerName]

# ChatRoom.py
