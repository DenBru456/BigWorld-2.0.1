from controls import *

envSetup = \
"""
from Helpers import GraphicsOptions
"""

args = \
(
	WatcherIntSlider( "FarPlane", "Render/Far Plane", minMax = (10, 5000) ),
	WatcherFloatEnum( "Wireframe", "Render/Wireframe Mode",
		(	( "Off",		0 ),
			( "Terrain",	1 ),
			( "Objects",	2 ),
			( "Everything",	3 )
		) ),
	WatcherCheckBox( "Vertical_Blank", "Render/waitForVBL" ),
	WatcherCheckBox( "Frame_Rate_Graph", "Render/DisplayFramerateGraph" ),
	Divider(),
	WatcherCheckBox( "Use Visual Compounding", "Chunks/Use Compound" ),
	WatcherCheckBox( "Draw Terrain", "Render/Terrain/draw" ),
	WatcherCheckBox( "Draw Water", "Client Settings/Water/draw" ),
	
	Divider(),
	
	CheckBox( "Compressed_Normal_Maps", \
		updateCommand = "GraphicsOptions.normalMapsCompressed()", \
		setCommand = "GraphicsOptions.compressNormalMaps(Compressed_Normal_Maps)" ),
	CheckBox( "Sky_Light_Map_Enable", \
		updateCommand = "GraphicsOptions.optIncludeOptionEnabled('SKY_LIGHT_MAP_ENABLE')", \
		setCommand = "GraphicsOptions.enableOptincludeOption('SKY_LIGHT_MAP_ENABLE', Sky_Light_Map_Enable)" ),
	CheckBox( "Mod_X2_Enable", \
		updateCommand = "GraphicsOptions.optIncludeOptionEnabled('MOD2X')", \
		setCommand = "GraphicsOptions.enableOptincludeOption('MOD2X', Mod_X2_Enable)" ),
	CheckBox( "Terrain_Specular_Enable", \
		updateCommand = "GraphicsOptions.optIncludeOptionEnabled('TERRAIN_SPECULAR_ENABLE')", \
		setCommand = "GraphicsOptions.enableOptincludeOption('TERRAIN_SPECULAR_ENABLE', Terrain_Specular_Enable)" ),
)

commands = \
(
	( "Turn Off HUD" 		, "$p.statsGui.fader.value = 0" ),
	( "Turn On HUD" 		, "$p.statsGui.fader.value = 4" ),	
	( "Restart Game", """ BigWorld.restartGame() """ ),	
)
