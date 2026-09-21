import WorldEditor
import ResMgr

import ToolbarUIAdapter
reload( ToolbarUIAdapter )
import TerrainUIAdapter
reload( TerrainUIAdapter )
import ItemUIAdapter
reload( ItemUIAdapter )
import Actions
reload( Actions )

from WorldEditorDirector import bd
from WorldEditorDirector import oi
from ToolbarUIAdapter import *
from TerrainUIAdapter import *
from ItemUIAdapter import *
from WeatherUIAdapter import *
from Actions import *


"""This module routes user interface events from the Borland GUI through
to the c++ WorldEditor and python WorldEditorDirector"""


#--------------------------------------------------------------------------
#	Section - unimplemented methods
#--------------------------------------------------------------------------
def onButtonClick( name ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/CLICK_NOT_IMPLEMENTED", name )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onSliderAdjust( name, value, min, max ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/ADJUST_NOT_IMPLEMENTED", name, str( min ), str( value ), str( max ) )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onCheckBoxToggle( name, value ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/TOGGLE_NOT_IMPLEMENTED", name, str( value ) )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onComboBoxSelect( name, selectionName ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/SELECT_NOT_IMPLEMENTED", name, selectionName )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onEvent( event, value ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/EVENT_NOT_IMPLEMENTED", event, str( value ) )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onBrowserItemSelect( name, filename ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/ITEM_NOT_IMPLEMENTED", name, filename )
	WorldEditor.addCommentaryMsg( msg, 1 )

