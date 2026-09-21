import BigWorld

# This implements the VehicleExample on the Cell.  It's purpose is to provide
# a central point to confirm or deny a request to mount and dismount.  It
# does this via an ALL_CLIENT property change.

# To create the VehicleExample, telnet to a BigWorld Base:
#	telnet <host> 40001
# and type:
#	BigWorld.createBase( "VehicleExample" )
class VehicleExample( BigWorld.Entity ):

	def __init__( self ):
		BigWorld.Entity.__init__( self )

	# This method will be called by the client to request a mount.
	# If another player has already mounted, then nothing will happen.
	# If permission is granted, then the player will be informed by the
	# property update (see VehicleExample.def)
	def mount( self, playerID ):
		if self.pilot == 0:
			self.pilot = playerID

	# This method will be called by the client to request a dismount.
	# The client will be able to put the dismount into effect when it
	# receives the property update.
	def dismount( self, playerID ):
		self.pilot = 0

# VehicleExample.py
