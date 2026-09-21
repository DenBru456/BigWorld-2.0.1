import BigWorld

# ------------------------------------------------------------------------------
# Section: class RipperBot
# ------------------------------------------------------------------------------

class RipperBot( BigWorld.Proxy ):
	def clientDead( self ):
		print "Help: The base just told us (ripper %d) we're dead!" % self.id
		self.cell.die()

	def onLoseCell( self ):
		self.destroy()

# RipperBot.py