def onListItemSelect( name, index ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/LIST_ITEM_NOT_IMPLEMENTED", name, str( index ) )
	WorldEditor.addCommentaryMsg( msg, 1 )


# ------------------------------------------------------------------------------
# Section: Individual command methods
# ------------------------------------------------------------------------------

# ---- Far plane ----

def slrFarPlaneAdjust( value, min, max ):
	"""This function sets the farPlane distance to the given value parameter."""
	WorldEditor.farPlane( value )

def slrFarPlaneUpdate():
	"""This function returns the farPlane distance."""
	return WorldEditor.farPlane()

def edtFarPlaneExit( value ):
	"""This function allows the farPlane distance to be set in centimetres and metres."""
	if value[-2:] == "cm":
		floatValue = float(value[:-2])/100.0
	elif value[-1] == "m":
		floatValue = float(value[:-1])
	else:
		floatValue = float(value)

	WorldEditor.farPlane( floatValue )

def edtFarPlaneUpdate():
	"""This function returns the farPlane distance in metres."""
	return "%.0fm" % (WorldEditor.farPlane(), )

# ---- Misc ----

def slrProjectCurrentTimeAdjust( value, min, max ):
	percent = (value-min) / (max-min) * 23.9
	WorldEditor.romp.setTime( percent )

# ---- Snaps ----

def edtMiscSnapsXExit( value ):
	if value[-2:] == "cm":
		floatValue = float(value[:-2])/100.0
	elif value[-1] == "m":
		floatValue = float(value[:-1])
	else:
		floatValue = float(value)

	ns = WorldEditor.getOptionVector3( "snaps/movement" )
	WorldEditor.setOptionVector3( "snaps/movement", ( floatValue, ns[1], ns[2] ) )

def edtMiscSnapsXUpdate():
	snaps = WorldEditor.getOptionVector3( "snaps/movement" )
	return "%0.1fm" % (snaps[0], )


def edtMiscSnapsYExit( value ):
	if value[-2:] == "cm":
		floatValue = float(value[:-2])/100.0
	elif value[-1] == "m":
		floatValue = float(value[:-1])
	else:
		floatValue = float(value)

	ns = WorldEditor.getOptionVector3( "snaps/movement" )
	WorldEditor.setOptionVector3( "snaps/movement", ( ns[0], floatValue, ns[2] ) )

def edtMiscSnapsYUpdate():
	snaps = WorldEditor.getOptionVector3( "snaps/movement" )
	return "%0.1fm" % (snaps[1], )


def edtMiscSnapsZExit( value ):
	if value[-2:] == "cm":
		floatValue = float(value[:-2])/100.0
	elif value[-1] == "m":
		floatValue = float(value[:-1])
	else:
		floatValue = float(value)

	ns = WorldEditor.getOptionVector3( "snaps/movement" )
	WorldEditor.setOptionVector3( "snaps/movement", ( ns[0], ns[1], floatValue ) )

def edtMiscSnapsZUpdate():
	snaps = WorldEditor.getOptionVector3( "snaps/movement" )
	return "%0.1fm" % (snaps[2], )


def pgcAllToolsTabSelect( value ):
	global bd

	if value == "tabTerrain":
		if ( bd != None ):
			bd.enterMode( "Terrain" )
	elif value == "tabTerrainImport":
		if ( bd != None ):
			bd.enterMode( "Height" )
	elif value in ("tabObject", "tabScene"):
		if ( bd != None ):
			bd.enterMode( "Object" )
	elif value == "tabProject":
		if ( bd != None ):
			bd.enterMode( "Project" )
	elif ( bd != None ):
		if ( bd.getMode() == "Project" ):
			bd.enterMode( "Object" ) # enter Object mode if in Project mode


def pgcObjectsTabSelect( value ):
	global oi
	if value != "tabObjectUal":
		if value == "tabObjectShell" or value == "tabPrefabs" or value == "tabObjectPrefabs":
			oi.setShellMode( 1 )
		else:
			oi.setShellMode( 0 )

# Set the active tab to bd.currentTab, if it's specified
def pgcAllToolsUpdate():
	global bd

	val = None

	if bd != None and hasattr( bd, "currentTab" ):
		val = bd.currentTab
		bd.currentTab = None

	return val


#--------------------------------------------------------------------------
#	Section - The Project tab
#--------------------------------------------------------------------------
def projectLock( commitMsg ):
	"""This function locks the project for editing the locked chunks.
	Locked chunks can only be edited with the editor that locked them."""
	WorldEditor.projectLock( commitMsg )

def actProjectProgressExecute():
	WorldEditor.projectProgress()

def projectCommitChanges( commitMsg, keepLocks ):
	"""This function commits the changes to the locked chunks in the project to the repository."""
	WorldEditor.projectCommit( commitMsg, keepLocks )

def projectDiscardChanges( commitMsg, keepLocks ):
	"""This function discards changes made to the locked chunks while the project was locked."""
	WorldEditor.projectDiscard( commitMsg, keepLocks )

def projectUpdateSpace():
	"""This function retrieves updates made to the space from the repository."""
	WorldEditor.projectUpdateSpace()
	
def projectCalculateMap():
	WorldEditor.projectCalculateMap()

def projectExportMap():
	WorldEditor.projectExportMap()

def slrProjectMapBlendAdjust( value, min, max ):
	WorldEditor.projectMapAlpha( (value-min) / (max-min) )
		
def slrProjectMapBlendUpdate():
	return 1.0 + WorldEditor.projectMapAlpha() * 99.0

selectFilters = (
					( "All" , "" ),
					( "All Except Terrain and Shells" , "" ),
					# Raymond, simple modification to change the name
					# ( "Shells Only" , "" ),
					( "Shells + Contents" , "" ),
					( "All Lights" , "spotLight|ambientLight|directionalLight|omniLight|flare|pulseLight" ),
					( "Omni Lights" , "omniLight" ),
					( "Ambient Lights" , "ambientLight" ),
					( "Directional Lights" , "directionalLight" ),
					( "Pulse Lights" , "pulseLight" ),
					( "Spot Lights" , "spotLight" ),
					( "Models" , "model|speedtree" ),
					( "Trees" , "speedtree" ),
					( "Entities" , "entity" ),
					( "Clusters and Markers" , "marker|marker_cluster" ),
					( "Particles" , "particles" ),
					( "Waypoint Stations" , "station" ),
					( "Terrain" , "terrain" ),
					( "Sounds" , "sound" ),
					( "Water" , "water" ),
					( "Portals" , "portal" ),
					( "User Data Objects" , "UserDataObject" ),
					( "Hidden Objects" , "hidden" ),
					( "Frozen Objects" , "frozen" )
				)

def cmbSelectFilterKeys():
	return selectFilters

def cmbSelectFilterUpdate():
	return (WorldEditor.getOptionString( "tools/selectFilter" ), )

def setSelectionFilter( name ):
	"""This function sets the selection filter."""
	filter = ""
	for item in selectFilters:
		if item[0] == name:
			filter = item[1]

	WorldEditor.setSelectionFilter( filter )

	if name == "Portals":
		WorldEditor.setNoSelectionFilter( "" )
	else:
		WorldEditor.setNoSelectionFilter( "portal" )

	if name == "All Except Terrain and Shells":
		WorldEditor.setNoSelectionFilter( "portal|terrain" )
		WorldEditor.setSelectShellsOnly( 2 )
	elif name == "Shells + Contents":
		WorldEditor.setSelectShellsOnly( 1 )
	elif name == "Models":
		WorldEditor.setSelectShellsOnly( 2 )
	else:
		WorldEditor.setSelectShellsOnly( 0 )
		
def cmbSelectFilterChange( value ):
	if(	WorldEditor.getOptionString( "tools/selectFilter" ) != value ):
		msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/SELECTION_FILTER", value )
		WorldEditor.addCommentaryMsg( msg )
		WorldEditor.setOptionString( "tools/selectFilter", value )
	setSelectionFilter( value )
	WorldEditor.setToolMode( "Objects", )

def doSetSelectionFilter( item ):
	cmbSelectFilterChange( item.displayName )
	pass

def updateSelectionFilter( item ):
	if item.displayName == WorldEditor.getOptionString( "tools/selectFilter" ):
		return 1
	return 0

coordFilters = (
					( "World" , "" ),
					( "Local" , "" ),
					( "View" , "" ),
				)


def cmbCoordFilterKeys():
	return coordFilters

def cmbCoordFilterUpdate():
	return (WorldEditor.getOptionString( "tools/coordFilter" ), )

def cmbCoordFilterChange( value ):
	msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/REFERENCE_COORDINATE_SYSTEM", value )
	WorldEditor.addCommentaryMsg( msg )
	WorldEditor.setOptionString( "tools/coordFilter", value )

def actSaveCameraPositionExecute():
	dir = WorldEditor.getOptionString( "space/mru0" )
	dirDS = ResMgr.openSection( dir )
	if not dirDS:
		msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/UNABLE_TO_OPEN_LOCAL_DIRECTORY", dir )
		WorldEditor.addCommentaryMsg( msg )
		return

	ds = dirDS["space.localsettings"]
	if ds == None:
		ds = dirDS.createSection( "space.localsettings" )

	if ds == None:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIADAPTER_PY/UNABLE_TO_OPEN_SPACE_LOCALSETTINGS" )
		return


	m = WorldEditor.camera(0).view
	m.invert()
	ds.writeVector3( "startPosition", m.translation )
	ds.writeVector3( "startDirection", (m.roll, m.pitch, m.yaw) )
	ds.save()

	WorldEditor.addCommentaryMsg( "`SCRIPT/UIADAPTER_PY/CAMERA_POSITION_SAVED" )



def actSaveStartPositionExecute():
	dir = WorldEditor.getOptionString( "space/mru0" )
	dirDS = ResMgr.openSection( dir )
	if not dirDS:
		msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/UNABLE_TO_OPEN_LOCAL_DIRECTORY", dir )
		WorldEditor.addCommentaryMsg( msg )
		return

	ds = dirDS["space.settings"]
	if ds == None:
		ds = dirDS.createSection( "space.settings" )

	if ds == None:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIADAPTER_PY/UNABLE_TO_OPEN_SPACE_SETTINGS" )
		return


	m = WorldEditor.camera().view
	m.invert()

	ds.writeVector3( "startPosition", m.translation )
	ds.writeVector3( "startDirection", (m.roll, m.pitch, m.yaw) )
	ds.save()

	WorldEditor.addCommentaryMsg( "`SCRIPT/UIADAPTER_PY/START_POSITION_SET_TO_CAMERA_POSITION" )

def canSavePrefab():
	return bd.itemTool.functor.script.selection.size;

def savePrefab( name ):
	message = WorldEditor.saveChunkPrefab( bd.itemTool.functor.script.selection, name )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )

