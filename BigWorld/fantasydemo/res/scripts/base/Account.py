import BigWorld
from functools import partial
import AvatarModel
import PlayerModel

from GameData import FantasyDemoData

# ------------------------------------------------------------------------------
# Section: class Account
# ------------------------------------------------------------------------------

class Account( BigWorld.Proxy ):

	def __init__( self ):
		BigWorld.Proxy.__init__( self )
		self.isBot = False
		self.haveWebClient = False
		self.updateCharacterList()

	def onRestore( self ):
		self.updateCharacterList()

	def onEntitiesEnabled( self ):
		if self.activeCharacter == None:
			if self.accountName.startswith( 'Bot_' ):
				self.botLoggedOn()
			else:
				if self.databaseID == 0:
					self.writeToDB()
		else:
			# Re-login attempt, give client straight away
			self.activeCharacter.giveClientTo( None )
			self.giveClientTo( self.activeCharacter )

	def onLogOnAttempt( self, ip, port, password ):
		if ip == 0:
			# from web login, let it come in regardless
			self.selectedRealm = "fantasy" # TODO: select realm from web page
			return BigWorld.LOG_ON_ACCEPT
		if self.activeCharacter != None:
			# already have a character logged on - reject
			return BigWorld.LOG_ON_REJECT
		if ip == self.lastClientIpAddr and password == self.password:
			return BigWorld.LOG_ON_ACCEPT
		if self.clientAddr[0] == 0:
			# if we only have a web session holding onto us, allow
			return BigWorld.LOG_ON_ACCEPT

		# default - reject re-logon
		return BigWorld.LOG_ON_REJECT

	def botLoggedOn( self ):
		self.isBot = True
		if len(self.characterList) == 0:
			self.createNewAvatar( self.accountName )
		else:
			self.characterBeginPlay( self.characterList[0]['name'] )

	def selectRealm( self, realmID ):
		if realmID not in FantasyDemoData.REALMS:
			print "ERROR: Account.selectRealm: received invalid realmID '%s'" % realmID
			return

		self.selectedRealm = realmID
		self.updateCharacterList()
		self.client.switchRealm( realmID, self.characterList )

	def createNewAvatar( self, avatarName, response=None ):
		avatar = BigWorld.createBaseLocally( "Avatar",
				{ "playerName":avatarName,
					"persistentAvatarModelData":PlayerModel.randomPlayerModel( self.selectedRealm ),
					"realm":self.selectedRealm,
					"xmppName": self.accountName} )
		avatar.writeToDB( partial( self.onCreatedNewAvatar, response=response) )

	def characterBeginPlay( self, characterName ):
		for character in self.persistentCharacterList:
			if character['name'] == characterName and character['realm'] == self.selectedRealm:
				BigWorld.createBaseFromDBID(	character['type'],
												character['databaseID'],
												self.onLoadedAvatar )
				return
		print "Unknown character '%s' for realm '%s'." % (characterName, self.selectedRealm)


	def onCreatedNewAvatar( self, success, avatar, response ):
		if success:
			newAvatarName = avatar.cellData['playerName']
			self.persistentCharacterList.append( dict(
													name = newAvatarName,
													databaseID = avatar.databaseID,
													type = 'Avatar',
													realm = avatar.realm,
													characterModel = avatar.persistentAvatarModelData ) )
			self.updateCharacterList()
			print 'New character', newAvatarName, 'created'
			if self.isBot:
				self.onAvatarReady( avatar )
			else:
				avatar.destroy()
				if response == None:
					self.client.createCharacterCallback( True, u'', self.characterList )
				else:
					# web request
					response.success = True
					response.done()
		else:
			print 'Failed to create new Avatar %s for player %s' % \
				(avatar.cellData['playerName'], self.accountName)
			if not self.isBot:
				errMsg = 'A character with name %s already exists.' % \
					avatar.cellData['playerName']
				self.client.createCharacterCallback( False, unicode(errMsg), self.characterList )
			avatar.destroy()
			if response:
				response.success = False
				response.errMsg = errMsg
				response.done()

	def updateCharacterList( self ):
		newCharacterList = []
		for character in self.persistentCharacterList:
			if character['realm'] == self.selectedRealm:
				newCharacter = {}
				newCharacter['name'] = character['name']
				newCharacter['characterModel'] = AvatarModel.pack( character['characterModel'] )
				newCharacter['realm'] = character['realm']
				newCharacterList.append( newCharacter )
		self.characterList = newCharacterList

	def onLoadedAvatar( self, avatar, dbID, wasActive ):
		if avatar != None and \
				BigWorld.entities.has_key( avatar.id ):
			# We should be on the same BaseApp as the avatar, but we may still
			# be passed a mailbox if the entity is already checked out.
			avatar = BigWorld.entities[avatar.id]
			self.onAvatarReady( avatar )
		else:
			if avatar != None:
				print "Account(%d).onLoadedAvatar: Avatar %d is not on " \
						"the same BaseApp as this account" % \
					(self.id, avatar.id)
			else:
				print "Account(%d).onLoadedAvatar: " \
						"Failed to load %s for player %s" % \
					(self.characterList[0]['type'], self.accountName)
			self.onAvatarReady( None )


	def onAvatarReady( self, avatar ):
		if avatar != None:
			self.activeCharacter = avatar
			avatar.account = self
			self.lastClientIpAddr = self.clientAddr[0]

			if avatar.realm == '':
				print "Defaulting to fantasy"
				avatar.realm = "fantasy"

			# Test that the teleport point is valid.
			try:
				avatar.getTeleportPoint()
			except KeyError:
				print "Account: initial teleport point in '%s' isn't available yet." % avatar.realm
				avatar.destroy()
				self.failLogon( "Server is not yet ready for Avatars." )
				return

			self.giveClientTo( avatar )
			if self.databaseID == 0:
				print "Writing Account to DB"
				self.writeToDB()
		else:
			self.failLogon( "Failed to create your avatar."  )

	def onClientDeath( self ):
		print "Account(%d).onClientDeath" % self.id
		if not self.haveWebClient:
			self.destroy()

	def onAvatarDeath( self, avatarDBID, avatarModel ):
		if self.isDestroyed:
			# Avatar could be holding a reference to us while we're destroyed
			return

		print "Account(%d).onAvatarDeath" % self.id
		for character in self.persistentCharacterList:
			if character['databaseID'] == avatarDBID:
				character['characterModel'] = AvatarModel.unpack( avatarModel )
		self.activeCharacter = None
		if not self.haveWebClient:
			self.destroy()

	def failLogon( self, message ):
		self.client.failLogon( unicode( message ) )
		self.addTimer( 0.5 )

	def onTimer( self, id, userArg ):
		self.giveClientTo( None )
		self.destroy()


	def webGetCharacterList( self, response ):
		response.characters = []
		for character in self.persistentCharacterList:
			cInfo = {}
			cInfo['name'] = character.name.encode( 'utf8' )
			cInfo['type'] = character.type
			cInfo['realm'] = character.realm
			cInfo['databaseID'] = character.databaseID
			cInfo['charClass'] = \
				PlayerModel.modelListToCharacterClassString(
					character.characterModel.models )
			response.characters.append( cInfo )
		response.done()

	def webChooseCharacter( self, response, cName, cType ):
		cName = cName.decode( 'utf8' )
		found = False

		for c in self.persistentCharacterList:
			if c['name'] == cName and c['type'] == cType:
				found = True
				break
		if found:
			def onWebChooseCharacter( response, avatar, dbID, active ):
				if type( avatar ) == bool:
					response.errMsg = "Could not load from database"
				else:
					print "Account(%d).webChooseCharacter: " \
							"got avatar entity: %d" % \
						(self.id, avatar.id)
					response.character = avatar

				response.done()

			BigWorld.createBaseFromDBID( c['type'], c['databaseID'],
				partial( onWebChooseCharacter, response ) )
		else:
			response.errMsg = "Cannot find character"
			response.done()

	def webCreateCharacter( self, response, name ):
		name = name.decode( 'utf8' )
		self.createNewAvatar( name, response )

	def webLogout( self ):
		print "Account(%d).webLogout" % self.id
		if not self.hasClient and self.activeCharacter == None:
			self.destroy()

	def onKeepAliveStart( self ):
		self.haveWebClient = True

	def onKeepAliveStop( self ):
		print "Account(%d).onKeepAliveStop" % self.id
		self.haveWebClient = False
		self.webLogout()


# Account.py
