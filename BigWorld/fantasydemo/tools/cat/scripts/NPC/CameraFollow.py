from controls import *

args = ()

commands = \
(
	( "Follow Target with camera" , """
c = BigWorld.FlexiCam()
target = None
target = $B.target.entity.focalMatrix
if target == None: target = $B.target().entity.model.root
c.target = target
c.preferredPos = (0.3,0,-2)
c.viewOffset = (0,0,0)
c.timeMultiplier = 8
if target != None: $B.camera(c)
	""" ),
	( "Player Camera" , """
FantasyDemo.rds.cc.inaccuracyProvider=None
FantasyDemo.rds.updatePivotDist()
FantasyDemo.cameraType(0)
	""" ),
)
