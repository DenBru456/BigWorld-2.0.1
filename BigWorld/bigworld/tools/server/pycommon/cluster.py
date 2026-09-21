"""
Module for querying info about a BigWorld cluster.  Class layout is hierarchical
and most layers of the structure should not define methods which provide direct
access to internals of other layers, although the top level class (Cluster) does
this in some cases for substantial convenience.

Hierarchy
=========

Cluster
|
+- User-----+
|           |
+- Machine  |
   |        |
   +- Process
      |
	  +- WatcherData

"""

import os
import socket
import time
import threading
import types

import messages
import log
import util
import socketplus
import memory_stream
import uid as uidmodule

from exposed import Exposed

import bwsetup; bwsetup.addPath( ".." )


# ------------------------------------------------------------------------------
# Section: Listener Registration
# ------------------------------------------------------------------------------

def registerListener( name = "", kind = "birth",
					  sock = None, host = "localhost", **kwargs ):
	"""
	Registers a birth or death listener with machined.

	@param name     The name of the interface to monitor, e.g. LoginInterface
	@param kind     Either 'birth' or 'death'
	@param sock     The socket replies will go to, or None for a new socket
	@param host     The host of the machined we'll register with

	@kwarg category The category of component to listen for,
	                e.g. SERVER_COMPONENT

    @kwarg uid      The uid to listen for, defaults to self
	@kwarg before   String that will appear before the address in the reply
	@kwarg after    String that will appear after the address in the reply

	@return         The socket to expect notifications on
	"""

	# Category of component
	if kwargs.has_key( "category" ):
		category = kwargs[ "category" ]
	else:
		category = messages.ProcessMessage.SERVER_COMPONENT

	# UID to look for
	if kwargs.has_key( "uid" ):
		uid = kwargs[ "uid" ]
	else:
		uid = uidmodule.getuid()

	# Bytes before and after
	if kwargs.has_key( "before" ):
		before = kwargs[ "before" ]
	else:
		before = ""
	if kwargs.has_key( "after" ):
		after = kwargs[ "after" ]
	else:
		after = ""

	# Create a listening socket if none provided
	if sock == None:
		sock = socketplus.socket()
		sock.bind( ( "localhost", 0 ) )

	# Form MGM to register the listener
	lm = messages.ListenerMessage()

	if kind == "birth":
		lm.param = lm.PARAM_IS_MSGTYPE | lm.ADD_BIRTH_LISTENER
	elif kind == "death":
		lm.param = lm.PARAM_IS_MSGTYPE | lm.ADD_DEATH_LISTENER
	else:
		raise RuntimeError, "Unknown kind: %s" % kind

	# Reply port
	lm.port = socket.htons( sock.getsockname()[1] )

	lm.name = name
	lm.category = category
	lm.uid = uid
	lm.pid = os.getpid()

	# Register the listener
	lm.send( sock, host )

	# Get the registration reply
	while True:
		data, srcaddr = sock.recvfrom( 2048 )
		stream = memory_stream.MemoryStream( data )
		try:
			messages.MGMPacket().read( stream )
			break
		except memory_stream.MemoryStream.error, e:
			log.error( "Couldn't destream listener registration reply" )
			print e

	# Return the reply socket
	return sock


# ------------------------------------------------------------------------------
# Section: Cluster
# ------------------------------------------------------------------------------

