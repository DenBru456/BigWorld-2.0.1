# -*- coding: utf-8 -*-

import BigWorld
import Helpers.PyGUI as PyGUI
import ResMgr
import Keys
from functools import partial
from bwdebug import ERROR_MSG
import types
import Cursor
import PostProcessing
from PostProcessing.Effects import *

from Helpers.PyGUI import PyGUIEvent
from FDToolTip import ToolTipInfo
import FantasyDemo

import weakref

class EffectSliderInfo:
	def __init__( self, prop, min = 0.0, max = 1.0, uiDesc = "" ):
		self.prop = prop
		self.minValue = min
		self.maxValue = max
		self.uiDesc = uiDesc


	def apply( self, slider, label, amountLabel ):
		label.text = self.uiDesc
		slider.script.minValue = self.minValue
		slider.script.maxValue = self.maxValue
		slider.script.stepSize = (self.maxValue - self.minValue) / 500.0
		try:
			value = self.prop.get()
			if value != None:
				try:
					amountLabel.text = self.prop.format(value)
					slider.script._setValue( value )
				except:
					amountLabel.text = "err"
		except NameError:
			label.text = "Unavailable"
			amountLabel.text = ""


	def updateAmountLabel( self, label ):
		value = self.prop.get()
		if value != None:
			label.text = self.prop.format(value)


class EffectButtonInfo:
	def __init__( self, name, preset, sl1, sl2, sl3  ):
		self.name = name
		self.preset = preset
		self.sliderName = [sl1,sl2,sl3]
		self.component = None


	def isSupported( self ):
		if self.preset is not None:
			if self.preset == "default":
				return True
			else:
				return PostProcessing.isSupported( self.preset )
		else:
			#it comes down to the sliders.  Currently just
			#allow the button to be supported, and the sliders
			#themselves report as 'unavailable' or not.
			return True