#--------------------------------------------------------------------------
# Section - ItemUIAdapter
#--------------------------------------------------------------------------

def brwObjectItemSelect( self, value ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	cmbSelectFilterChange( "All" )

def brwObjectModelItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Model" )
	oi.setShellMode( 0 )
	if filter == "":
		filter = "Models"
	cmbSelectFilterChange( filter )

def brwObjectShellItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Shell" )
	oi.setShellMode( 1 )
	if filter == "":
# Raymond, simple modification to change the name	
		# filter = "Shells Only"
		filter = "Shells + Contents"
	cmbSelectFilterChange( filter )

def brwObjectPrefabsItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Prefabs" )
	if filter == "":
		filter = "All"
	cmbSelectFilterChange( filter )

def brwObjectEntityItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Entity" )
	if filter == "":
		filter = "Entities"
	cmbSelectFilterChange( filter )

def brwObjectLightsItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Lights" )
	if filter == "":
		filter = "All Lights"
	cmbSelectFilterChange( filter )

def brwObjectParticlesItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Particles" )
	if filter == "":
		filter = "Particles"
	cmbSelectFilterChange( filter )

def brwObjectMiscItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	filter = oi.setObjectTab( "Misc" )
	if filter == "":
		filter = "All Except Terrain and Shells"
	cmbSelectFilterChange( filter )

def brwObjectEntityBaseClassesItemSelect( value, dblClick ):
	global oi
	oi.setBrowsePath( value )
	oi.showBrowse()
	cmbSelectFilterChange( "Entities" )


#--------------------------------------------------------------------------
# Section - UAL related methods
#--------------------------------------------------------------------------

def ualSelectFilterChange( value ):
	if(	WorldEditor.getOptionString( "tools/selectFilter" ) != value ):
		msg = ResMgr.localise( "SCRIPT/UIADAPTER_PY/SELECTION_FILTER", value )
		WorldEditor.addCommentaryMsg( msg )
		WorldEditor.setOptionString( "tools/selectFilter", value )
	setSelectionFilter( value )

def brwObjectUalItemSelect( value, dblClick ):
	
	global oi
	if value.find( "/shells" ) == -1 and value[:7] != "shells/":
		if WorldEditor.isTerrainTexture( value ) and dblClick:
			WorldEditor.setToolMode( "TerrainTexture" )
			WorldEditor.setCurrentTexture( value )
		elif value[-6:] == ".brush":
			WorldEditor.setToolMode( "TerrainTexture" )
			WorldEditor.setCurrentBrush( value )
		elif (	value[-6:] == ".model" or
				value[-4:] == ".def" or
				value[-4:] == ".spt" or
				value[-7:] == ".prefab" or
				value[-4:] == ".xml"):
			WorldEditor.setToolMode( "Objects" )
			oi.setShellMode( 0 )
			ualSelectFilterChange( "All Except Terrain and Shells" )
	else:
		WorldEditor.setToolMode( "Objects" )
		oi.setShellMode( 1 )
		ualSelectFilterChange( "Shells + Contents" )
	oi.setBrowsePath( value )
	oi.showBrowse()

def brwObjectItemAdd( ):
	bd.itemTool.functor.script.addChunkItem()

def contextMenuGetItems( type, path ):
	if path[-4:] == ".xml" and path.find( "particles" ) != -1:
		return [ ( 1, ResMgr.localise("WORLDEDITOR/WORLDEDITOR/CHUNK/EDITOR_CHUNK_PARTICLE/EDIT_IN_PARTICLE_EDITOR") ) ]
	elif path[-6:] == ".model":
		return [ ( 2, ResMgr.localise("WORLDEDITOR/WORLDEDITOR/CHUNK/EDITOR_CHUNK_MODEL/EDIT_IN_MODEL_EDITOR") )]
	return []

def contextMenuHandleResult( type, path, command ):
	if command == 1:
		WorldEditor.launchTool( "particleeditor", "-o \"" + path + "\"" )
	elif command == 2:
		WorldEditor.launchTool( "modeleditor", "-o \"" + path + "\"" )

# set selection filter at launch
setSelectionFilter( WorldEditor.getOptionString( "tools/selectFilter" ) )


#--------------------------------------------------------------------------
# Section - PageChunkTexture related methods
#--------------------------------------------------------------------------

def setTerrainTextureParams( texture, uProjection, vProjection ):
	"""This function changes the current texture used to paint the terrain.""" 
	WorldEditor.setCurrentTextureFull( texture, uProjection, vProjection )


#--------------------------------------------------------------------------
# Section - Scene Browser related methods
#--------------------------------------------------------------------------

def deleteChunkItems( selection ):
	"""This function deletes the specified chunk items."""
	WorldEditor.deleteChunkItems( selection )