class Cluster( Exposed ):
	"""A way of organising information about the machines in a cluster."""

	def __init__( self, **kw ):
		Exposed.__init__( self )

		self.user = kw.get( "user" )
		self.uid = kw.get( "uid" )

		# Mapping from ip addresses to Machine objects
		self.machines = {}

		# Mapping from uids to User objects
		self.users = {}

		self.procs = set()

		self.refresh()

	def __str__( self ):

		ms = self.getMachines()
		ms.sort( Machine.cmpByHostDigits )

		lines = []
		for m in ms:
			lines.append( str( m ) )

		lines.append( "%d machines total" % len( ms ) )

		return "\n".join( lines )

	def lsUsers( self ):

		for u in sorted( self.getUsers(), key = lambda u: u.name ):
			numProcs = len( u.getProcs() )
			log.info( "%s running %d process%s" %
					(u, numProcs, ("", "es")[numProcs != 1]) )
			for p in u.getProcs():
				log.verbose( "\t%s", p )

	def refresh( self, retry = 5, clearUsers = False ):
		for i in xrange( retry ):
			if self.refresh_( clearUsers ):
				return True
		return False

	def refresh_( self, clearUsers = False ):
		# Flat list of all processes (non-essential but useful)
		self.procs = set()

		# Only flush users if explictly required
		if clearUsers:
			self.users.clear()

		# We need to keep a record of the things that are reported by the
		# cluster that is separate to our own internal lists, so we can remove
		# any stale objects which refer to cluster components that no longer
		# exist
		newMachines = set(); newProcs = set()

		# Find all the machines in this cluster, we send out both a
		# HighPrecision and LowPrecision message to ensure we receive
		# replies from both quickly.
		wmm = messages.WholeMachineMessage()
		hpm = messages.HighPrecisionMachineMessage()

		# Find server processes and statistics for each
		psm = messages.ProcessStatsMessage()
		if self.uid:
			psm.uid = self.uid
			psm.param |= psm.PARAM_USE_UID
		elif self.user:
			psm.uid = uidmodule.getuid( self.user )
			psm.param |= psm.PARAM_USE_UID

		# Run the MGM query
		replies = messages.MachineGuardMessage.batchQuery( [hpm, wmm, psm] )

		def handleMachineMessage( mgm, srcIP, srcPort ):
			# TODO: Remove nested function

			machArgs = (self, mgm, srcIP)

			# If we've never seen this machine before make a new object
			if not self.getMachine( srcIP ):
				self.machines[ srcIP ] = Machine( *machArgs )

			# Otherwise re-initialise the existing one, passing the extra
			# False argument to prevent the process map being cleared
			else:
				self.getMachine( srcIP ).__init__( *(machArgs + (False,)) )

			# Mark this machine as non-stale
			newMachines.add( self.getMachine( srcIP ) )

			return


		# Now set up Machine objects
		#  Handle the HighPrecision replies first, then  all machines that
		#  didn't reply with HighPrecision results.

		# dict of machines that have responded with a HighPrecision message
		seenHPM = {}
		for mgm, (srcip, srcport) in replies[ hpm ]:

			# Build a list of seen machines so we don't add them again while
			# processing the WholeMachineMessage replies

			handleMachineMessage( mgm, srcip, srcport )
			seenHPM[ srcip ] = True


		# All the old bwmachined processes that don't understand HPM
		for mgm, (srcip, srcport) in replies[ wmm ]:

			if seenHPM.has_key( srcip ):
				continue

			handleMachineMessage( mgm, srcip, srcport )


		# Sort SERVER_COMPONENTs before WATCHER_NUBs
		def cmpByCategory( m1, m2 ):
			if m1.category == m2.category == m1.WATCHER_NUB or \
			   m1.category == m2.category == m1.SERVER_COMPONENT:
				return 0
			elif m1.category == m1.SERVER_COMPONENT:
				return -1
			else:
				return 0

		replies[ psm ].sort( cmpByCategory, key = lambda (mgm, addr): mgm )
		serverComponents = set()

		# Now set up Process objects
		for mgm, (srcip, srcport) in replies[ psm ]:

			# If we don't know anything about srcip, the WHOLE_MACHINE mgm has
			# been lost, so restart this refresh
			if not self.machines.has_key( srcip ):
				log.error( "Got process %s on unknown host %s!",
						   mgm.name, srcip )
				return False

			# pid == 0 indicates no processes found
			if mgm.pid == 0:
				continue

			hostmachine = self.machines[ srcip ]
			pid = mgm.pid

			# If we have already received a SERVER_COMPONENT message for this
			# process, ignore the additional info
			if hostmachine.getProc( pid ) in serverComponents:
				continue

			# If we already have a Process for this pid, re-init now
			if hostmachine.getProc( pid ):
				p = hostmachine.getProc( pid )
				p.__init__( hostmachine, mgm )
			else:
				p = Process.getProcess( hostmachine, mgm )
				hostmachine.procs[ pid ] = p

			serverComponents.add( p )

			# Since some processes may register more than one interface
			# (i.e. LoginIntInterface and LoginInterface) we make sure we
			# don't add any process twice
			if p not in self.procs:

				# Since we always clear self.procs, we always have to re-append
				self.procs.add( p )

				# Mark this process as non-stale
				newProcs.add( p )

		# Build lists of stale objects
		machinesToRemove = []
		procsToRemove = []

		for m in self.getMachinesIter():
			if m not in newMachines:
				machinesToRemove.append( m )

			for p in m.getProcs():
				if p not in newProcs:
					procsToRemove.append( (m, p) )

		# Clear stale objects
		for m, p in procsToRemove:
			del m.procs[ p.pid ]

		for m in machinesToRemove:
			del self.machines[ m.ip ]

		# Re-initialise existing User objects
		for uid, user in self.users.items():
			try:
				user.__init__( uid, self )
			except user_module.UserError, errMsg:
				# Could not resolve user, remove it.
				del self.users[ uid ]
				log.error( errMsg )		

		# Warn about out-of-date machined's
		for m in self.getMachinesIter():
			if m.machinedVersion < \
				   messages.MachineGuardMessage.MACHINED_VERSION:
				log.verbose( "Out-of-date machined on %s (v%d)",
							 m.name, m.machinedVersion )

		# We made it!
		return True

	# Send a log message to all message logger instances in a cluster
	def log( self, text, user ):
		for logger in self.getProcs( "message_logger" ):
			try:
				logger.sendMessage( text, user )
			except:
				log.error( "Failed to log message to %s" % logger )


	def getProcs( self, name = None, uid = None ):
		"""Returns all procs in the cluster with the given name, under the given
		   UID"""

		return util.filterProcs( self.procs, name, uid )


	def getProc( self, name, uid = None ):
		"""Returns first process matching the given name, or None on failure."""

		for p in self.procs:
			if p.name == name and \
			   (uid is None or p.uid == uid):
				return p

		return None


	def getUser( self, uid = None, machine = None,
				 checkCoreDumps = False, refreshEnv = False ):
		"""
		Returns the User object for the given uid or username, or yourself if
		none given.
		"""

		if uid is None or uid == "":
			uid = uidmodule.getuid()

		# An actual call to machined is made if any flags are set or we don't
		# know anything about this user yet.
		if checkCoreDumps or refreshEnv or \
		   isinstance( uid, messages.UserMessage ) or \
		   (type( uid ) == int and uid not in self.users) or \
		   (isinstance( uid, types.StringTypes ) and \
			uid not in self.users.itervalues()):

			user = user_module.User( uid,
					self, machine, checkCoreDumps, refreshEnv )
			self.users[ user.uid ] = user

		# UID lookup
		if type( uid ) == int:
			return self.users[ uid ]

		# Name lookup
		for user in self.users.itervalues():
			if user.name == uid:
				return user

		return None


	def getUsers( self ):
		"""
		Returns a list of all users who are running at least one process, plus
		any user that has already been manually fetched with getUser().
		"""

		# Make objects for currently unknown users that are running processes
		for p in self.procs:
			if p.uid not in self.users:
				try:
					self.getUser( p.uid )
				except user_module.UserError, errMsg:
					# It's possible something happened to the process / user
					# between discovering the process and attempting the lookup.
					# This is most likely to occur if a process was discovered
					# for a user that isn't known by the rest of the network.
					log.error( errMsg )		

		return self.users.values()


	def getAllUsers( self, machines = [] ):
		"""
		Hits every machined on the network for its entire User mapping and
		returns the union of said mappings.  Note that this doesn't actually
		cause disk access of ~/.bwmachined.conf on every machined, they only
		return user objects that were already in memory.
		"""

		mgm = messages.UserMessage()
		replies = messages.MachineGuardMessage.batchQuery(
			[mgm], 1.0, machines )[ mgm ]

		for reply, _ in replies:
			self.getUser( reply )

		return self.users.values()


	def getMachine( self, ip ):
		"""Returns the Machine for the supplied ip or hostname."""

		if self.machines.has_key( ip ):
			return self.machines[ ip ]

		for m in self.machines.values():
			if m.name == ip:
				return m

		return None

	def getMachines( self ): return self.machines.values()

	def getMachinesIter( self ): return self.machines.itervalues()

	# You can raise this inside Cluster.waitFor() to cause it to fail early
	class TerminateEarlyException( Exception ):
		def __init__( self, *args, **kw ):
			Exception.__init__( self, *args, **kw )

	def waitFor( self, testmethod, sleep, maxretries=0, callback=None ):
		"""
		Waits for testmethod() to return true, in sleep intervals of 'sleep',
		with an optional maximum of 'maxretries' calls to sleep().  If
		'callback' is given, it will be executed on each iteration of the loop.
		"""

		try:
			retries = 0
			while not testmethod() and \
					  (retries < maxretries or not maxretries):
				if callback: callback()
				time.sleep( sleep )
				self.refresh()
				retries += 1

			return (not maxretries) or retries < maxretries

		except self.TerminateEarlyException:
			return False

	def queryTags( self, cat = None, machines = [] ):
		"""
		Query a tag category on each machine, or all machines in the cluster if
		'machines' is None.  Will write the tags to the Machines' tags
		dictionaries.

		If cat is None, then all tags will be fetched from each machine
		"""

		# Special little block for querying all tags on machine set
		if cat is None:

			# Get all category names for all machines
			self.queryTags( "" )

			# Find the set of unique categories
			categories = set()
			for m in self.getMachines():
				for c in m.tags.keys():
					categories.add( c )

			# Do a broadcast query on each category found
			for c in categories:
				self.queryTags( c )
			return

		# Do the request
		mgm = messages.TagsMessage()
		mgm.tags = [cat]
		for mgm, (srcip, srcport) in \
			messages.MachineGuardMessage.batchQuery( [mgm], 1, machines )[mgm]:

			if not self.machines.has_key( srcip ):
				log.error( "Reply from machine at unknown address %s" %
						   srcip )
				continue
			else:
				m = self.machines[ srcip ]

			if mgm.exists:
				if cat:
					m.tags[ cat ] = mgm.tags
				else:
					for t in mgm.tags:
						m.tags[ t ] = []

	def getGroups( self ):

		self.queryTags( "Groups" )
		groups = {}
		for m in self.getMachines():
			if m.tags.has_key( "Groups" ):
				for t in m.tags[ "Groups" ]:
					if not groups.has_key( t ):
						groups[ t ] = [ m ]
					else:
						groups[ t ].append( m )
		return groups


