import WorldEditor
from WorldEditorDirector import bd
import Personality
import ResMgr
import BigWorld
from os import startfile

def doQuickSave( item ):
	"""This function forces a quick save operation."""
	Personality.preQuickSave()
	WorldEditor.quickSave()

def doFullSave( item ):
	"""This function forces a full save and process all operation."""
	Personality.preFullSave()
	WorldEditor.save()
	
def doRegenerateTerrainLODs( item ):
	"""This function regenerates the terrain LODs."""
	WorldEditor.regenerateLODs()
	
def canRegenerateTerrainLODs( item ):
	"""This function returns 1 if the terrain LODS can be regenerated, 0 if they can't."""
	return WorldEditor.canRegenerateLODs()

def convertTerrain( item ):
	"""This function converts the current space's terrain to the new format."""
	WorldEditor.convertCurrentTerrain()
	bd.enterChunkVizMode()

def canConvertTerrain( item ):
	"""Returns 0 if the terrain can be converted, 1 if it can't."""
	return WorldEditor.canConvertCurrentTerrain()

def resizeTerrainMaps( item ):
	"""This function resizes the current space's terrain maps."""
	WorldEditor.resizeTerrainMaps()
	bd.enterChunkVizMode()

def canResizeTerrainMaps( item ):
	"""Returns 0 if the terrain maps can be resized, 1 if it can't."""
	return WorldEditor.canResizeCurrentTerrain()

def doImport( item ):
	WorldEditor.importDataGUI()
	
def doExport( item ):
	WorldEditor.exportDataGUI()
	
def doUndo( item ):
	"""This function performs an undo operation."""
	what = WorldEditor.undo(0)
	if what:
		msg = ResMgr.localise( "SCRIPT/UIEXT_PY/UNDOING", what )
		WorldEditor.addCommentaryMsg( msg )
	WorldEditor.undo()

	bd.itemTool.functor.script.selUpdate()

def doRedo( item ):
	what = WorldEditor.redo(0)
	if what:
		msg = ResMgr.localise( "SCRIPT/UIEXT_PY/REDOING", what )
		WorldEditor.addCommentaryMsg( msg )
	WorldEditor.redo()

	bd.itemTool.functor.script.selUpdate()

def doSelectAll( item ):
	"""This function selects all editable items in all loaded chunks."""

	# If the scene browser was focused when CTRL+A was hit, select hidden and frozen items.
	selectHidden = WorldEditor.isSceneBrowserFocused()	
	selectFrozen = WorldEditor.isSceneBrowserFocused()
	
	group = WorldEditor.selectAll( selectHidden, selectFrozen )
	if ( group != None ):
		bd.itemTool.functor.script.selection.rem( bd.itemTool.functor.script.selection )
		bd.itemTool.functor.script.selection.add( group )
		bd.itemTool.functor.script.selUpdate()

def doDeselectAll( item ):
	if bd.itemTool.functor.script.selection.size:
		bd.itemTool.functor.script.selection.rem( bd.itemTool.functor.script.selection )
		bd.itemTool.functor.script.selUpdate()

def doSaveChunkTemplate( item ):
	if bd.itemTool.functor.script.selection.size:
		WorldEditor.saveChunkTemplate( bd.itemTool.functor.script.selection )
	else:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/NOTHING_SELECTED" )

def doSaveCameraPosition( item ):
	dir = WorldEditor.getOptionString( "space/mru0" )
	dirDS = ResMgr.openSection( dir )
	if not dirDS:
		msg = ResMgr.localise( "SCRIPT/UIEXT_PY/UNABLE_TO_OPEN_LOCAL_DIRECTORY", dir )
		WorldEditor.addCommentaryMsg( msg )
		return

	ds = dirDS["space.localsettings"]
	if ds == None:
		ds = dirDS.createSection( "space.localsettings" )

	if ds == None:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNABLE_TO_OPEN_SPACE_LOCALSETTINGS" )
		return


	m = WorldEditor.camera(0).view
	m.invert()
	ds.writeVector3( "startPosition", m.translation )
	ds.writeVector3( "startDirection", (m.roll, m.pitch, m.yaw) )
	ds.save()

	WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/CAMERA_POSITION_SAVED" )

