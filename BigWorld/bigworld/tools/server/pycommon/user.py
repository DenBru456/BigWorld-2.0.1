import log
import messages
import random
import re
import operator
import socketplus
import sys
import types
import util
from exposed import Exposed
from xml.dom import minidom

from StringIO import StringIO

from cluster_constants import CELL_ENTITY_ADJ
from cluster_constants import MAX_SERVER_CPU
from cluster_constants import POLL_SLEEP
from cluster_constants import MAX_POLL_SLEEPS
from cluster_constants import MAX_STARTUP_SLEEPS
from cluster_constants import RECV_BUF_SIZE

from cluster_constants import NBOTS_AT_ONCE
from cluster_constants import MAX_BOTS_CPU
from cluster_constants import CPU_WAIT_SLEEP


# ------------------------------------------------------------------------------
# Section: LoadStats
# ------------------------------------------------------------------------------

class LoadStats( object ):
	def __init__( self, min, avg, max ):
		self.min = min
		self.avg = avg
		self.max = max

	def __str__( self ):
		return "%.2f %.2f %.2f" % (self.min, self.avg, self.max )


# The exception that gets thrown when a user can't be found
class UserError( Exception ):
	def __init__( self, *args, **kw ):
		Exception.__init__( self, *args, **kw )


# ------------------------------------------------------------------------------
# Section: User
# ------------------------------------------------------------------------------

