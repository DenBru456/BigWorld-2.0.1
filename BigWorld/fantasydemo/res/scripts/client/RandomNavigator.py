import math
import BigWorld
from Helpers import Caps


# ------------------------------------------------------------------------------
# Section: class RandomNavigator
# ------------------------------------------------------------------------------


class RandomNavigator( BigWorld.Entity ):
	stdModel = 'characters/avatars/base/base.model'

	def __init__( self ):
		BigWorld.Entity.__init__( self )


	def prerequisites( self ):
		return [ RandomNavigator.stdModel ]


	def onEnterWorld( self, prereqs ):
		self.model = prereqs[RandomNavigator.stdModel]
		BigWorld.addShadowEntity( self )
		self.targetCaps = [Caps.CAP_CAN_HIT , Caps.CAP_CAN_USE]
		self.filter = BigWorld.AvatarDropFilter()


	def onLeaveWorld( self ):
		BigWorld.delShadowEntity( self )
		self.model = None


	def use( self ):
		pass


#RandomNavigator.py
