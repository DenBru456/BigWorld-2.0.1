import os
import turbogears

from turbogears import expose
from turbogears import identity
from turbogears import redirect

from web_console.common import util

from pycommon import cluster
from pycommon import log
from pycommon import watcher_data_type as WDT

import collections as collections_module


@identity.require( identity.not_anonymous() )
@expose( template="watchers.templates.tree_processes" )
@util.unicodeToStr
def _getProcesses( user ):
	c = cluster.cache.get()

	user = util.getUser( c, user )
	# TODO: should this be user.getServerProcs?
	processes = user.getProcs()
	processes.sort( lambda x, y: cmp( x.label(), y.label() ) )

	return dict( user = user, processes = processes )


@identity.require( identity.not_anonymous() )
@expose( template="watchers.templates.tree" )
@util.unicodeToStr
def _getWatcherSubTree( machine, pid, path="", newval=None, dataType=None ):
	c = cluster.cache.get()
	m = c.getMachine( machine )
	p = m.getProc( int( pid ) )
	if not p:
		raise redirect( "/error", msg = "Process %s no longer exists" % pid )

	try:
		wd = p.getWatcherData( path )
	except TypeError, e:
		# It is possible that a type error will be thrown if the process
		# does not support querying the watcher tree.
		raise redirect( "/error", msg = str( e ) )

# TODO: this needs to be adjusted!
	if newval:
		log.info( "Setting a new value" )
		status = False
		if dataType != None:
			wdtClass = WDT.WDTRegistry.getClass( int(dataType) )
			wdtObj = wdtClass( newval )
			status = wd.set( wdtObj )
		else:
			status = wd.set( newval )

		wd = p.getWatcherData( os.path.dirname( wd.path ) )

	else:
		status = True

	children = wd.getChildren()
	subdirs = []
	watchersList = []
	if children:
		subdirs = [c for c in children if c.isDir()]
		watchersList = [c for c in children if not c.isDir()]
	collections = list( collections_module.getCollections() )

	watchers = []
	for w in watchersList:
		# Unfortunately this menu is created here because
		# the list of watchers is generated above
		# (this should be moved into controllers.py)
		menu = util.ActionMenuOptions()
		menu.addGroup( "Action..." )
		menu.addRedirect( "Edit", util.alterParams( path=w.path ),
						  help="Edit this watcher value" )
		menu.addGroup( "Add to Collection..." )
		for collection in collections:
			menu.addScript( "%s" % collection.pageName,
				args = ( collection.pageName, p.name, w.path ),
				group = "Add to Collection...",
				script = "addToCollection" )

		menu.addScript( "Create filtered view",
				args = (p.name, w.path),
				script = "createFilteredView" )

		watchers.append( (w, menu) )

	return dict( process = p, machine = m, status = status, watcherData = wd,
				 subDirs = subdirs, watchers = watchers )



class Tree( turbogears.controllers.Controller ):

	@expose()
	def index( self, user=None, machine=None, pid=None, path="", newval=None, dataType=None ):
		if not machine and not pid:
			return _getProcesses( user )

		else:
			return _getWatcherSubTree( machine, pid, path, newval, dataType )


# tree.py