def doSaveStartPosition( item ):
	dir = WorldEditor.getOptionString( "space/mru0" )
	dirDS = ResMgr.openSection( dir )
	if not dirDS:
		msg = ResMgr.localise( "SCRIPT/UIEXT_PY/UNABLE_TO_OPEN_LOCAL_DIRECTORY", dir )
		WorldEditor.addCommentaryMsg( msg )
		return

	ds = dirDS["space.settings"]
	if ds == None:
		ds = dirDS.createSection( "space.settings" )

	if ds == None:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNABLE_TO_OPEN_SPACE_SETTINGS" )
		return


	m = WorldEditor.camera().view
	m.invert()

	ds.writeVector3( "startPosition", m.translation )
	ds.writeVector3( "startDirection", (m.roll, m.pitch, m.yaw) )
	ds.save()

	WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/START_POSITION_SET_TO_CAMERA_POSITION" )

def onShowOrthoMode( item ):
		WorldEditor.setOptionInt( "camera/ortho", 1 )
		WorldEditor.changeToCamera(1)

def onHideOrthoMode( item ):
		WorldEditor.setOptionInt( "camera/ortho", 0 )
		WorldEditor.changeToCamera(0)

def onEnableUmbraMode( item ):
	""" Sets both Umbra and the useUmbra Option so that 
	    the game will start in the last set state
	"""
	try:
		BigWorld.setWatcher( "Render/Umbra/enabled", 1 )
		WorldEditor.setOptionInt( "render/useUmbra", 1 )
	except Exception:
		# An exception can happen if Umbra is compiled out, ignore
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UMBRA_NOT_INCLUDED" )

def onDisableUmbraMode( item ):
	""" Sets both Umbra and the useUmbra Option so that 
	    the game will start in the last set state
	"""
	try:
		BigWorld.setWatcher( "Render/Umbra/enabled", 0 )
		WorldEditor.setOptionInt( "render/useUmbra", 0 )
	except Exception:
		# An exception can happen if Umbra is compiled out, ignore
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UMBRA_NOT_INCLUDED" )

def updateUmbraEnabled( item ):
	ret = False
	try:
		if BigWorld.getWatcher( "Render/Umbra/enabled" ) == "true" and WorldEditor.getOptionInt( "render/useUmbra" ) == 1:
			ret = True
	except Exception:
		# An exception can happen if Umbra is compiled out, ignore
		pass
	return ret

def updateUmbraDisabled( item ):
	ret = True
	try:
		if BigWorld.getWatcher( "Render/Umbra/enabled" ) == "true" or WorldEditor.getOptionInt( "render/useUmbra" ) == 1:
			ret = False
	except Exception:
		# An exception can happen if Umbra is compiled out, ignore
		pass
	return ret
	
	
def onEnableDefaultWeather( item ):
	""" Sets both Umbra and the useUmbra Option so that 
	    the game will start in the last set state
	"""	
	WorldEditor.setOptionInt( "render/useDefaultWeather", 1)

def onDisableDefaultWeather( item ):
	""" Sets both Umbra and the useUmbra Option so that 
	    the game will start in the last set state
	"""
	WorldEditor.setOptionInt( "render/useDefaultWeather", 0)

def updateDefaultWeatherEnabled( item ):
	return WorldEditor.getOptionInt("render/useDefaultWeather") ==  1

def updateDefaultWeatherDisabled( item ):
	return WorldEditor.getOptionInt("render/useDefaultWeather") ==  0


def updateCamera():
	value = WorldEditor.getOptionString( "camera/speed" )
	c = WorldEditor.camera()
	c.speed = WorldEditor.getOptionFloat( "camera/speed/" + value, 60 )
	c.turboSpeed = WorldEditor.getOptionFloat( "camera/speed/" + value + "/turbo", 120 )

