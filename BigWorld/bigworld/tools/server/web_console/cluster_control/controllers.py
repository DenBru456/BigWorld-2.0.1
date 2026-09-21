import logging
import cherrypy
import turbogears
import sqlobject

from turbogears import controllers, expose, redirect
from turbogears import validate, validators, identity
from turbogears import widgets
from turbojson import jsonify

# Standard python modules
from StringIO import StringIO
import os
import re
import random
import threading
import traceback
import signal as sigmodule

# BigWorld modules
import bwsetup; bwsetup.addPath( "../.." )
from pycommon import cluster
from pycommon import user as user_module
from pycommon import process as process_module
from pycommon import uid as uidmodule
from pycommon import log
from pycommon import async_task

import pycommon.util

from web_console.common import util
from web_console.common import module
from web_console.common import ajax
from web_console.common import model as common_model
import model

# For tradeshows always ignore layout errors
#showLayoutErrors = turbogears.config.get( "server.environment" ) == "development"
showLayoutErrors = True

class ClusterControl( module.Module ):

	def __init__( self, *args, **kw ):
		module.Module.__init__( self, *args, **kw )
		self.addPage( "Manage Servers", "procs" )
		self.addPage( "All Users", "users" )
		self.addPage( "All Machines", "machines" )
		self.addPage( "Saved Layouts", "layouts" )
		self.addPage( "Help", "help" )

	@identity.require( identity.not_anonymous() )
	@expose( template="common.templates.help" )
	def help( self ):
		return dict( PAGE_TITLE="BigWorld WebConsole: ClusterControl Help",
			   HELP_PAGE="static/html/help.html" )

	def appendToLayout( self, layout, tag ):
		for i in xrange( len( layout ) ):
			layout[i] = layout[i] + (tag,)


	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.procs" )
	def procs( self, user=None ):
		c = cluster.cache.get()
		user = util.getUser( c, user )

		areWorldProcessesRunning = True
		layoutErrors = None
		if user:
			procs = sorted( user.getProcs() )
			procsName = [p.name for p in procs]
			if "dbmgr" not in procsName or \
			   "loginapp" not in procsName or \
			   "cellappmgr" not in procsName or \
			   "baseappmgr" not in procsName:
				areWorldProcessesRunning = False

			if showLayoutErrors:
				layoutErrors = user.getLayoutErrors()
		else:
			raise redirect( "/error", msg = "Unable to resolve active user" )
			areWorldProcessesRunning = False

		isProduction = False
		if areWorldProcessesRunning:
			serverProcs = user.getServerProcs()
			# We just pick the first server proc to ask whether we are in
			# production.
			isProduction = serverProcs[0].isProduction() 

		return dict( procs = procs, user = user, layoutErrors = layoutErrors,
					 page_specific_js = ["/log/static/js/query.js"],
					 areWorldProcessesRunning = areWorldProcessesRunning,
					 isProduction = isProduction )


	@identity.require(identity.not_anonymous())
	@expose()
	def index( self ):
		raise redirect( turbogears.url( "procs" ) )

	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.machine" )
	def machine( self, machine ):
		c = cluster.cache.get()
		machine = c.getMachine( machine )
		procs = sorted( machine.getProcs() )
		procs.sort( key = lambda p: p.uid )
		return dict( m = machine, ps = procs )

	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.machines" )
	def machines( self, group = None ):
		c = cluster.cache.get()
		machines = c.getMachines()
		machines.sort()

		if group:
			c.queryTags( "Groups" )
			machines = [m for m in machines if m.tags.has_key( "Groups" )
						and group in m.tags[ "Groups" ]]

		return dict( ms = machines, group = group )

	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.users" )
	def users( self, user=None ):

		c = cluster.cache.get()
		activeUsers = sorted( c.getUsers() )
		inactiveUsers = {}
		for user in uidmodule.getall():
			inactiveUsers[ user.name ] = user
		for user in activeUsers:
			if inactiveUsers.has_key( user.name ):
				del inactiveUsers[ user.name ]
		inactiveUsers = sorted( inactiveUsers.values() )

		return dict( activeUsers = activeUsers,
					 inactiveUsers = inactiveUsers )


	# Perform the same functionality as the control_cluster 'flush' command.
	# This should only be called from the "All Users" page, and then return
	# the user to that page with an updated user list.
	@identity.require( identity.not_anonymous() )
	@expose()
	def usersFlush( self ):

		c = cluster.cache.get()
		ms = c.getMachines()

		for m in ms:
			m.flushMappings()

		raise redirect( "users" )


	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.start" )
	def start( self, user ):
		c = cluster.cache.get()
		try:
			user = c.getUser( user, refreshEnv = True, checkCoreDumps = True )
		except Exception, e:
			raise redirect( "/error", msg = str(e) )

		try:
			prefs = model.ccStartPrefs.select(
				model.ccStartPrefs.q.userID == util.getSessionUID() )[0]
		except:
			prefs = model.ccStartPrefs( user = util.getSessionUser(),
										mode = "single",
										arg = "",
										useTags = True )

		# It is possible that 'arg' will be saved to the DB as NULL when
		# starting a cluster by group name and selecting '(use all machines)'.
		# If this occurs we must force the arg to be an empty string so the
		# KID template doesn't fail.
		if prefs.arg == None:
			prefs.arg = ""

		savedLayouts = model.ccSavedLayouts.select(
			model.ccSavedLayouts.q.userID == util.getSessionUID() )

		return dict( user = user, c = c, prefs = prefs,
					 savedLayouts = [x.name for x in savedLayouts] )


	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.startproc" )
	@validate( validators = dict( count=validators.Int() ) )
	def startproc( self, user=None, pname=None, machine=None, count=None ):

		c = cluster.cache.get()
		user = util.getUser( c, user )

		# Ensure the count is correctly set for the singletons.
		# This is important because the field isn't passed through when
		# the input field is disabled.
		if pname in process_module.Process.SINGLETON_PROCS:
			count = 1

		# We're actually starting the processes
		if pname and machine and count:

			m = c.getMachine( machine )

			# Start the processes
			pname = pname.encode( "ascii" )
			user.startProc( m, pname, count )

			# Set this is as the default for next time
			for rec in model.ccStartProcPrefs.select(
				model.ccStartProcPrefs.q.userID == util.getSessionUID() ):
				rec.destroySelf()

			model.ccStartProcPrefs(
				user = util.getSessionUser(),
				proc = pname,
				machine = machine,
				count = count )

			raise redirect( "procs", user = user.name )

		# We're displaying the page to select what to start
		else:

			machines = sorted( c.getMachines(), key = lambda x: x.name )

			try:
				prefs = model.ccStartProcPrefs.select(
					model.ccStartProcPrefs.q.userID == util.getSessionUID() )[0]

			except IndexError:
				prefs = model.ccStartProcPrefs( user = util.getSessionUser() )

			# Generate a tuple of value and presentation information for the
			# selection list in the start procs page.
			machineList = []
			for m in machines:
				machineList.append( ( m.name,
					m.name + "  - (" + str( m.ncpus ) + " cpu)" ) )

			procList = [ (p, p) for p in process_module.Process.ALL_PROCS ]

			return dict( user = user, machines = machineList, prefs = prefs,
						proclist = procList )


	@identity.require(identity.not_anonymous())
	@expose()
	@validate( validators = dict( pid = validators.Int() ) )
	def stopproc( self, machine, pid ):

		c = cluster.cache.get()
		m = c.getMachine( machine )
		p = m.getProc( pid )
		u = p.user()

		if not identity.in_group( "admin" ) and \
		   util.getServerUsername() != u.name:
			return self.error( "You can't stop other people's processes" )

		p.stopNicely()

		raise redirect( "procs", user=u.name )



	@identity.require(identity.not_anonymous())
	@expose()
	@validate( validators = dict( pid = validators.Int(),
								  signal = validators.Int(),
								  restart = validators.StringBool() ) )
	def killproc( self, machine, pid, signal, restart = False ):

		c = cluster.cache.get()
		m = c.getMachine( machine )
		p = m.getProc( pid )
		u = p.user()

		if not identity.in_group( "admin" ) and \
		   util.getServerUsername() != u.name:
			return self.error( "You can't kill other people's processes" )

		if restart:
			u.startProc( m, p.name )

		m.killProc( p, signal )

		raise redirect( "procs", user=u.name )


	@identity.require(identity.not_anonymous())
	@expose()
	@validate( validators = dict( pid = validators.Int() ) )
	def retireApp( self, machine, pid ):
		c = cluster.cache.get()
		m = c.getMachine( machine )
		p = m.getProc( pid )
		u = p.user()

		if not identity.in_group( "admin" ) and \
				util.getServerUsername() != u.name:
			return self.error( "You can't retire other people's processes" )

		p.retireApp()

		raise redirect( 'procs', user=u.name )


	@identity.require(identity.not_anonymous())
	@expose()
	@util.unicodeToStr
	def doStart( self, user, mode, group=None, machine=None, layout=None,
				 restrict=False ):

		c = cluster.cache.get()
		user = c.getUser( user )
		kw = {}
		util.clearDebugOutput()

		# Saved layout mode
		if mode == "layout":
			rec = self.getLayout( layout )
			if not rec:
				return self.error( "Couldn't find saved layout '%s' "
								   "in the database" % layout )
			task = async_task.AsyncTask( 0, user.startFromXML,
										 StringIO( rec.xmldata ) )

		# Single and group modes
		else:
			if mode == "single":
				machines = [c.getMachine( machine )]
				kw[ "useSimpleLayout" ] = True
			else:
				machines = None

			if mode == "group":

				# If the selected group is all machines, force the group
				# to be None. This will replicate the behavior of
				# 'cluster_control.py start all'
				if group == "(use all machines)":
					group = None

				kw[ "group" ] = group
				if restrict:
					kw[ "tags" ] = True

			task = async_task.AsyncTask( 0, user.start, machines, **kw )

		# Delete old pref
		for rec in model.ccStartPrefs.select(
			model.ccStartPrefs.q.userID == util.getSessionUID() ):
			rec.destroySelf()

		# Insert new pref
		if mode == "single":
			model.ccStartPrefs( user = util.getSessionUser(),
								mode = "single",
								arg = machine,
								useTags = bool( restrict ) )
		elif mode == "group":
			model.ccStartPrefs( user = util.getSessionUser(),
								mode = "group",
								arg = group,
								useTags = bool( restrict ) )

		elif mode == "layout":
			model.ccStartPrefs( user = util.getSessionUser(),
								mode = "layout",
								arg = layout,
								useTags = False )

		# Block until we get the layout out of the async task
		try:
			layout = task.waitForState( "layout" )[1][:]
		except task.TerminateException:
			return self.error( "Couldn't get layout" )

		# Tag each process as "running"
		for i in xrange( len( layout ) ):
			layout[i] = layout[i] + ("running",)

 		return self.toggle( "start", task.id, layout, user )

	@identity.require(identity.not_anonymous())
	@expose()
	def restart( self, user ):
		c = cluster.cache.get()
		user = c.getUser( user )
		layout = user.getLayout()
		self.appendToLayout( layout, "registered" )
		task = async_task.AsyncTask( 0, user.restart )
		return self.toggle( "restart", task.id, layout, user )

	@identity.require(identity.not_anonymous())
	@expose()
	def stop( self, user ):
		c = cluster.cache.get()
		user = c.getUser( user )
		layout = user.getLayout()
		self.appendToLayout( layout, "registered" )
		task = async_task.AsyncTask( 0, user.smartStop )
		return self.toggle( "stop", task.id, layout, user )

	@identity.require(identity.not_anonymous())
	@expose()
	def kill( self, user ):
		"""
		Kill the server.  Data loss may occur if BaseApps are in the 
		process of writing entities to the database.
		"""
		c = cluster.cache.get()
		user = c.getUser( user )
		layout = user.getLayout()
		self.appendToLayout( layout, "registered" )
		task = async_task.AsyncTask( 0, user.smartStop, forceKill=True )
		return self.toggle( "stop", task.id, layout, user )

	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.toggle" )
	def toggle( self, action, id, layout, user ):

		# Figure out pnames set
		pnames = set()
		for _, pname, _, _ in layout:
			pnames.add( pname )
		pnames = list( pnames )
		pnames.sort( process_module.Process.cmpByName )

		return dict( action = action, layout = layout,
					 pnames = pnames, user = user, id = id )

	@identity.require(identity.not_anonymous())
	@ajax.expose
	def verifyEnv( self, user, type, value ):

		c = cluster.cache.get()
		util.clearDebugOutput()
		ms = []

		if type == "machine":
			ms.append( c.getMachine( value ) )

		elif type == "group":
			groups = c.getGroups()
			if value == "(use all machines)":
				ms = c.getMachines()
			elif groups.has_key( value ):
				ms = groups[ value ]
			else:
				raise ajax.Error( "Unknown group: %s" % value,
								  util.getDebugErrors() )

		elif type == "layout":
			layout = self.getLayout( value )
			mnames = [m for (m,p) in user_module.User.parseXMLLayout( layout.xmldata )]

			ms = []; missing = False
			for mname in mnames:
				ms.append( c.getMachine( mname ) )
				if not ms[-1]:
					log.error( "Layout refers to unknown machine %s", mname )
					missing = True

			if missing:
				raise ajax.Error( "Layout refers to unknown machines",
								  util.getDebugErrors() )

		user = c.getUser( user, random.choice( ms ), refreshEnv = True )

		if user.verifyEnvSync( ms ):
			return dict( mfroot = user.mfroot, bwrespath = user.bwrespath )

		else:
			raise ajax.Error(
				"Inconsistent environment settings across target machines",
				util.getDebugErrors() )


	@identity.require(identity.not_anonymous())
	@expose( template="cluster_control.templates.coredumps" )
	def coredumps( self, user = None ):

		if not user:
			user = util.getServerUsername()

		c = cluster.cache.get( user = user )
		user = c.getUser( user, checkCoreDumps = True )
		coredumps = sorted( user.coredumps, key = lambda x: x[2] )
		return dict( user = user, coredumps = coredumps )


	# --------------------------------------------------------------------------
	# Section: Saved XML layouts
	# --------------------------------------------------------------------------

	@util.unicodeToStr
	def getLayout( self, name ):
		recs = list( model.ccSavedLayouts.select( sqlobject.AND(
			model.ccSavedLayouts.q.userID == util.getSessionUID(),
			model.ccSavedLayouts.q.name == name ) ) )
		if len( recs ) == 1:
			return recs[0]
		elif len( recs ) == 0:
			return None
		else:
			log.critical( "Multiple saved layouts called '%s' exist for %s",
						  name, util.getSessionUsername() )

	@identity.require( identity.not_anonymous() )
	@ajax.expose
	def saveLayout( self, user, name ):

		c = cluster.cache.get()
		user = c.getUser( user )
		stream = StringIO()
		user.saveToXML( stream )

		# Delete any existing query with the same name
		old = self.getLayout( name )
		if old: old.destroySelf()

		model.ccSavedLayouts( user = util.getSessionUser(),
							  name = name,
							  serveruser = user.name,
							  xmldata = stream.getvalue() )

		return "Server layout saved successfully"

	@identity.require( identity.not_anonymous() )
	@expose()
	def deleteLayout( self, name ):
		rec = self.getLayout( name )
		if not rec:
			return self.error( "Can't delete non-existant layout '%s'" % name )
		else:
			rec.destroySelf()
			raise redirect( "layouts" )

	@identity.require(identity.not_anonymous())
	@expose( template="web_console.cluster_control.templates.layouts" )
	def layouts( self ):
		recs = model.ccSavedLayouts.select(
			model.ccSavedLayouts.q.userID == util.getSessionUID() )

		# Convert each XML layout into a mapping of process counts
		layouts = []
		pnames = set()
		for rec in recs:
			counts = {}
			layout = user_module.User.parseXMLLayout( rec.xmldata )
			for mname, pname in layout:
				pnames.add( pname )
				if counts.has_key( pname ):
					counts[ pname ] += 1
				else:
					counts[ pname ] = 1
			layouts.append( counts )

		# Not all layouts have the same types of server processes.
		# If a particular process type (e.g. bots) is missing, set
		# count for that process type to 0.
		for counts in layouts:
			for pname in pnames.difference( counts.keys() ):
				counts[ pname ] = 0

		# Sort pnames by pre-arranged ordering here
		pnames = list( pnames )
		pnames.sort( process_module.Process.cmpByName )

		return dict( recs = recs, layouts = layouts, pnames = pnames )


	@identity.require(identity.not_anonymous())
	@expose( template="web_console.common.templates.error" )
	def error( self, msg ):
		debugmsgs = util.getDebugErrors()
		return dict( msg = msg, debug = debugmsgs )

# controllers.py