class PostProcessingWindow( PyGUI.DraggableWindow ):

	factoryString = "FDGUI.PostProcessingWindow"
	sliders = {}
	sliders['Sharpness'] = EffectSliderInfo( Sharpen.amount,0.0,1.0,"Sharpness" )
	sliders['Saturation'] = EffectSliderInfo( ColourCorrect.saturation,-1.0,1.0,"Saturation" )
	sliders['Brightness'] = EffectSliderInfo( ColourCorrect.brightness,-1.0,1.0,"Brightness" )
	sliders['Bloom'] = EffectSliderInfo( Bloom.amount, 0.0,2.0,"Bloom Amount" )
	sliders['Colour Correction'] = EffectSliderInfo( ColourCorrect.amount,0.0,1.0,"Colour Correction" )
	sliders['Tone Map'] = EffectSliderInfo( ColourCorrect.toneMap,0.0,1.0,"Tone Map" )
	sliders['Focal Length'] = EffectSliderInfo( DepthOfField.focalLength,0.0,0.5,"Focal Length" )
	sliders['Aperture'] = EffectSliderInfo( DepthOfField.aperture,0.001,0.1,"Aperture" )
	sliders['Focal Distance'] = EffectSliderInfo( DepthOfField.zFocus,0.1,100.0,"Focal Distance" )
	sliders['Noise Threshold'] = EffectSliderInfo( ScotopicVision.noiseThreshold,0.0,1.0,"Noise Threshold" )
	sliders['Noise Level'] = EffectSliderInfo( ScotopicVision.noiseLevel,0.0,20.0,"Noise Level" )
	sliders['Texture Scale'] = EffectSliderInfo( ScotopicVision.textureScale,0.1,15.0,"Texture Scale" )
	sliders['Edge Dilation Threshold'] = EffectSliderInfo( Posterise.edgeDilation,0.0,1.0,"Edge Dilation Threshold" )
	sliders['PoEAmount'] = EffectSliderInfo( Posterise.amount,0.0,1.0,"Amount" )
	sliders['SetMaxCoC2'] = EffectSliderInfo( DepthOfField.maxCoC2,0.0,64.0,"Circle of Confusion max." )
	sliders['Bokeh Amount'] = EffectSliderInfo( DepthOfField.bokehAmount,0.0,4.0,"Bokeh Amount" )
	sliders['Bokeh Type'] = EffectSliderInfo( DepthOfField.bokehType,0.0,1.0,"Bokeh Type" )
	sliders['Dof2Falloff'] = EffectSliderInfo( DepthOfField.falloff,0.0,10.0,"Falloff" )
	sliders['Dof2ZNear'] = EffectSliderInfo( DepthOfField.zNear,0.0,1.0,"Near Z" )
	sliders['Dof2ZFar'] = EffectSliderInfo( DepthOfField.zFar,0.0,1.0,"Far Z" )
	sliders['DistortAlpha'] = EffectSliderInfo( DistortionTransfer.alpha,0.0,1.0,"Alpha" )
	sliders['DistortScale'] = EffectSliderInfo( DistortionTransfer.scale,0.0,1.0,"Amount" )
	sliders['DistortTile'] = EffectSliderInfo( DistortionTransfer.tile,1.0,128.0,"Tile" )
	sliders['FilmGrainAlpha'] = EffectSliderInfo( FilmGrain.alpha,0.0,5.0,"Alpha" )
	sliders['Speed'] = EffectSliderInfo( FilmGrain.speed,0.0,0.5,"Speed" )
	sliders['FilmGrainScale'] = EffectSliderInfo( FilmGrain.scale,1.0,50.0,"Scale" )
	sliders['FilmGrainAlpha2'] = EffectSliderInfo( FilmGrain.alpha2,0.0,5.0,"Alpha" )
	sliders['Speed2'] = EffectSliderInfo( FilmGrain.speed2,0.0,0.5,"Speed" )
	sliders['FilmGrainScale2'] = EffectSliderInfo( FilmGrain.scale2,1.0,50.0,"Scale" )
	sliders['Hatching Power'] = EffectSliderInfo( Hatching.power,0.5,64.0,"Power" )
	sliders['Hatching Tile'] = EffectSliderInfo( Hatching.tile,1.0,128.0,"Tile" )
	sliders['Hatching Scale'] = EffectSliderInfo( Hatching.scale,0.0,15.0,"Scale" )
	sliders['Dof3Alpha'] = EffectSliderInfo( DepthOfField.dof3Alpha,0.0,1.0,"Alpha" )
	sliders['Dof3Overdrive'] = EffectSliderInfo( DepthOfField.dof3Overdrive,0.0,5.0,"Overdrive" )
	sliders['Rainbow Amount'] = EffectSliderInfo( Rainbow.amount,0.0,1.0,"Amount" )
	sliders['Rainbow Droplet Size'] = EffectSliderInfo( Rainbow.dropletSize,0.0,1.0,"Droplet Size" )	
	
	buttons = []
	# Name of button, preset xml file, then the identifier of the 3 sliders for that page.
	buttons.append( EffectButtonInfo( 'Colour Mixing', None, 'Sharpness', 'Saturation', 'Brightness' ) )
	buttons.append( EffectButtonInfo( 'Colour Correction', None, 'Colour Correction', 'Tone Map', 'Saturation' ) )	
	buttons.append( EffectButtonInfo( 'Night vision', None, 'Noise Level', 'Noise Threshold', 'Texture Scale') )
	buttons.append( EffectButtonInfo( 'Cel Shading', None, 'PoEAmount', 'Edge Dilation Threshold', 'Saturation') )
	buttons.append( EffectButtonInfo( 'Lens Simulated', None, 'Focal Length', 'Aperture', 'Focal Distance') )
	buttons.append( EffectButtonInfo( 'Lens Explicit', None, 'Dof2Falloff', 'Dof2ZNear', 'Dof2ZFar') )
	buttons.append( EffectButtonInfo( 'Depth of Field2', None, 'Focal Length', 'Aperture', 'Focal Distance') )
	buttons.append( EffectButtonInfo( 'Film Grain', None, 'FilmGrainAlpha', 'Speed', 'FilmGrainScale') )
	buttons.append( EffectButtonInfo( 'Film Grain2', None, 'FilmGrainAlpha2', 'Speed2', 'FilmGrainScale2') )
	buttons.append( EffectButtonInfo( 'Bokeh Control', None, 'Bokeh Amount', 'SetMaxCoC2', 'Bokeh Type') )
	buttons.append( EffectButtonInfo( 'Depth of Field 3', None, 'Dof3Alpha', 'Dof3Overdrive', 'Dof2ZFar') )	
	buttons.append( EffectButtonInfo( 'Fisheye', None, 'DistortAlpha', 'DistortScale', 'DistortTile') )
	buttons.append( EffectButtonInfo( 'Hatching', None, 'Hatching Scale', 'Hatching Power', 'Hatching Tile') )
	buttons.append( EffectButtonInfo( 'Rainbow', None, 'Rainbow Amount', 'Rainbow Droplet Size', 'Sharpness') )
	buttons.append( EffectButtonInfo( 'Default', "default", 'Sharpness', 'Colour Correction', 'Tone Map') )
	buttons.append( EffectButtonInfo( 'Depth of Field', "system/post_processing/chains/preset_depth_of_field.ppchain", 'Dof2ZFar', 'Dof2Falloff', 'Dof3Overdrive') )
	buttons.append( EffectButtonInfo( 'Tone Mapping', "system/post_processing/chains/preset_tone_mapping.ppchain", 'Colour Correction', 'Tone Map', 'Saturation') )
	buttons.append( EffectButtonInfo( 'Cartoon', "system/post_processing/chains/preset_cartoon.ppchain", 'PoEAmount', 'Edge Dilation Threshold', 'Saturation') )
	buttons.append( EffectButtonInfo( 'Film Noir', "system/post_processing/chains/preset_film_noir.ppchain", 'Saturation', 'FilmGrainScale', 'FilmGrainScale2') )
	buttons.append( EffectButtonInfo( 'Cross Hatching', "system/post_processing/chains/preset_cross_hatching.ppchain", 'Hatching Scale', 'Hatching Power', 'Hatching Tile') )
	buttons.append( EffectButtonInfo( 'Night Vision', "system/post_processing/chains/preset_night_vision.ppchain", 'Noise Threshold', 'Noise Level', 'Texture Scale') )
	buttons.append( EffectButtonInfo( 'Weird', "system/post_processing/chains/preset_weird.ppchain", 'Sharpness', 'Saturation', 'Brightness') )


	def __init__( self, component ):
		PyGUI.DraggableWindow.__init__( self, component )
		self.dg = None
		PostProcessing.registerGraphicsSettingListener( self._onSelectQualityOption )
	
	
	def buttonSet( self, idx ):
		self.buttons = []
		idx = idx % 3
		self.btnSet = idx
		if idx == 0:
			self.buttons.append( "Default" )
			self.buttons.append( "Depth of Field" )
			self.buttons.append( "Tone Mapping" )
			self.buttons.append( "Cartoon" )
			self.buttons.append( "Film Noir" )
			self.buttons.append( "Cross Hatching" )
			self.buttons.append( "Night Vision" )
			self.buttons.append( "Weird" )
		elif idx == 1:
			self.buttons.append( "Colour Mixing" )
			self.buttons.append( "Night vision" )
			self.buttons.append( "Lens Simulated" )
			self.buttons.append( "Lens Explicit" )
			self.buttons.append( "Depth of Field 3" )
			self.buttons.append( 'Colour Correction' )
			self.buttons.append( "Cel Shading" )
			self.buttons.append( "Hatching" )
		else:
			self.buttons.append( 'Colour Mixing' )
			self.buttons.append( 'Colour Correction' )
			self.buttons.append( 'Film Grain' )
			self.buttons.append( 'Film Grain2' )
			self.buttons.append( "Cel Shading" )
			self.buttons.append( "Hatching" )
			self.buttons.append( 'Fisheye' )
			self.buttons.append( 'Rainbow' )
		assert( len(self.buttons) == 8 )

		effectsGrid = self.component.effectsGrid
		self._findButtonInfo(0).component 	= weakref.proxy( effectsGrid.effect1Button.box )
		self._findButtonInfo(0).label 		= weakref.proxy( effectsGrid.effect1Button.label )
		self._findButtonInfo(1).component 	= weakref.proxy( effectsGrid.effect2Button.box )
		self._findButtonInfo(1).label 		= weakref.proxy( effectsGrid.effect2Button.label )
		self._findButtonInfo(2).component 	= weakref.proxy( effectsGrid.effect3Button.box )
		self._findButtonInfo(2).label 		= weakref.proxy( effectsGrid.effect3Button.label )
		self._findButtonInfo(3).component 	= weakref.proxy( effectsGrid.effect4Button.box )
		self._findButtonInfo(3).label 		= weakref.proxy( effectsGrid.effect4Button.label )
		self._findButtonInfo(4).component 	= weakref.proxy( effectsGrid.effect5Button.box )
		self._findButtonInfo(4).label 		= weakref.proxy( effectsGrid.effect5Button.label )
		self._findButtonInfo(5).component 	= weakref.proxy( effectsGrid.effect6Button.box )
		self._findButtonInfo(5).label 		= weakref.proxy( effectsGrid.effect6Button.label )
		self._findButtonInfo(6).component 	= weakref.proxy( effectsGrid.effect7Button.box )
		self._findButtonInfo(6).label 		= weakref.proxy( effectsGrid.effect7Button.label )
		self._findButtonInfo(7).component	= weakref.proxy( effectsGrid.effect8Button.box )
		self._findButtonInfo(7).label 		= weakref.proxy( effectsGrid.effect8Button.label )

		self._setButtonEnableStates()
		self._setupTooltips()


	def _onSelectQualityOption( self, idx ):
		self._setButtonEnableStates()
		self._updateSliders()


	def _setButtonEnableStates( self ):
		for i in xrange( 0, 8 ):
			info = self._findButtonInfo(i)
			buttonScript = info.component.script
			buttonScript.setDisabledState( not info.isSupported() )


	def _setupTooltips( self ):
		for i in xrange(0,8):
			button = self._findButtonInfo(i)
			toolTipInfo = ToolTipInfo( button.component, "tooltip1line", {'text':button.name, 'shortcut':''}  )
			button.component.script.setToolTipInfo( toolTipInfo )
			button.label.text = button.name


	def onActive( self ):
		self._updateSliders()


	@PyGUIEvent( "closeBox", "onClick" )
	def onCloseBoxClick( self ):
		self.active( False )
		
		
	def save(self, filename = "scripts/data/post_processing.xml" ):
		ds = ResMgr.openSection( filename, True )
		for (key,s) in PostProcessingWindow.sliders.items():
			#print key, s.getFn
			ds.writeFloat(key, s.prop.get())
		ds.save()


	def load(self, filename = "scripts/data/post_processing.xml", speed = 0.5 ):
		ds = ResMgr.openSection( filename, False )
		if ds is not None:
			for (key,s) in PostProcessingWindow.sliders.items():
				s.prop.set( ds.readFloat(key), speed )


	@PyGUIEvent( "effectsGrid.effect1Button.box", "onActivate", True, 0 )
	@PyGUIEvent( "effectsGrid.effect1Button.box", "onDeactivate", False, 0 )
	@PyGUIEvent( "effectsGrid.effect2Button.box", "onActivate", True, 1 )
	@PyGUIEvent( "effectsGrid.effect2Button.box", "onDeactivate", False, 1 )
	@PyGUIEvent( "effectsGrid.effect3Button.box", "onActivate", True, 2 )
	@PyGUIEvent( "effectsGrid.effect3Button.box", "onDeactivate", False, 2 )
	@PyGUIEvent( "effectsGrid.effect4Button.box", "onActivate", True, 3 )
	@PyGUIEvent( "effectsGrid.effect4Button.box", "onDeactivate", False, 3 )
	@PyGUIEvent( "effectsGrid.effect5Button.box", "onActivate", True, 4 )
	@PyGUIEvent( "effectsGrid.effect5Button.box", "onDeactivate", False, 4 )
	@PyGUIEvent( "effectsGrid.effect6Button.box", "onActivate", True, 5 )
	@PyGUIEvent( "effectsGrid.effect6Button.box", "onDeactivate", False, 5 )
	@PyGUIEvent( "effectsGrid.effect7Button.box", "onActivate", True, 6 )
	@PyGUIEvent( "effectsGrid.effect7Button.box", "onDeactivate", False, 6 )
	@PyGUIEvent( "effectsGrid.effect8Button.box", "onActivate", True, 7 )
	@PyGUIEvent( "effectsGrid.effect8Button.box", "onDeactivate", False, 7 )
	def onEffectButton( self, on, idx ):	
		# This will turn off file access warnings while we switch effects...
		currentWDE = BigWorld.worldDrawEnabled()
		BigWorld.worldDrawEnabled( False )
		
		if BigWorld.isKeyDown( Keys.KEY_LALT ):
			if not self.dg:
				self.dg = PostProcessing.debugGui()
			self.dg.visible = not self.dg.visible
		elif BigWorld.isKeyDown( Keys.KEY_LCONTROL ):
			self.buttonSet( self.btnSet+1 )
		else:
			self._activatePage(idx)

		BigWorld.worldDrawEnabled( currentWDE )

	def _findButtonInfo( self, idx ):
		name = self.buttons[idx]
		for i in PostProcessingWindow.buttons:
			if name == i.name:
				return i
		raise IndexError( idx )
	
	
	def _activatePage( self, idx ):
		'''Activate the page given by the button at index idx.
		Sets up the sliders to correspond to the appropriate
		information.  Also, if the button has an associated
		preset, set that on the post-processing chain.'''
		buttonInfo = self._findButtonInfo(idx)

		if buttonInfo.preset == "default":
			PostProcessing.defaultChain()
		elif buttonInfo.preset:
			PostProcessing.RenderTargets.clearRenderTargets()
			PostProcessing.chain( PostProcessing.load(buttonInfo.preset) )

		self._fillSliderInfo(idx)
		self._updateSliders()


	def _fillSliderInfo( self, idx ):
		'''Fill the self.sliderInfo list with the 3 sliders appropriate
		to the button given by the index parameter.'''
		buttonInfo = self._findButtonInfo(idx)
		self.sliderInfo = []
		for i in xrange(0,3):
			sliderInfo = PostProcessingWindow.sliders[buttonInfo.sliderName[i]]
			self.sliderInfo.append( sliderInfo )


	def _updateSliders( self ):
		'''Update the slider area to represent the current state
		of the post-processing chain.'''
		c = self.component
		amounts = [c.slAmount1,c.slAmount2,c.slAmount3]
		labels = [c.slLabel1,c.slLabel2,c.slLabel3]
		sliders = [c.slider1,c.slider2,c.slider3]
		for i in xrange(0,3):
			self.sliderInfo[i].apply( sliders[i], labels[i], amounts[i] )


	@PyGUIEvent( "slider1", "onValueChanged", 0 )
	@PyGUIEvent( "slider2", "onValueChanged", 1 )
	@PyGUIEvent( "slider3", "onValueChanged", 2 )
	def onSlider( self, idx, value ):
		c = self.component
		amounts = [c.slAmount1,c.slAmount2,c.slAmount3]
		try:
			self.sliderInfo[idx].updateAmountLabel(amounts[idx])
			self.sliderInfo[idx].prop.set(value,0.01)
		except NameError:
			pass


	def active( self, show ):
		if self.isActive == show:
			return

		PyGUI.DraggableWindow.active( self, show )
		Cursor.showCursor( show )

		if show:
			self.onActive()


	def onBound( self ):
		PyGUI.DraggableWindow.onBound( self )
		self.buttonSet(0)
		self._setButtonEnableStates()
		self._fillSliderInfo(0)
		self._updateSliders()
		effectsGrid = self.component.effectsGrid
		effectsGrid.script.doLayout()