def doSlowCamera( item ):
	WorldEditor.setOptionString( "camera/speed", "Slow" );
	updateCamera()

def doMediumCamera( item ):
	WorldEditor.setOptionString( "camera/speed", "Medium" );
	updateCamera()

def doFastCamera( item ):
	WorldEditor.setOptionString( "camera/speed", "Fast" );
	updateCamera()

def doSuperFastCamera( item ):
	WorldEditor.setOptionString( "camera/speed", "SuperFast" );
	updateCamera()
	
def normalMode( item ):
	WorldEditor.setOptionInt( "render/chunk/vizMode", 0 )
	bd.enterChunkVizMode()

def boundaryBox( item ):
	WorldEditor.setOptionInt( "render/chunk/vizMode", 1 )
	bd.enterChunkVizMode()

def heightMap( item ):
	WorldEditor.setOptionInt( "render/chunk/vizMode", 2 )
	bd.enterChunkVizMode()

def meshMode( item ):
	WorldEditor.setOptionInt( "render/chunk/vizMode", 3 )
	bd.enterChunkVizMode()

def doSnapFreePositioning( item ):
	WorldEditor.setOptionInt( "snaps/itemSnapMode", 0 )
	bd.updateItemSnaps()

def doSnapTerrainLock( item ):
	WorldEditor.setOptionInt( "snaps/itemSnapMode", 1 )
	bd.updateItemSnaps()

def doSnapObstacleLock( item ):
	WorldEditor.setOptionInt( "snaps/itemSnapMode", 2 )
	bd.updateItemSnaps()
	
def doHideAllOutside( item ):
	WorldEditor.setOptionInt( "render/hideOutsideObjects", 1 )
	WorldEditor.setOptionInt( "render/scenery/shells/gameVisibility", 0 )

def doShowAllOutside( item ):
	WorldEditor.setOptionInt( "render/hideOutsideObjects", 0 )
	WorldEditor.setOptionInt( "render/scenery/shells/gameVisibility", 1 )

#
#  Panels functions
#  See getContentID in mainframe.cpp for info on the Panel/Tool IDs
#

#  setting the current tool mode
def doToolModeObject( item ):
	WorldEditor.setToolMode( "Objects" )
	
def doToolModeTerrainTexture( item ):
	WorldEditor.setToolMode( "TerrainTexture" )
	
def doToolModeTerrainHeight( item ):
	WorldEditor.setToolMode( "TerrainHeight" )
	
def doToolModeTerrainFilter( item ):
	WorldEditor.setToolMode( "TerrainFilter" )
	
def doToolModeTerrainMesh( item ):
	WorldEditor.setToolMode( "TerrainMesh" )
	
def doToolModeTerrainImpExp( item ):
	WorldEditor.setToolMode( "TerrainImpExp" )
	
def doToolModeProject( item ):
	WorldEditor.setToolMode( "Project" )

#  show panels

def doShowTools( item ):
	WorldEditor.showPanel( u"Tools", 1 )

def doShowToolObject( item ):
	WorldEditor.showPanel( u"Objects", 1 )

def doShowToolTerrainTexture( item ):
	WorldEditor.showPanel( u"TerrainTexture", 1 )

def doShowToolTerrainHeight( item ):
	WorldEditor.showPanel( u"TerrainHeight", 1 )

def doShowToolTerrainFilter( item ):
	WorldEditor.showPanel( u"TerrainFilter", 1 )

def doShowToolTerrainMesh( item ):
	WorldEditor.showPanel( u"TerrainMesh", 1 )

def doShowToolProject( item ):
	WorldEditor.showPanel( u"Project", 1 )

#  show/hide other panels
def doShowPanelUAL( item ):
	WorldEditor.showPanel( u"UAL", 1 )

def doShowPanelSceneBrowser( item ):
	WorldEditor.showPanel( u"SceneBrowser", 1 )

def doShowPanelPostProcessing( item ):
	WorldEditor.showPanel( u"PostProcessing", 1 )