class CacheItem( object ):
	def __init__( self, cluster, kw, currThread ):
		self.cluster = cluster
		self._kw = kw
		self._time = time.time()
		self._thread = currThread

	def matches( self, kw, thread ):
		return kw == self._kw and thread == self._thread

	def isOld( self ):
		return time.time() - self._time > 1.0


class ClusterCache( object ):
	def __init__( self ):
		# A cache of previously created Cluster objects
		self._items = []
		self._lock = threading.RLock()


	def _expunge( self ):
		"""
		Clears out-of-date cluster objects in the cache.
		"""

		self._items = [item for item in self._items if not item.isOld()]


	def get( self, **kw ):
		"""
		Factory method that accepts the same params as the constructor.  Use
		this if you want to recycle Cluster objects that are being created in
		quick succession.
		"""

		try:
			self._lock.acquire()
			self._expunge()

			currThread = threading.currentThread()

			# Try to find a cache object that is new enough
			for item in self._items:
				if item.matches( kw, currThread ):
					return item.cluster

			cluster = Cluster( **kw )
			self._add( CacheItem( cluster, kw, currThread ) )
			return cluster

		finally:
			self._lock.release()


	def _add( self, item ):
		self._lock.acquire()
		self._expunge()
		self._items.append( item )
		self._lock.release()


cache = ClusterCache()

from machine import Machine
from process import Process
import user as user_module

# cluster.py
