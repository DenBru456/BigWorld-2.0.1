import BigWorld
import Keys
from Helpers import PyGUI
from functools import partial
from Helpers.BWCoroutine import *

from GameData.MainMenuGUIData import *

import FDGUI.Cursor

import weakref

def _readItemText(i):
	return str(i()) if callable(i) else str(i)
	
	
def _fixAspectRatio( c, graphicAspectRatio ):
	screenWidth, screenHeight = BigWorld.screenSize()
	screenAspectRatio = screenWidth / screenHeight	
	c.width = (graphicAspectRatio/screenAspectRatio) * 2.0
	c.height = 2.0

	

class MainMenuScrollButton(PyGUI.PyGUIBase):

	factoryString="MainMenuGUI.MainMenuScrollButton"

	def __init__( self, component = None ):
		PyGUI.PyGUIBase.__init__( self, component )
		component.focus = True
		component.mouseButtonFocus = True
		component.crossFocus = True
		self.timerHandle = None
		self.mouseDown = False
		self.mouseOver = False
		self.scrollCount = 0


	def handleMouseButtonEvent( self, comp, event ):
		PyGUI.PyGUIBase.handleMouseButtonEvent( self, comp, event )
		if event.key != Keys.KEY_LEFTMOUSE:
			return False

		self.scrollCount = 0

		if event.isKeyDown():
			self._setupTimer()
			self._scrollNow()
		else:
			self._cancelTimer()

		self.mouseDown = event.isKeyDown()
		self.mouseOver = True
		return True


	def handleMouseEnterEvent( self, comp ):
		self.mouseDown = BigWorld.isKeyDown( Keys.KEY_LEFTMOUSE )
		self.mouseOver = True

		if not self.mouseDown:
			self.scrollCount = 0

		self._setupTimer()
		return True


	def handleMouseLeaveEvent( self, comp ):
		self.mouseOver = False
		return True


	def onLoad( self, section ):
		self.dist = section.readInt( "moveDistance" )


	def _scrollNow( self ):
		scrollingList = self.component.parent.script.mainmenuComponent.script
		scrollingList.scrollList( self.dist )
		self.scrollCount += 1


	def _scrollCB( self ):
		self.timerHandle = None
		if not self.mouseDown or not self.mouseOver:
			return

		self._scrollNow()
		self.timerHandle = BigWorld.callback( SCROLL_RATE, self._scrollCB )


	def _setupTimer( self ):
		self._cancelTimer()
		delay = INITIAL_SCROLL_RATE if self.scrollCount == 0 else SCROLL_RATE
		self.timerHandle = BigWorld.callback( delay, self._scrollCB )


	def _cancelTimer( self ):
		if self.timerHandle is not None:
			BigWorld.cancelCallback( self.timerHandle )
		self.timerHandle = None



class MainMenu(PyGUI.PyGUIBase):

	factoryString="MainMenuGUI.MainMenu"	

	def __init__( self, component = None ):
		PyGUI.PyGUIBase.__init__( self, component )
		self.mainmenuComponent  = None
		self.component.focus = True
		self.backgroundAspectRatio = 0


	@BWMemberCoroutine
	def showCharacterScreen( self, active, fadeSpeed = 2.0 ):
		if active:
			self.component.background.fader.speed = fadeSpeed
			self.component.background.fader.value = 0.0
			self.mainmenuComponent.position = (-0.9, 0.0, 0.5)
			self.mainmenuComponent.width = 0.7
			self.component.scrollUp.position.x = -0.9
			self.component.scrollUp.width = 0.7
			self.component.scrollDown.position.x = -0.9
			self.component.scrollDown.width = 0.7
			self.doLayout( None )			
			
			BigWorld.worldDrawEnabled( True )

			if fadeSpeed > 0:
				yield BWWaitForPeriod( fadeSpeed )

		else:
			self.component.background.fader.speed = fadeSpeed
			self.component.background.fader.value = 1.0
			self.mainmenuComponent.position = (-0.6, 0.0, 0.5)
			self.mainmenuComponent.width = 1.2
			self.component.scrollUp.position.x = -0.6
			self.component.scrollUp.width = 1.2
			self.component.scrollDown.position.x = -0.6
			self.component.scrollDown.width = 1.2
			self.doLayout( None )

			if fadeSpeed > 0:
				yield BWWaitForPeriod( fadeSpeed )

			BigWorld.worldDrawEnabled( False )


	def onLoad( self, section ):
		self.backgroundAspectRatio = section.readFloat( "backgroundAspectRatio", 0 )

	def onBound( self ):
		PyGUI.PyGUIBase.onBound( self )
		self.mainmenuComponent = weakref.proxy( self.component.mainmenu )
		
		self.component.scrollDown.focus = True
		self.component.scrollDown.mouseButtonFocus = True
		self.component.scrollDown.crossFocus = True
		self.component.scrollUp.focus = True
		self.component.scrollUp.mouseButtonFocus = True
		self.component.scrollUp.crossFocus = True
		
	def active( self, state ):
		PyGUI.PyGUIBase.active( self, state )
		FDGUI.Cursor.showCursor( state )
		
	def handleMouseEvent( self, comp, event ):
		self.mainmenuComponent.script.scrollList( -event.dz / 120 )
		return False
		
	def doLayout( self, parent ):
		if self.backgroundAspectRatio == 0:
			t1 = self.component.background.texture
			t2 = self.component.mainBackground.texture
			aspectRatio1 = t1.width / t1.height
			aspectRatio2 = t2.width / t2.height
		else:
			aspectRatio1 = self.backgroundAspectRatio
			aspectRatio2 = self.backgroundAspectRatio

		_fixAspectRatio( self.component.background, aspectRatio1 )
		_fixAspectRatio( self.component.mainBackground, aspectRatio2 )
		PyGUI.PyGUIBase.doLayout( self, parent )


