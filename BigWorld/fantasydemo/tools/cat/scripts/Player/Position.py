from controls import *

args = (
	StaticText( "position", updateCommand = """
location = $B.findChunkFromPoint( $p.position ).split( '@' )
print \"(%.1f,%.1f,%.1f) @ %s @ %s\" % ( $p.position.x, $p.position.y, $p.position.z, location[0], location[1] )
		""" ),

	Float( "x", updateCommand = "$p.position.x" ),
	Float( "y", updateCommand = "$p.position.y" ),
	Float( "z", updateCommand = "$p.position.z" )
		 )

commands = \
(
	( "Teleport" , "$p.physics.teleport( (x, y, z) )" ),
)