def doShowPanelProperties( item ):
	WorldEditor.showPanel( u"Properties", 1 )

def doShowPanelOptionsGeneral( item ):
	WorldEditor.showPanel( u"Options", 1 )
	
def doShowPanelOptionsNavigation( item ):
	WorldEditor.showPanel( u"Navigation", 1 )

def doShowPanelOptionsWeather( item ):
	WorldEditor.showPanel( u"Weather", 1 )

def doShowPanelOptionsEnvironment( item ):
	WorldEditor.showPanel( u"Environment", 1 )

def doShowPanelHistogram( item ):
	WorldEditor.showPanel( u"Histogram", 1 )

def doShowPanelMessages( item ):
	WorldEditor.showPanel( u"Messages", 1 )

def doShowPanelChunkWatcher( item ):
	WorldEditor.showPanel( u"ChunkWatcher", 1 )

def doShowPanelChunkTexture( item ):
	WorldEditor.showPanel( u"PageChunkTexture", 1 )

def doRequestFeature( item ):
	startfile( "mailto:support@bigworldtech.com?subject=WorldEditor  %2D Feature Request %2F Bug Report" )
	

#	Hide/Freeze clearing the selection

def doHideSelection( item ):
	message = WorldEditor.hideChunkItems( bd.itemTool.functor.script.selection )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	
def doUnhideSelection( item ):
	message = WorldEditor.hideChunkItems( bd.itemTool.functor.script.selection, False )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )

def unhideAllInternal( ignoreSelectionFilter ):
	if ignoreSelectionFilter:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNHIDE_ALL_OBJECTS", 0 )
	else:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNHIDE_ALL_SELECTABLE_OBJECTS", 0 )

	group = WorldEditor.selectAll( True, False, ignoreSelectionFilter )
	if group != None:
		message = WorldEditor.hideChunkItems( group, False )
		if message != None:
			WorldEditor.addCommentaryMsg( message, 0 )	
			
def doUnhideAllFilter( item ):
	unhideAllInternal( False )
	
def doUnhideAll( item ):
	unhideAllInternal( True )

def doFreezeSelection( item ):
	message = WorldEditor.freezeChunkItems( bd.itemTool.functor.script.selection )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	

def doUnfreezeSelection( item ):
	message = WorldEditor.freezeChunkItems( bd.itemTool.functor.script.selection, False )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	

def unfreezeAllInternal( ignoreSelectionFilter ):
	if ignoreSelectionFilter:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNFREEZE_ALL_OBJECTS", 0 )
	else:
		WorldEditor.addCommentaryMsg( "`SCRIPT/UIEXT_PY/UNFREEZE_ALL_SELECTABLE_OBJECTS", 0 )
	group = WorldEditor.selectAll( False, True, ignoreSelectionFilter )
	if ( group != None ):
		message = WorldEditor.freezeChunkItems( group, False )
		if message != None:
			WorldEditor.addCommentaryMsg( message, 0 )

def doUnfreezeAllFilter( item ):
	unfreezeAllInternal( False )
	
def doUnfreezeAll( item ):
	unfreezeAllInternal( True )

#	Hide/Freeze keeping the selection

def doHideSelectionAndKeep( item ):
	message = WorldEditor.hideChunkItems( bd.itemTool.functor.script.selection, True, True )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	
def doUnhideSelectionAndKeep( item ):
	message = WorldEditor.hideChunkItems( bd.itemTool.functor.script.selection, False, True )
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )

def doFreezeSelectionAndKeep( item ):
	message = WorldEditor.freezeChunkItems( bd.itemTool.functor.script.selection, True, True )
	bd.resetSelUpdate() # refresh the selection to update the properties panel
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	

def doUnfreezeSelectionAndKeep( item ):
	message = WorldEditor.freezeChunkItems( bd.itemTool.functor.script.selection, False, True )
	bd.resetSelUpdate() # refresh the selection to update the properties panel
	if message != None:
		WorldEditor.addCommentaryMsg( message, 0 )
	