class SmoothMover( PyGUI.SmoothMover ):

	factoryString = "MainMenuGUI.SmoothMover"

	def __init__( self, component ):
		PyGUI.SmoothMover.__init__( self, component )

	def doLayout( self, parent ):
		self.component.width = parent.component.width
		PyGUI.SmoothMover.doLayout( self, parent )


# -------------------------------------------------------------------------
# This class implements an individual item in the a scrolling list page.
# Each item is initialised with a text label and a functor
# -------------------------------------------------------------------------
class MenuItem( PyGUI.PyGUIBase ):

	factoryString="MainMenuGUI.MenuItem"

	def __init__( self, component ):
		PyGUI.PyGUIBase.__init__( self, component )
		self.event = None
		component.focus = True
		component.mouseButtonFocus = True
		component.crossFocus = True
		component.moveFocus = True
		
		self.selected = False
		self.mouseOver = False
		
	#when the list item is created, what to do.
	def setup( self, setupParams, listIdx ):
		self.component.name.text = _readItemText( setupParams[0] )
		self.event = setupParams[1]		
		if len(setupParams) > 2:
			self.component.status.text = _readItemText( setupParams[2] )
		else:
			self.component.status.text = ""			
		self.listIdx = listIdx

	def canSelect( self ):
		return not (self.event == None)

	def adjustFont( self, width ):
		if width < 700:
			self.component.name.font = self.smallFont
			self.component.status.font = self.smallFont
		else:
			self.component.name.font = self.bigFont
			self.component.status.font = self.bigFont
			
		self.component.name.reset()
		self.component.status.reset()
		
		heightMode = self.component.heightMode
		self.component.heightMode = "LEGACY"	
		self.component.height = self.component.name.height * 1.1
		self.component.heightMode = heightMode
		return self.component.height

	#arggh generic item colouring
	def setupHighlights( self ):
		if not self.event:
			self.component.colour = ITEM_COLOUR_BG_UNSELECTABLE
			self.component.name.colour = ITEM_COLOUR_TEXT_UNSELECTABLE
		elif self.selected:
			self.component.colour = ITEM_COLOUR_BG_SELECTED
			self.component.name.colour = ITEM_COLOUR_TEXT_SELECTED
		else:
			self.component.colour = ITEM_COLOUR_BG_UNSELECTED
			self.component.name.colour = ITEM_COLOUR_TEXT_UNSELECTED


	def select( self, state ):
		self.selected = state
		self.setupHighlights()


	def doLayout( self, parent ):
		self.component.width = parent.component.width
		self.component.name.width = parent.component.width
		self.component.name.position.x = -parent.component.width / 2 + 0.05

		PyGUI.PyGUIBase.doLayout( self, parent )

	#i.e. the button was pressed. make event happen
	def onSelect( self, mainGui ):
		if self.event:
			mainGui.active(0)
			self.event()
			
	def selectSelf( self, bringIntoView = True ):
		scrollingList = self.component.parent.parent.script
		if scrollingList.canSelect( self.listIdx ):
			scrollingList.selectItem( self.listIdx, bringIntoView )

	def onLoad( self, section ):
		self.smallFont = section.readString( "smallFont", "default_small.font" )
		self.bigFont = section.readString( "bigFont", "default_medium.font" )


	def handleMouseClickEvent( self, comp ):
		scrollingList = self.component.parent.parent.script
		if scrollingList.canSelect( self.listIdx ):
			scrollingList.selectItem( self.listIdx )
			scrollingList.executeSelected()
			
		return True

	def handleMouseEnterEvent( self, comp ):
		self.mouseOver = True
		return True


	def handleMouseLeaveEvent( self, comp ):
		self.mouseOver = False
		return True


	def handleMouseEvent( self, comp, event ):
		PyGUI.PyGUIBase.handleMouseEvent( self, comp, event )
		if event.dx != 0 or event.dy != 0: # Don't select if its only mouse wheel
			self.selectSelf( False )
		return False

	def handleMouseButtonEvent( self, comp, event ):
		PyGUI.PyGUIBase.handleMouseButtonEvent( self, comp, event )
		if event.key == Keys.KEY_LEFTMOUSE and event.isKeyDown():
			self.selectSelf()
			return True	
	
		return False