class User( Exposed ):
	"""
	Info about a user, and methods to query info about the server a user is
	running.

	The 'uid' param passed here can either be the username or the UID or an MGM
	that already has all the details in it.
	"""

	def __init__( self, uid, cluster, machine = None,
				  checkCoreDumps = False, refreshEnv = False ):

		Exposed.__init__( self )
		self.cluster = cluster

		# Request the user info from the server if not already given
		if not isinstance( uid, messages.UserMessage ):

			query = mgm = messages.UserMessage()

			if type( uid ) == int:
				mgm.param = mgm.PARAM_USE_UID
				mgm.uid = uid
			elif isinstance( uid, types.StringTypes ):
				mgm.param = mgm.PARAM_USE_NAME
				mgm.username = uid.encode( "utf-8" )
			else:
				log.critical( "First param to User() must be an " +
							  "int, string or UserMessage, not %s" %
							  uid.__class__.__name__ )

			if checkCoreDumps:
				mgm.param |= mgm.PARAM_CHECK_COREDUMPS

			if refreshEnv:
				mgm.param |= mgm.PARAM_REFRESH_ENV

			# A list of machines that aren't reply to UserMessages
			blacklist = set()

			# Macro to select a machine to do the uid resolution
			def pickMachine():
				candidates = [m for m in cluster.getMachines() \
							  if uid not in m.unknownUsers and \
							  m not in blacklist]
				if candidates:
					return random.choice( candidates )
				else:
					raise UserError, "No machines on network able " \
						  "to resolve user %s" % uid

			# The machine we request the user info from
			if not machine:
				machine = pickMachine()

			while True:
				replies = mgm.query( machine )

				if not replies:
					log.error( "%s:%s didn't reply to UserMessage, blacklisting",
							   machine.name, machine.ip)
					blacklist.add( machine )

				elif replies[0].uid == mgm.UID_NOT_FOUND:
					log.verbose( "%s:%s couldn't resolve user %s, "
								 "will not ask again",
								 machine.name, machine.ip, uid )
					machine.unknownUsers.add( uid )

				else:
					mgm = replies[0]
					break

				machine = pickMachine()
		else:
			query = mgm = uid

		self.uid = mgm.uid
		self.name = mgm.username
		self.fullname = mgm.fullname
		self.home = mgm.home
		self.mfroot = mgm.mfroot
		self.bwrespath = mgm.bwrespath
		self.coredumps = mgm.coredumps

		# Can be a hash of the min/avg/max loads for various server components
		self.load = None

		# Some counters only used when doing bots stuff
		self.totalBots = self.numProxies = self.numEntities = None


	def __str__( self ):
		return "%s (%d)" % (self.name, self.uid)

	def __cmp__( self, other ):
		if not isinstance( other, User ):
			return -1
		return cmp( self.name, other.name )

	def __hash__( self ):
		return hash( self.uid ) ^ hash( self.name )

	def getLoad( self, name ):
		loads = self.getLoads()
		if loads.has_key( name ):
			return loads[ name ]
		else:
			return 0

	def getLoads( self ):

		if not self.load:
			self._getLoads()
		return self.load

	def getNumEntities( self ):

		if self.numEntities != None:
			return self.numEntities

		elif self.serverIsRunning():
			self.numEntities = int( self.getProc( "cellappmgr" ).
									getWatcherValue( "numEntities", 0 ) ) + \
									CELL_ENTITY_ADJ
			return self.numEntities
		else:
			return None

	def getNumProxies( self ):

		if self.numProxies != None:
			return self.numProxies

		elif self.serverIsRunning():
			self.numProxies = int( self.getProc( "baseappmgr" ).
								   getWatcherValue( "numProxies", 0 ) )
			return self.numProxies
		else:
			return None

	def getTotalBots( self ):

		if self.totalBots is None:
			self.totalBots = sum( map( lambda bp: bp.nbots(),
									   self.getProcs( "bots" ) ) )

		return self.totalBots

	def _getLoads( self ):

		# Argmin/max over reported machine CPU loads
		def botsLoad( f ):
			return f( [ p.load for p in self.getProcs( "bots" ) ] ) 

		# Macro for querying load watcher values
		def watcherload( cb, am ):
			return max(
				float( self.getProc( "%sappmgr" % cb ).\
					   getWatcherValue( "%sAppLoad/%s" % (cb, am), 0 ) ), 0.0 )

		# Mapping from name to LoadStats object for all those processes
		self.load = {}

		# Total up all known bots and calculate bot CPU usage
		if self.getProcs( "bots" ):
			def avg( x ):
				return sum( x ) / float( len( x ) )

			self.load[ "bots" ] = LoadStats( botsLoad( min ),
											 botsLoad( avg ),
											 botsLoad( max ) )

		# Some important stats
		if self.serverIsRunning():
			for name in [ "cell", "base" ]:
				self.load[ name + "app" ] = LoadStats(
					watcherload( name, "min" ),
					watcherload( name, "average" ),
					watcherload( name, "max" ) )

	# ------------------------------------------------------------------------
	# Subsection: Query methods
	# ------------------------------------------------------------------------

	# Convenience functions
	def getProc( self, name ):
		return self.cluster.getProc( name, self.uid )

	def getProcs( self, name=None ):
		return self.cluster.getProcs( name, self.uid )

	def getServerProcs( self ):
		return [p for p in self.getProcs() if p.name in Process.SERVER_PROCS]

	# Return a this user's process that matches the given name exactly
	def getProcExact( self, name ):

		for p in self.getProcs():
			if p.label() == name:
				return p
		return None

	def serverIsRunning( self ):
		"""Returns true if this user appears to be running a proper bigworld
		   server."""
		for sp in Process.SERVER_PROCS:
			if not self.getProcs( sp ):
				return False
		return True

	def serverIsOverloaded( self ):
		"""Returns true if any machine running server components for this user
		is overloaded."""

		return self.getLoad( "cellapp" ).max > MAX_SERVER_CPU or \
			   self.getLoad( "baseapp" ).max > MAX_SERVER_CPU

	def getLayout( self ):
		layout = []
		for p in self.getServerProcs():
			layout.append( (p.machine.name, p.name, p.pid) )
		return layout

	def getLayoutStatus( self, layout, _async_ = None ):
		"""
		Takes a list of (mname, pname, pid) and returns a list of
		(mname, pname, pid, status).
		"""

		status = []
		notregistered = []

		shouldExtendTime = False

		# Check for registered processes first
		for mname, pname, pid in layout:
			m = self.cluster.getMachine( mname )
			if not m:
				status.append( (mname, pname, pid, "nomachine", "") )
				continue
			p = m.getProc( pid )
			if p:
				statusMsg = ""

				if _async_:
					# Avoid doing watcher query if not async
					procStatus = p.status()
					if p.name == "dbmgr":
						# Process status of 6 == consolidating
						if procStatus != None and procStatus == 6:
							statusMsg = "Consolidating"
							shouldExtendTime = True

				status.append( (mname, pname, pid, "registered", statusMsg) )
			else:
				notregistered.append( (mname, pname, pid) )

		# Check unregistered processes to see if they are actually running
		for mname, pname, pid in notregistered:

			m = self.cluster.getMachine( mname )
			pm = messages.PidMessage()
			pm.pid = pid
			replies = pm.query( m )

			if not replies:
				log.error( "No reply to PidMessage from %s", mname )
				status.append( (mname, pname, pid, "nomachine", "") )
			elif replies[0].running:
				status.append( (mname, pname, pid, "running", "") )
			else:
				status.append( (mname, pname, pid, "dead", "") )

		# Figure out return counts
		dead = running = registered = 0

		for mname, pname, pid, state, details in status:
			if state == "dead": dead += 1
			if state == "running": running += 1
			if state == "registered": registered += 1

		# Notify async handlers
		if _async_:
			# If the DBMgr is consolidating the secondary DB's then extend the async
			# process life
			if shouldExtendTime:
				_async_.extendTimeout( 1 )
			_async_.update( "status", dict( layout = status ) )

		return (dead, running, registered, status)


	def getLayoutErrors( self ):
		"""Return a list of strings containing error messages (if any) for the
		User's server layout.""" 

		# List of machines with bots running on them
		botMachines = {}
		errors = []
		machineInfo = {}

		dbMachine = None
		for proc in self.getProcs():

			if proc.requiresOwnCPU():
				uniqueProcs = machineInfo.get( proc.machine, 0 )
				uniqueProcs = uniqueProcs + 1
				machineInfo[ proc.machine ] = uniqueProcs

			if proc.name == "dbmgr":
				dbMachine = proc.machine
				# DBMgr should really be on a machine by itself
				if len( dbMachine.procs ) > 1:
					errors.append( "DBMgr is running on a machine with other "
						"server processes." )

			elif proc.name == "bots":
				# if bots - add to machine array
				botMachines[ proc.machine.name ] = True

		# Now check if there are too many processes for each core
		for machine, uniqueCount in machineInfo.iteritems():
			if machine.ncpus < uniqueCount:
				errors.append( "Machine %s appears to be running too many processes "
					"for the number of available CPUs/cores." % machine.name )


		# If there are any bots running, check that the processes aren't running
		# on server machines with other processes such as dbmgr/cellapp/baseapp 
		errorBotMachines = []
		for botMachineName in botMachines.keys():
			for uniqueMachine in machineInfo.keys():
				if uniqueMachine.name == botMachineName:
					errorBotMachines.append( botMachineName )

		if len( errorBotMachines ) > 0:
			errors.append( "bots running on the following machines should "
				"be moved to less critical server machines: %s" % \
				", ".join( errorBotMachines ) )

		return errors


	def layoutIsRunning( self, layout, status = [], _async_ = None ):

		dead, running, registered, status[:] = \
					   self.getLayoutStatus( layout, _async_ )

		if running == 0 and dead > 0:
			raise Cluster.TerminateEarlyException
		else:
			return registered == len( layout )


	def layoutIsStopped( self, layout, status = [], _async_ = None ):

		dead, running, registered, status[:] = \
					   self.getLayoutStatus( layout, _async_ )

		return dead == len( layout )


	# ------------------------------------------------------------------------
	# Subsection: Output methods
	# ------------------------------------------------------------------------

	def lsMiscProcesses( self ):
		"""
		Print out info for misc processes.  Returns a list of the processes
		displayed.
		"""

		miscps = [p for p in self.getProcs() if \
				  Process.clean( p.name ) in Process.SINGLETON_PROCS]

		if not miscps:
			log.info( "no misc processes found!" )
			return []
		miscps.sort( key = lambda x : x.label() )

		log.info( "misc processes:" )
		for p in miscps:
			log.info( "\t%s", p )

		return miscps


	def ls( self ):
		"""
		Prints detailed server info for a particular user.
		"""

		# Assemble a list of already-displayed processes
		displayed = self.lsMiscProcesses()

		# Quick macro to get all machines for a given component
		def displayMachinesForProcess( name, warn = True ):
			procs = self.getProcs( name )
			procs.sort( key = lambda x : x.label() )

			if procs:
				log.info( "%s (%d):" %
						  (Process.getPlural( name ), len( procs )) )
				for p in procs:
					log.info( "\t%s", p )

			elif warn:
				log.info( "no %s found!" % Process.getPlural( name ) )

			return procs

		# Display cellapps and baseapps
		displayed.extend( displayMachinesForProcess( "cellapp" ) )
		displayed.extend( displayMachinesForProcess( "baseapp" ) )

		# Display any processes not already done
		remaining = set( self.getProcs() ) - set( displayed )

		for pname in Process.ALL_PROCS:
			ps = [p for p in remaining if p.name == pname]
			if ps:
				displayMachinesForProcess( pname, False )

		# Display listing of used machines
		ms = util.uniq( [p.machine for p in self.getProcs()], cmp = cmp )
		ms.sort( key = lambda x : x.name )

		if ms:
			log.info( "\nmachines (%d):", len( ms ) )
			for m in ms:
				log.info( "\t%s", m )

	def lsSummary( self ):
		"""Prints summarised info about this user's server."""

		# Can't go any further without a complete server
		if not self.serverIsRunning():
			log.error( "Server isn't running, can't display summary" )
			return

		# Find world server
		self.lsMiscProcesses()

		# Macro that displays a summary for a type of process
		def displaySummaryForProcess( name, warn = True ):
			procs = self.getProcs( name )
			if procs:
				log.info( "%d %s at (%s)" % \
						  (len( procs ),
						   Process.getPlural( name, len( procs ) ),
						   self.getLoad( name )) )
			elif warn:
				log.info( "no %s found!" % Process.getPlural( name ) )

		displaySummaryForProcess( "cellapp" )
		displaySummaryForProcess( "baseapp" )
		displaySummaryForProcess( "bots", False )

	# --------------------------------------------------------------------------
	# Subsection: Cluster control methods
	# --------------------------------------------------------------------------

	def verifyEnvSync( self, machines = [], writeBack = False ):
		"""
		Checks this users BW env settings on each machines (or entire network if
		machines == []) and warns if settings are out of sync.

		If writeBack is True, the largest set of machines with in-sync config
		settings will be written back to the passed-in 'machines' list.
		"""

		um = messages.UserMessage()
		um.param = um.PARAM_USE_UID
		um.uid = self.uid

		variants = {}

		for um, (ip, port) in messages.MachineGuardMessage.batchQuery(
			[um], 1.0, machines )[um]:
			if um.mfroot or um.bwrespath:
				glob = um.mfroot + ";" + um.bwrespath
			else:
				glob = "<undefined>"
			if not variants.has_key( glob ):
				variants[ glob ] = set( [ip] )
			else:
				variants[ glob ].add( ip )

		if len( variants ) <= 1:
			return True

		else:

			if not writeBack:
				log.warning( "~/.bwmachined.conf differs on network:" )
				for glob, ips in variants.items():
					log.warning( "" )
					log.warning( "%s:" % glob )
					for ip in sorted( ips, util.cmpAddr ):
						m = self.cluster.getMachine( ip )
						if m:
							log.warning( m.name )
						else:
							log.error( "Unable to resolve hostname for %s", ip )

			else:
				while machines:
					machines.pop()
				biggest = sorted( variants.values(), key = len )[-1]
				machines.extend( map( self.cluster.getMachine, biggest ) )

			return False


	def start( self, machines = None, _async_ = None,
				bots = False, revivers = False, tags = False, group = None,
				useSimpleLayout = False ):
		"""
		Start a server for this user.  If machines is not passed, all machines
		are considered as candidates.

		If 'bots' is True, bots processes will be allocated and started.

		If 'revivers' is True, a reviver will be started on each machine that a
		process of another type is.

		If 'tags' is True, machines will be restricted to starting process types
		listed in their [Components] tag list.

		If 'group' is defined, then only machines in that machined group will be
		considered.
		"""

		# Don't start up if we already have processes running
		if self.getServerProcs():
			log.error( "Server processes already running, aborting startup" )
			self.ls()
			return False

		# Get server candidates
		if not machines:
			machines = self.cluster.getMachines()
		machines.sort( lambda m1, m2: cmp( m1.totalmhz(), m2.totalmhz() ) )

		# Verify that env is in sync
		if not self.verifyEnvSync( machines, writeBack = True ):
			log.warning( "Candidate machines restricted due to out-of-sync env"	)
			log.warning( "Candidate set is now %s",
						 ",".join( [m.name for m in machines] ) )

		# If group is specified, restrict machine set to that group now
		if group:
			self.cluster.queryTags( "Groups" )
			machines = [m for m in machines \
						if "Groups" in m.tags and group in m.tags[ "Groups" ]]
			log.verbose( "Machines in group %s: %s",
						 group, " ".join( [m.name for m in machines] ) )

		log.verbose( "Candidate machines:" )
		for m in machines:
			log.verbose( m )

		# Bail now if no candidates found
		if not machines:
			log.error( "No machines found satisfying the filters" )
			return False

		# List of server processes we expect to be running
		layout = []

		# Make a list of 'cpus' sorted by speed
		cpus = reduce( operator.concat, [ [m]*m.ncpus for m in machines ] )
		cpus.sort( lambda m1, m2: cmp( m1.mhz, m2.mhz ) )

		# If we are going to need to know about machine Components tags, get
		# them now
		if tags:
			self.cluster.queryTags( "Components", machines )

		# A little class to represent a class of processes for spawning
		class Category:

			UID = self.uid

			# If multiplier is None, we must spawn exactly one process
			# If exclusive, we try to spawn only one of these processes per CPU
			def __init__( self, name, multiplier, exclusive ):
				self.name = name
				self.multiplier = multiplier
				self.exclusive = exclusive
				self.totalCPU = 0.0
				self.machines = []

			# Processes with multiplier == None are considered to be the lowest
			# so that they will be allocated first.  In the event of CPU
			# allocation ties, the higher multiplier is considered to be lower
			# since this will cause it to be allocated to a slower CPU.
			def __cmp__( self, other ):
				if self.multiplier is None or other.multiplier is None:
					return cmp( self.multiplier, other.multiplier )
				else:
					return cmp( self.totalCPU * self.multiplier,
								other.totalCPU * other.multiplier ) or \
								-cmp( self.multiplier, other.multiplier )

			def add( self, machine ):
				self.totalCPU += max( 1-machine.load(), 0 ) * machine.totalmhz()
				self.machines.append( machine )
				pid = machine.startProc( self.name, self.UID, _async_=_async_ )

				if pid == 0:
					log.error( "Couldn't even execute %s on %s",
							   self.name, machine.name )
					return False
				else:
					log.verbose( "Starting %s on %s", self.name, machine.name )
					layout.append( (machine.name, self.name, pid) )
					return True

		# Set up categories for process spawning
		allcats = [ Category( "cellappmgr", None, False ),
					Category( "baseappmgr", None, False ),
					Category( "dbmgr", None, False ),
					Category( "loginapp", None, False ),
					Category( "cellapp", 3.0, True ),
					Category( "baseapp", 5.0, True ) ]
		if bots:
			allcats.append( Category( "bots", 2.0, True ) )

		# Make a copy of the category list, cause we'll want to modify it in the
		# CPU allocation loop
		cats = allcats[:]

		# Make a log entry to say we're starting the server
		self.log( "Starting server" )

		# Allocate all CPUs to categories
		while cpus and cats:

			# Pick the most needy category
			cat = min( cats )

			# Find the slowest CPU that is capable of running this process type
			cpu = None
			for m in cpus:
				if not tags or m.canRun( cat.name ):
					cpu = m
					break

			# If no CPU found, stop trying to assign CPU to this category (we'll
			# fix it up later if no CPUs were allocated)
			if not cpu:
				cats.remove( cat )
				continue

			# Add this process to that category
			if not cat.add( cpu ):
				log.error( "Process execution failure; shutting down server" )
				self.cluster.refresh()
				self.smartStop( forceKill=True )
				return False

			# If the category is exclusive, remove that CPU from the list
			if cat.exclusive:
				cpus.remove( cpu )

			# If the category is singleton, remove it from the list
			if cat.multiplier is None or useSimpleLayout:
				cats.remove( cat )

				# If the category is singleton and there are no more singleton
				# categories, remove the cpu (i.e. don't spawn other stuff on
				# the world server unless you have to)
				if not [c for c in cats if c.multiplier is None] and \
					   cpu in cpus:
					cpus.remove( cpu )

		# If any category didn't get allocated any CPU, allocate it to the
		# fastest machine capable of running it now
		allocateFailed = False
		for cat in [ c for c in allcats if not c.machines ]:

			for m in machines[::-1]:
				if not tags or m.canRun( cat.name ):
					cat.add( m )
					break

			if not cat.machines:
				log.error( "Couldn't find any machines capable of running %ss",
						   cat.name )
				allocateFailed = True

		if allocateFailed:
			log.error( "Some processes weren't started, aborting" )
			return False

		# Start revivers on all machines used if required
		if revivers:
			reviverCat = Category( "reviver", None, False )
			allcats.append( reviverCat )
			for m in machines:
				reviverCat.add( m )

		for c in allcats:
			log.verbose( "%s (%dMHz): %s" % \
						 (c.name, c.totalCPU,
						  " ".join( [m.name for m in c.machines] )) )

		if layout and self.verifyStartup( layout, _async_ = _async_ ):
			self.ls()
			return True
		else:
			return False

	@staticmethod
	def parseXMLLayout( s ):
		"""
		Reads a server layout from an XML string, and returns a list of
		processes in the format [(machine_name, process_name) ...].  Note that
		this is not the format that is expected by layoutIsRunning(), it doesn't
		include the PIDs.  It is up to startFromXML() to include this itself.
		"""

		# TODO: There is very little error checking for the expected format of
		# the XML here.  If the XML is not specified exactly as required, the
		# resulting errors will probably not make much sense.

		doc = minidom.parseString( s )
		layout = []

		for pname in Process.ALL_PROCS:

			# Find the section of the XML tree that deals with these procs.  The
			# plural case is for compatibility with old layouts.
			nodes = doc.getElementsByTagName( pname ) or \
					doc.getElementsByTagName( Process.getPlural( pname ) )

			if not nodes: continue
			root = nodes[0]

			for child in filter( lambda n: n.attributes, root.childNodes ):

				# For "machine" elements
				if child.tagName == "machine":
					mname = child.getAttribute( "name" )
					count = child.getAttribute( "count" ) or "1"
					count = int( count )
					for i in xrange( count ):
						layout.append( (mname, pname) )

				# For "range" elements
				elif child.tagName == "range":
					prefix = child.getAttribute( "prefix" )
					start = int( child.getAttribute( "start" ) )
					end = int( child.getAttribute( "end" ) )
					format = child.getAttribute( "format" ) or "%d"
					count = child.getAttribute( "count" ) or "1"
					count = int( count )

					for i in xrange( start, end+1 ):
						mname = prefix + (format % i)
						for j in xrange( count ):
							layout.append( (mname, pname) )

		# Special-case for old-style layouts with the 'world' section
		worldNodes = doc.getElementsByTagName( "world" )
		if worldNodes:
			mname = worldNodes[0].getAttribute( "name" )
			for pname in ("cellappmgr", "baseappmgr", "loginapp", "dbmgr"):
				layout.append( (mname, pname) )

		return layout

	def startFromXML( self, file, _async_ = None, enforceBasicLayout = False ):
		"""
		Start a server using the layout in the given XML.  The argument can
		either be a filename pointing to an XML file or a file-like object to
		read the XML data from.

		If enforceBasicLayout is True and the layout given in the XML is missing
		any basic server processes, then they will automatically be started too.
		"""

		# Don't do anything if a server's already running
		if self.serverIsRunning():
			log.error( "Can't load layout from XML while server is running!" )
			return False

		if type( file ) == str:
			try:
				xmldata = open( file ).read()
			except Exception, e:
				log.error( "Couldn't read XML data from %s: %s", file, e )
				return False
		else:
			xmldata = file.read()

		layout = self.parseXMLLayout( xmldata )

		# Verify that each machine actually exists
		missing = False
		mnames, pnames = set(), set()
		for mname, pname in layout:
			m = self.cluster.getMachine( mname )
			if m:
				mnames.add( mname )
				pnames.add( pname )
			else:
				log.error( "Layout refers to non-existent machine '%s'", mname )
				missing = True

		if missing:
			log.error( "Aborting startup due to missing machines" )
			return False

		self.log( "Starting server" )

		# Enforce basic layout if required
		if enforceBasicLayout:

			mnames = list( mnames )
			if not mnames:
				log.error( "Can't enforce basic layout with an "
						   "empty prior layout" )
				return False

			for pname in Process.SERVER_PROCS:
				if pname not in pnames:
					layout.append( (random.choice( mnames ), pname) )
					log.notice( "Added missing basic process %s to %s",
								layout[-1][1], layout[-1][0] )

		# Iterate through layout and add the pid to each entry for passing to
		# layoutIsRunning()
		for i in xrange( len( layout ) ):
			mname, pname = layout[i]
			machine = self.cluster.getMachine( mname )
			pid = machine.startProc( pname, self.uid, _async_ = _async_ )
			layout[i] = (mname, pname, pid)
			log.verbose( "Starting %s on %s (pid:%d)", pname, mname, pid )

		if layout and self.verifyStartup( layout, _async_ = _async_ ):
			self.ls()
			return True
		else:
			return False

	def verifyStartup( self, layout, _async_ = None ):

		# Signal async listeners with the layout
		if _async_:
			_async_.update( "layout", layout )

		status = []
		ok = self.cluster.waitFor(
			util.Functor( self.layoutIsRunning,
						  args = [layout, status],
						  kwargs = {"_async_": _async_} ),
			POLL_SLEEP, MAX_STARTUP_SLEEPS )

		if not ok:
			log.error( "The following processes failed to start:" )
			# NB: procStatus is used rather than unpacking directly
			#     in the for loop, as layoutIsRunning can return an
			#     extra 'details' element which will break unpacking
			for procStatus in status:
				mname = procStatus[ 0 ]
				pname = procStatus[ 1 ]
				pid   = procStatus[ 2 ]
				state = procStatus[ 3 ]
				if state != "registered":
					log.error( "%s on %s (pid: %d): %s",
							   pname, mname, pid, state )
		return ok

	def stop( self, signal = None, _async_ = None ):
		"""
		Kills all my processes by sending the given signal, or SIGINT if none
		given.
		"""

		if signal is None:
			signal = messages.SignalMessage.SIGINT

		# Kill revivers first if there are any
		for p in self.getProcs( "reviver" ):
			p.stop()

		# Wait for reviver death
		if not self.cluster.waitFor( lambda: not self.getProcs( "reviver" ),
									 POLL_SLEEP, MAX_POLL_SLEEPS ):
			log.error( "Some revivers haven't shut down!" )
			for p in self.getProcs( "reviver" ):
				log.error( p )
			return False

		# Kick off loginapp controlled shutdown on SIGUSR1
		if signal == messages.SignalMessage.SIGUSR1:
			loginapps = self.getProcs( "loginapp" )
			if loginapps:
				for p in loginapps:
					p.stop( messages.SignalMessage.SIGUSR1 )
			else:
				log.error( "Can't do controlled shutdown with no loginapp!" )
				return False

			# Loginapp's don't know about bots processes so kill them manually
			for bp in self.getProcs( "bots" ):
				bp.stop()

		# Otherwise send signals to all server components
		else:
			for p in self.getProcs():
				if hasattr( p, "stop" ):
					p.stop( signal )

		# Wait for server to shutdown
		if not self.cluster.waitFor(
					util.Functor( self.layoutIsStopped,
						  args = [self.getLayout()],
						  kwargs = {"_async_": _async_} ),
					POLL_SLEEP, MAX_POLL_SLEEPS ):
			procs = self.getProcs()

			if procs:
				log.warning( "Components still running after stop( %d ):" % signal )
				for p in procs:
					log.warning( "%s (load: %.3f)" % (p, p.machine.load()) )

				return False

		return True

	def smartStop( self, forceKill=False, _async_ = None ):
		"""
		Stop the server by the most controlled means possible.
		"""

		errors = False

		# Because of the way the shutdown messages flow, you actually need all
		# the "world" processes running to do a controlled shutdown
		if self.getProc( "loginapp" ) and self.getProc( "dbmgr" ) and \
			   self.getProc( "cellappmgr" ) and self.getProc( "baseappmgr" ):

			self.log( "Starting controlled shutdown" )

			if self.stop( messages.SignalMessage.SIGUSR1, _async_ = _async_ ):
				return True
			else:
				if not forceKill:
					# Don't force processes to quit.
					# If we are doing controlled shutdown, we'll have to wait
					# until the components have all shutdown by themselves,
					# just report on what processes are still up every
					# MAX_POLL_SLEEPS.
					while not self.cluster.waitFor(
						util.Functor( self.layoutIsStopped,
							args = [self.getLayout()],
							kwargs = {"_async_": _async_} ),
						POLL_SLEEP, MAX_POLL_SLEEPS ):

						log.warning( "Components still running after controlled "
							"shutdown initiated:" )
						for p in self.getProcs():
							log.warning( "%s (load: %.3f)", p, p.machine.load() )

					# if we break out, then controlled shutdown is finished
					# (presumably succeeded)
					return True

				log.error( "Controlled shutdown failed" )
				errors = True


		if forceKill:
			self.log( "Starting SIGINT shutdown" )

			if self.stop( messages.SignalMessage.SIGINT, _async_ = _async_ ):
				if errors:
					log.info( "Shutdown via SIGINT successful" )
				return True
			else:
				log.error( "Forced shutdown with SIGINT failed" )
				errors = True

			self.log( "Starting SIGQUIT shutdown" )

			if self.stop( messages.SignalMessage.SIGQUIT, _async_ = _async_ ):
				if errors:
					log.info( "Shutdown via SIGQUIT successful" )
				return True
			else:
				log.error( "Forced shutdown with SIGQUIT failed" )
				errors = True

		else:	
			# Handles the case where only some of the server processes is running 
			# or no server process is running, and force kill is not allowed.
			# The server most likely is in the process of shutting down, although 
			# it may be the case that one or more of the "world" processes may 
			# have crashed.
			# If the user wants to kill the remaining running server processes, 
			# they should use ./control_cluster.py kill command.
			if self.getProcs():
				# List processes still running.
				self.ls()

				msg = \
