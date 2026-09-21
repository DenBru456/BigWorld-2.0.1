# -*- coding: utf-8 -*-

from Helpers.PyGUI import DraggableWindow
from Helpers.PyGUI import InternalBrowser
from Helpers.PyGUI import PyGUIEvent
from functools import partial
from JavaScriptBridge import JavaScriptBridge
import BigWorld
import random
import FantasyDemo

class HTMLWindow( DraggableWindow, JavaScriptBridge ):

	DEFAULT_RATE_PER_SECOND=1./3.
	MEDIUM_RATE_PER_SECOND=2
	HIGH_RATE_PER_SECOND=8
	def __init__( self, component, uri, highRateTime=0.5 ):
		DraggableWindow.__init__( self, component )
		self.component.script = self
		self.uri = uri
		self.alreadyInit = False
		self.ratePerSecondCallbackHandle = None
		self.highRateTime = highRateTime
		#get a callback upon resolution override change
		FantasyDemo.rds.fdgui.addResolutionOverrideHandler( self )
		self.fullyInitialised = True
		
	def init( self ):
		if not self.alreadyInit:
			self.addObserver()
		self.reload()
		self.alreadyInit = True
		#set default to normal
		self._temporarySetRatePerSecond(HTMLWindow.DEFAULT_RATE_PER_SECOND, 0)
		#set to high for a second just to make sure we are updated
		self._temporarySetRatePerSecond(HTMLWindow.MEDIUM_RATE_PER_SECOND, 4)

	def reload( self ):
		self._getInternalBrowserScript().navigate( self.uri )

	@PyGUIEvent( "closeBox", "onClick" )
	def onCloseBoxClick( self ):
		self.active( False )

	def _getInternalBrowserScript(self):
		return self._getInternalBrowser().script

	def _getInternalBrowser(self):
		return self.component.internalBrowser

	def _temporarySetRatePerSecond( self, ratePerSecond, timeToChangeBack):
		"""
		Temporary set the rate per second 
		@param ratePerSecond the new ratePerSecond to be used
		@param timeToChangeBack when to change the value back to the default value, 0 means never
		"""
		# First cancel the callback if exists
		hadCallback=False
		if self.ratePerSecondCallbackHandle:
			BigWorld.cancelCallback( self.ratePerSecondCallbackHandle )
			self.ratePerSecondCallbackHandle = None
			hadCallback = True
		# Schedule a callback to change the rate per second back
		# if we are already on fast rate without a callback no need for a callback here as we want to keep high rate
		# using DEFAULT_RATE_PER_SECOND + 0.1 (for precision accuracy)
		if timeToChangeBack > 0 and (self._getRatePerSecond() <= HTMLWindow.DEFAULT_RATE_PER_SECOND + 0.1 or hadCallback):
			self.ratePerSecondCallbackHandle = BigWorld.callback(timeToChangeBack, partial(self._callbackSetRatePerSecond, self.DEFAULT_RATE_PER_SECOND))
		self._setRatePerSecond(ratePerSecond)

	
	def _callbackSetRatePerSecond(self, rate):
		self.ratePerSecondCallbackHandle = None
		self._setRatePerSecond ( rate )
		
	def _setRatePerSecond(self, rate):
		self._getInternalBrowserScript().setRatePerSecond(rate)

	def _getRatePerSecond(self):
		return self._getInternalBrowserScript().getRatePerSecond()
		
	def onClick( self, uri ):
		self._getInternalBrowserScript().navigate( event.uri )

	def addObserver(self):
		self._getInternalBrowserScript().addObserver( self )
		self._getInternalBrowserScript().addFocusObserver( self )

	# Called by child who takes the focus
	# so we can inform other child of losing key focus
	def focus( self, state ):
		if hasattr( self, "fullyInitialised" ):
			if state:
				self._temporarySetRatePerSecond( HTMLWindow.HIGH_RATE_PER_SECOND, 0 )
			else:
				self._temporarySetRatePerSecond( HTMLWindow.DEFAULT_RATE_PER_SECOND, 0 )

	def updateResolutionOverride(self):
		self._temporarySetRatePerSecond( HTMLWindow.HIGH_RATE_PER_SECOND, 4 )

	def invokeCallback( self ):
		# if we are on a lower rate or have a callback (meaning we are probably not in focus) set the medium rate
		if (self._getRatePerSecond() < HTMLWindow.MEDIUM_RATE_PER_SECOND or self.ratePerSecondCallbackHandle):
			#This method will be called when callbacks invoked from Javascript or when we call javascript
			self._temporarySetRatePerSecond ( HTMLWindow.MEDIUM_RATE_PER_SECOND , self.highRateTime)
		
# HTMLWindow.py
