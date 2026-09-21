# -*- coding: utf-8 -*-

import BigWorld
import Math
import types
import GUI
from PyGUIBase import PyGUIBase
from VisualStateComponent import VisualState, VisualStateComponent
import Utils
import Keys
import LLMozlibKeys
import FantasyDemo

from FocusManager import setFocusedComponent, isFocusedComponent

class InternalBrowser( PyGUIBase ):
	factoryString = "PyGUI.InternalBrowser"
	visualStateString="PyGUI.ButtonVisualState"

	def __init__( self, component = None):
		PyGUIBase.__init__( self, component )
		self.component.script = self
		# Flag to mark whether we dynamically focus the browser or not.
		self.mozillaHandlesKeyboard = True
		self.prevCursorManagement = True
		self.focusObserver = None
		
	def onLoad( self, dataSection ):
		self.exactWidth = dataSection.readInt( "exactWidth", 0 )
		self.exactHeight = dataSection.readInt( "exactHeight", 0 )

		if self.exactHeight == 0 and self.exactWidth == 0:
			resQuality="EFFECT_SCROLLING"
		else:
			resQuality = "EFFECT_QUALITY"
			
		componentWidth, componentHeight  = Utils.pixelSize(self.component)
		self.webPage = BigWorld.WebPageProvider(componentWidth, componentHeight, True, False, u"http://www.google.com", resQuality)
		self.updateResolutionOverride()
		#get a callback upon resolution override change
		FantasyDemo.rds.fdgui.addResolutionOverrideHandler( self )

		self.component.focus = False
		self.component.mouseButtonFocus = True
		self.component.moveFocus = True
		self.component.crossFocus = True
		self.component.texture = self.webPage.texture
		self.component.materialFX = "SOLID"
		

	# get the mouse web coordinates
	def _getWebCoordinates( self, cursorPosition ):
		c = self.component
		pos = c.screenToLocal( cursorPosition )
		if pos.x > c.width or pos.y > c.height or pos.x < 0 or pos.y < 0:
			return None
		# Note if the texture was scaled the coordinates should be scaled 
		# (downscaled) accordingly especially as the componentWidth does not take
		# into account the resolution override
		componentWidth, componentHeight  = Utils.pixelSize(self.component)
		pos.x = pos.x * self.webPage.width / componentWidth
		pos.y = pos.y * self.webPage.height / componentHeight
		return pos


	def handleMouseButtonEvent( self, comp, event ):
		PyGUIBase.handleMouseButtonEvent( self, comp, event )
		pos = self._getWebCoordinates( event.cursorPosition )
		if pos is None:
			# Mouse was outside the view
			return False
		if event.isKeyDown():
			setFocusedComponent( self.component )
		self.webPage.handleMouseButtonEvent (pos, event.isKeyDown())	
		return True


	def handleMouseEvent( self, comp, event ):
		#we do the dz (wheel scroll in any case if required)
		#each mouseMove is 120 (and usually scrolls 3 lines)
		#we devide by -40 as scroll 1 scrolls one line down but we get -120
		if event.dz != 0:
			self.webPage.scrollByLines( event.dz / -40 )
		pos = self._getWebCoordinates( event.cursorPosition )
		if pos is None:
			# Mouse was outside the view
			return False
		self.webPage.handleMouseMove(pos)	
		return True


	def handleMouseEnterEvent( self, comp ):
		#Web handles cursor
		self.prevCursorManagement = GUI.mcursor().automaticCursorManagement
		GUI.mcursor().automaticCursorManagement = False
		self.webPage.allowCursorInteraction(True)
		return True
	
	def handleMouseLeaveEvent( self, comp ):
		self.webPage.allowCursorInteraction(False)
		#BW handles cursor
		GUI.mcursor().automaticCursorManagement = self.prevCursorManagement
		return True

	def handleKeyEvent( self, event ):
		if event.isMouseButton():
			return False
		if not isFocusedComponent( self.component ) and not self.mozillaHandlesKeyboard:
			return False
		character = event.character

		if ( event.isKeyDown() ):	
			callKeyboardEvent=False
			callUnicodeEvent=False
			if ( event.key == Keys.KEY_ESCAPE ) :
				usedKey = LLMozlibKeys.LL_DOM_VK_ESCAPE
				callKeyboardEvent=True
			elif ( event.key == Keys.KEY_BACKSPACE ):
				usedKey = LLMozlibKeys.LL_DOM_VK_BACK_SPACE
				callKeyboardEvent=True
			elif ( event.key == Keys.KEY_RETURN ):
				usedKey = LLMozlibKeys.LL_DOM_VK_RETURN
				callKeyboardEvent=True
			elif ( event.key == Keys.KEY_TAB ) :
				usedKey = LLMozlibKeys.LL_DOM_VK_TAB
				callKeyboardEvent=True
			elif ( character is not None ):
				callUnicodeEvent=True
			
			#Now send the key to the correct function.
			if not self.mozillaHandlesKeyboard:
				if callUnicodeEvent:
					self.webPage.handleUnicodeInput(character)
					return 1
				elif callKeyboardEvent:
					self.webPage.handleKeyboardEvent(usedKey)
					return 1
			else:
				return True
		#even if the key was not consumed we still don't want it sent to other components
		return True

	def addFocusObserver(self, focusObserver):
		self.focusObserver = focusObserver

	def focus( self, state ):
		if self.mozillaHandlesKeyboard:
			self.webPage.focusBrowser(state, state)
		if self.focusObserver:
			self.focusObserver.focus( state )
			
	def setRatePerSecond(self, rate):
		self.webPage.ratePerSecond = rate

	def getRatePerSecond(self):
		return self.webPage.ratePerSecond

	def navigate(self, url):
		self.webPage.navigate(url)

	def navigateBack(self):
		self.webPage.navigateBack()

	def navigateForward(self):
		self.webPage.navigateForward()

	def addObserver(self, observer):
		self.webPage.listener = observer

	def updateResolutionOverride(self):
		#adjust the web page based on the new sizes as we want to have the 
		#texture size meeting the exact width and height of the page (which changes due to the resolution override)
		#to prevent the resolution override stuff from blurring our page.
		webPageWidth, webPageHeight  = Utils.pixelSize(self.component)
		screenWidth = BigWorld.screenWidth()
		screenHeight = BigWorld.screenHeight()
		usedResolutionOverride = GUI.screenResolution()
		if usedResolutionOverride != (0,0) :
			webPageWidth *= BigWorld.screenWidth() / usedResolutionOverride[0] 
			webPageHeight *= BigWorld.screenHeight() / usedResolutionOverride[1]
		self.webPage.setSize(webPageWidth, webPageHeight, self.exactWidth, self.exactHeight);