"\n\n" \
"The server cannot be shut down cleanly. It may already be in the process of\n" \
"shutting down.\n\n" \
"To force the server processes listed above to stop now rather than waiting for\n" \
"them to stop, use the following command:\n" \
"$ ./control_cluster.py kill\n\n" \
"WARNING: Using './control_cluster.py kill' command may cause data loss as\n" \
"BaseApps may be in the process of writing entities to the database."

				log.info( msg )

			else:
				log.info( "No server process is running." )	
				return True

		return False

	def restart( self, _async_ = None ):
		"""
		Shuts down the server then restarts it with the same layout.
		"""

		stream = StringIO()
		self.saveToXML( stream )
		stream.seek( 0 )
		if not self.smartStop( _async_ = _async_ ):
			return False
		return self.startFromXML( stream, _async_ = _async_,
								  enforceBasicLayout = True )

	def startProc( self, machine, pname, count = 1 ):

		# Start new processes and collect their PIDs
		pids = [machine.startProc( pname, self.uid ) for i in xrange( count )]

		# If there are any 0's in there something went wrong
		if 0 in pids:
			log.error( "%d processes didn't start!",
					   len( [pid for pid in pids if pid == 0] ) )
			return False

		# Function to test whether the new processes have started
		allDone = lambda: None not in [machine.getProc( pid ) for pid in pids]

		# Wait till they've started up
		if not self.cluster.waitFor( allDone, 1, 10 ):
			log.error( "Some processes didn't start!" )
			return False
		else:
			return True


	def verifyLayoutIsRunning( self, file ):
		try:
			layout = self.parseXMLLayout( open( file ).read() )
		except IOError:
			print "No such file '%s'" % file
			return False
		except:
		 	print "Error reading '%s'" % file
		 	return False

		runningProcs = self.getProcs()

		for machine,proc in layout:

			foundProc = False
			# If we are still expecting more items in the layout
			# but no more items are running, fail.
			if len(runningProcs) == 0:
				return False

			for activeProc in runningProcs:
				if machine == activeProc.machine.name and \
				proc == activeProc.name:
					foundProc = True
					runningProcs.remove( activeProc )
					break

			if not foundProc:
				return False

		# MessageLogger shouldn't be considered part of the layout
		for remainingProc in runningProcs:
			if remainingProc.name == "message_logger":
				runningProcs.remove( remainingProc )

		if len(runningProcs) == 0:
			return True

		return False


	@Exposed.expose( args = [("file", "the filename to save the layout to")] )
	def saveToXML( self, file ):
		"""Writes this user's cluster layout to XML."""

		# Create XML document and root node
		doc = minidom.Document()
		root = doc.createElement( "cluster" )
		doc.appendChild( root )

		# Now do the non-world processes
		for pname in Process.ALL_PROCS:

			# Count up the number of procs on each machine
			pcounts = {}
			for p in self.getProcs( pname ):
				if pcounts.has_key( p.machine.name ):
					pcounts[ p.machine.name ] += 1
				else:
					pcounts[ p.machine.name ] = 1

			# Bail now if there aren't any
			if not pcounts: continue

			# Make a sorted list of the machines
			machines = filter( lambda m: pcounts.has_key( m.name ),
							   self.cluster.getMachines() )
			machines.sort( Machine.cmpByHostDigits )

			# The root node for these entries
			listNode = doc.createElement( pname )
			root.appendChild( listNode )

			# Make entries for each machine
			for m in machines:
				node = doc.createElement( "machine" )
				node.setAttribute( "name", m.name )
				if pcounts[ m.name ] > 1:
					node.setAttribute( "count", str( pcounts[ m.name ] ) )
				listNode.appendChild( node )

		# Write it to the file
		if type( file ) == str:
			file = open( file, "w" )
		file.write( doc.toprettyxml() )
		if not isinstance( file, StringIO ):
			file.close()
		return True

	#--------------------------------------------------------------------------
	# Subsection: Bot Operations
	#--------------------------------------------------------------------------

	def getBotMachines( self ):
		"""Returns a list of all the machines in the cluster that are candidates
		   for running bots."""

		return filter( lambda m: m.isBotCandidate( self.uid ),
					   self.cluster.getMachines() )

	def getBestAddCandidate( self ):
		"""
		Returns the lowest loaded bot process below the CPU thresh, or None
		if all bot processes are overloaded.
		"""

		bps = sorted( self.getProcs( "bots" ), key = lambda p: p.load )
		if not bps:
			return None

		if bps[0].load < MAX_BOTS_CPU:
			return bps[0]
		else:
			return None

	def getBestDelCandidate( self ):

		# Comparator for deletion.  Puts processes with the lowest number of
		# bots first, then orders by highest CPU load.
		def delcmp( bp1, bp2 ):
			botcmp = cmp( bp1.nbots(), bp2.nbots() )
			loadcmp = cmp( bp2.machine.load(), bp1.machine.load() )
			return botcmp or loadcmp

		# Throw away processes with no active bots
		bps = filter( lambda bp: bp.nbots() > 0, self.getProcs( "bots" ) )
		bps.sort( delcmp )

		if bps:
			return bps[0]
		else:
			return None

	def lsBots( self ):
		"""Prints out information about currently running bots processes, and
		   returns an array of BotProcess objects describing the same info."""

		# Get info about the cluster
		bms = sorted( self.getBotMachines(), cmp = util.cmpAddr,
					  key = lambda m: m.ip )

		usedms = util.uniq( map( lambda p: p.machine, self.getProcs( "bots" ) ),
							cmp )
		if usedms:
			log.info( "machines running bots processes:" )
			for bm in usedms:
				bps = bm.getProcs( "bots" )
				nbots = sum( [bp.nbots() for bp in bps] )
				log.info( "%-11s %d bots on %d bots processes",
						  bm.name, nbots, len( bps ) )
			log.info( "" )

		freems = self.getBotMachines()
		for m in usedms:
			freems.remove( m )
		if freems:
			log.info( "free candidate machines:" )
			for bm in freems:
				log.info( bm )
			log.info( "" )

		log.info( "%d clients\n%d proxies\n%d cell entities",
				  self.getTotalBots(), self.getNumProxies(),
				  self.getNumEntities() )

		for pname, load in self.getLoads().items():
			log.info( "min/avg/max %s load: %s",
					  re.sub( "app", "", pname ), load )


	def addBots( self, numToAdd ):
		"""Add the given number of bots to existing processes or create new
		   processes to handle them as necessary."""

		import time

		log.info( "Adding %d bot%s...", numToAdd, ("s","")[numToAdd==1] )
		totalToAdd = numToAdd
		starttime = time.time()

		while numToAdd > 0:

			try:
				# Refresh all cluster information
				self.cluster.refresh()

				# Find a bots process that isn't overloaded
				bp = self.getBestAddCandidate()

				if not bp:
					log.info( "\tall bots processes are overloaded; "
							  "waiting for more CPU..." )
					time.sleep( CPU_WAIT_SLEEP )
					continue

				# If server components are overloaded, wait for a little bit
				if self.serverIsOverloaded():
					log.info( "\tserver overloaded; waiting for more CPU ..." )
					while self.serverIsOverloaded():
						time.sleep( CPU_WAIT_SLEEP )
						self.cluster.refresh()

				# Add bots
				numToAddNow = min( numToAdd, NBOTS_AT_ONCE )
				bp.addBots( numToAddNow )
				numToAdd -= numToAddNow
				log.info( "\tadded %d to %s:%d (%d done in %.1fs)",
						  numToAddNow, bp.machine.name, bp.port(),
						  totalToAdd - numToAdd,
						  time.time() - starttime )

				# Wait a little bit.  We didn't need to do this before
				# because each refresh() took so long, but now we need to do
				# this or it's easy to overload a running system.
				time.sleep( 1.0 )

			except KeyboardInterrupt:
				break

		log.info( "Added %d bots in %.1fs",
				  totalToAdd - numToAdd, time.time() - starttime )


	def delBots( self, numtoop ):
		"""Deletes the given number of bots from running bots processes, least
		   loaded processes first.  Does not kill empty bots processes."""

		# If no bot processes, bail out
		if not self.getProcs( "bots" ):
			log.error( "no known bot processes to delete bots from" )
			return False

		# Bail if no known bots
		if self.getTotalBots() == 0:
			log.error( "can't delete - no known bots" )
			return False

		# Cap deletion amount if more than known
		numtoop = min( numtoop, self.getTotalBots() )

		log.info( "Deleting %d of %d known bots ..." %
				  (numtoop, self.getTotalBots() ) )
		deleted = 0

		while numtoop > 0:

			# Refresh cluster info
			self.cluster.refresh()

			# The process we're deleting from
			bp = self.getBestDelCandidate()

			# If we couldn't find a del candidate, chances are a bot process
			# timed out when asked for its bot count, so go round again.
			if bp is None:
				continue

			# The number we're actually going to delete at once
			chunksize = min( numtoop, NBOTS_AT_ONCE, bp.nbots() )

			# If the bot process has no bots, something's gone wrong
			assert bp.nbots() > 0

			# Do it
			bp.delBots( chunksize )
			bp.nbots( bp.nbots() - chunksize )
			numtoop -= chunksize
			deleted += chunksize
			log.info( "\tdeleted %d from %s:%d (%d done)",
					  chunksize, bp.machine.name, bp.port(), deleted )

		log.info( "Deleted %d bots OK." % deleted )
		return True

	def setWatchersOnAllBots( self, *values ):
		"""
		This method takes any number of tuples. Each tuple contains the path to
		the value to set and the value to set it to, eg:

		setWatchersOnAllBots( ('defaultControllerType', 'Patrol'),
		                      ('defaultControllerData', 'test.bwp') )

		It sets these watcher values on all bot processes.
		"""

		# Handle the case where you've just got two string arguments
		if values and (type(values[0]) == str):
			values=(values,)

		watcherMessage = messages.WatcherDataMessage()
		watcherMessage.message = watcherMessage.WATCHER_MSG_SET2
		watcherMessage.count = 0

		for value in values:
			log.info( "Setting '%s' to '%s'" % value )
			watcherMessage.addSetRequest( value[0], value[1] )

		sock = socketplus.socket()
		msg = watcherMessage.get()
		for bp in self.getProcs( "bots" ):
			sock.sendto( msg, bp.addr() )
			sock.recvfrom( RECV_BUF_SIZE )

	def setBotMovement( self, controllerType, controllerData, botTag ):
		"""Sets the controllerType and controllerData for all bots matching the
		   given tag, e.g. ('Patrol','server/bots/test.bwp','')."""

		self.setWatchersOnAllBots( ( "defaultControllerType", controllerType ),
								   ( "defaultControllerData", controllerData ),
								   ( "command/updateMovement", botTag ) )

	def runScriptOnBots( self, script = "" ):
		"""Runs Python script on all bot apps. With no args, command is read
		   from stdin, otherwise first arg is the command."""

		if script == "":
			log.info( "Input Python script to run (Ctrl+D to finish):" )
			self.setWatchersOnAllBots( "command/runPython", sys.stdin.read() )
		else:
			self.setWatchersOnAllBots( "command/runPython", script )


	#--------------------------------------------------------------------------
	# Subsection: Exposed stuff
	#--------------------------------------------------------------------------

	def log( self, text, severity = "INFO" ):
		"""
		Send a log message to all loggers on the network.
		"""

		for logger in self.cluster.getProcs( "message_logger" ):
			logger.sendMessage( text, self, severity )

from cluster import Cluster
from process import Process
from machine import Machine

# user.py
