#!/usr/bin/env python

import watcher_constants as Constants

class Forwarding( object ):

	forwardPaths = {}
	forwardPaths[ Constants.EXPOSE_WITH_ENTITY ]  = "forwardTo/withEntity"
	forwardPaths[ Constants.EXPOSE_ALL ]          = "forwardTo/all"
	forwardPaths[ Constants.EXPOSE_WITH_SPACE ]   = "forwardTo/withSpace"
	forwardPaths[ Constants.EXPOSE_LEAST_LOADED ] = "forwardTo/leastLoaded"


	def __init__( self ):
		pass

	@staticmethod
	def runTypeHintToWatcherPath( runType ):
		try:
			return Forwarding.forwardPaths[ int(runType) ]
		except:
			raise TypeError( "Unable to map '%s' to a known forwarding path." \
							% str(runType) )

# watcher.py
