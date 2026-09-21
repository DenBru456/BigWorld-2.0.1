"This module implements the RugRat entity."

import BigWorld

# ------------------------------------------------------------------------------
# Section: RugRat
# ------------------------------------------------------------------------------

class RugRat( BigWorld.Entity ):
	"A RugRat entity."

	targets = [
		(66,	24),
		(66,	15.5),
		(-22.3,	15.5),
		(-22.3,	24)
	]
	nTargets = 4

	velocities = [ 0.25, 1.3, 3.0 ]		# tommy / chuckie / spike

	def __init__( self ):
		BigWorld.Entity.__init__( self )

		# choose our model number
		self.modelNumber = int( self.id % 3 )

		# choose an initial index as a float
		#findex = random.random() * RugRat.nTargets
		#findex += self.id % RugRat.nTargets
		findex = ((self.id % 15)/ 15.0) * RugRat.nTargets
		while findex >= RugRat.nTargets:
			findex -= RugRat.nTargets

		# move to the position that corresponds to
		apt = RugRat.targets[ int(findex) ]
		bpt = RugRat.targets[ int(findex+1) % RugRat.nTargets ]
		t = findex - int(findex)
		self.moveToPoint( (	apt[0] * (1-t) + bpt[0] * t,
							0,
							apt[1] * (1-t) + bpt[1] * t	),
						RugRat.velocities[self.modelNumber] )

		# make the index an int
		self.targetIndex = int(findex)



	def onMove( self, cid, uid ):
		assert( 1 or cid or uid ) # Not used

		# ok, we're there - move to the next point then
		self.targetIndex = (self.targetIndex+1) % RugRat.nTargets
		pt = RugRat.targets[ self.targetIndex ]
		offset = self.modelNumber * 0.3
		self.moveToPoint( (pt[0] + offset, 0, pt[1] + offset),
			RugRat.velocities[self.modelNumber] )

# RugRat.py
