import BigWorld
import AvatarMode
import Avatar


class Merchant( BigWorld.Entity ):
	'''
	'''
	INNER_RANGE = 5


	def __init__( self ):
		BigWorld.Entity.__init__( self )
		self.addProximity( Merchant.INNER_RANGE )


	def commerceStartRequest( self, avatarID ):
		'''An avatar wants to trade with this Merchant.
		Params:
			avatarID				id of requesting avatar
		'''
		try:
			avatar = BigWorld.entities[ avatarID ]
		except KeyError:
			errorMsg = 'Merchant.commerceRequest: unknown entity: %d'
			print errorMsg % avatarID
			return
		if not isinstance( avatar, Avatar.Avatar ):
			print 'Merchant.commerceRequest: entity not an Avatar: %d' % avatarID
			avatar.commerceStartResponse( False, 0 )
			return

		if self.modeTarget == AvatarMode.NO_TARGET:
			self.modeTarget = avatarID
			avatar.commerceStartResponse( True, self.id )
			self.base.commerceItemsRequest( avatarID )
		else:
			avatar.commerceStartResponse( False, 0 )


	def commerceCancelRequest( self ):
		'''The avatar wants to cease trading with this Merchant.
		'''
		self._commerceCancel()


	def onEnterTrap( self, entity, range, trap ):
		'''Some entity has entered the proximity trap. Just ignore it.
		'''
		pass


	def onLeaveTrap( self, entity, range, trap ):
		'''The avatar has move far from this Merchant.
		If it is our trading partiner, cancel trading with him.
		'''
		if entity.id == self.modeTarget:
			self._commerceCancel()


	def _commerceCancel( self ):
		'''Cancel trading with the current partner avatar.
		'''
		self.modeTarget = AvatarMode.NO_TARGET

	def onWitnessed( self, witnessed ):
		'''Callback for when this entity to receive witness events.  When this
		entity enters the AoI of a witness entity, then it is called back with
		witnessed=True. After 12 minutes of being outside of all witness
		entities' AoI, this is called back with witnessed=False.

		This is a good place for switching on/off CPU-intensive tasks that only
		matter if there is an entity witnessing us, e.g. AI processing.
		'''

		if not witnessed:
			msg = "We have not been witnessed in some time"
		else:
			msg = "We have been witnessed!"
		print "Merchant(%d): %s" % (self.id, msg,)

	def sayToAoI( self, msg ):
		self.allClients.chat( msg )
	
# Merchant.py
