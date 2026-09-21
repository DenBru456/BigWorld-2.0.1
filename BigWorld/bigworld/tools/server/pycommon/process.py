from exposed import Exposed

import log
import messages
import re
import signal
import socket
import socketplus
import util

from cluster_constants import MESSAGE_LOGGER_NAME
from cluster_constants import RECV_BUF_SIZE

# ------------------------------------------------------------------------------
# Section: Version
# ------------------------------------------------------------------------------

class Version( object ):
	def __init__( self, major, minor, patch ):
		self.major = major
		self.minor = minor
		self.patch = patch

	def __str__( self ):
		if self.major == 0:
			return "Pre 2.0"
		else:
			return "%d.%d.%d" % (self.major, self.minor, self.patch)

	def __cmp__( self, other ):
		if not isinstance( other, tuple ):
			other = other.asTuple()

		return cmp( self.asTuple(), other )

	def asTuple( self ):
		return (self.major, self.minor, self.patch)

# ------------------------------------------------------------------------------
# Section: Process
# ------------------------------------------------------------------------------

class Process( Exposed ):
	"""Represents a process in a BigWorld cluster.  May have optional extra
	   fields attached (eg. bot processes have an 'nbots' field)."""

	SERVER_PROCS = ["cellappmgr", "baseappmgr", "loginapp", "dbmgr",
					"cellapp", "baseapp"]

	ALL_PROCS = SERVER_PROCS + ["bots", "reviver"]

	# Strictly speaking, loginapp is not a singleton process, but since we have
	# no numbering scheme for them yet and typically only run one, it just makes
	# life easier to think of them in this way.  TODO: Number loginapps and bots
	# processes, probably by using the dbmgr as the id broker.
	SINGLETON_PROCS = ["cellappmgr", "baseappmgr", "loginapp", "dbmgr"]

	INTERFACE_NAMES = { "ReviverInterface": "reviver",
						"LoginIntInterface": "loginapp",
						"LoginInterface": "loginapp",
						"BaseAppIntInterface": "baseapp",
						"BaseAppInterface": "baseapp",
						"CellAppInterface": "cellapp",
						"CellAppMgrInterface": "cellappmgr",
						"BaseAppMgrInterface": "baseappmgr",
						"DBInterface": "dbmgr",
						"BotsInterface" : "bots" }

	COMPONENT_NAMES = { "cellapp": "CellApp",
						"cellappmgr": "CellAppMgr",
						"baseapp": "BaseApp",
						"baseappmgr": "BaseAppMgr",
						"dbmgr": "DBMgr",
						"loginapp": "LoginApp",
						"bots": "Bots",
						"reviver" : "Reviver" }

	HAS_WATCHER_NUB = ALL_PROCS[:]

	def __init__( self, machine, mgm ):

		Exposed.__init__( self )
		self.machine = machine
		self.component = mgm.name
		self.uid = mgm.uid
		self.pid = mgm.pid
		self.id = mgm.id
		self.load = mgm.load / 255.0
		self.mem = mgm.mem / 255.0
		self.mute = False
		self.mercuryPort = socket.ntohs( mgm.port )

		self.version = \
			Version( mgm.majorVersion, mgm.minorVersion, mgm.patchVersion )

		self.interfaceVersion = mgm.interfaceVersion
		self.username = mgm.username
		self.defDigest = mgm.defDigest

		if Process.INTERFACE_NAMES.has_key( self.component ):
			self.name = Process.INTERFACE_NAMES[ self.component ]
		elif mgm.category == mgm.WATCHER_NUB:
			self.name = re.sub( "\d+$", "", self.component )
		else:
			self.name = self.component

		# This the watcher port for this process.  This is private to force
		# everyone to go via port() and addr()
		if not hasattr( self, "_port" ):
			self._port = None

	def __str__( self ):
		return "%-15s on %-8s %2d%% cpu  %2d%% mem  pid:%d version:%s" % \
			   (self.label(), self.machine.name,
				self.load * 100, self.mem * 100, self.pid, str( self.version ))

	def __cmp__( self, other ):
		"""
		Sorts world processes first, alphabetically otherwise.
		"""

		# Early breakout on type error
		if not isinstance( other, Process ):
			return -1

		# Macro to return position in list or len( list ) if not present
		def index( list, x ):
			try:
				return list.index( x )
			except ValueError:
				return len( list )

		return cmp( index( self.ALL_PROCS, self.name ),
					index( self.ALL_PROCS, other.name ) )


	def requiresOwnCPU( self ):
		"""This method can be used to decide whether a process should be run on
			its own CPU/core."""

		if (self.name in Process.SINGLETON_PROCS) and \
				self.name != "dbmgr":
			return False

		return True


	def getExposedID( self ):
		return dict( type = "process", machine = self.machine.name,
					 pid = self.pid )


	def label( self ):
		if self.id > 0:
			return "%s%02d" % (self.name, self.id)
		else:
			return self.name


	def status( self ):
		"""Returns a string representation of the status of the current process.
			This enables access to the DBMgr's new statusDetail watcher, and
			provides the ability for similar functionality to be added to other
			server process types."""

		if self.name == "dbmgr":
			return self.getWatcherValue( "status", "" )
		else:
			return ""


	def isProduction( self ):
		return self.getWatcherValue( "isProduction", False )

	def supportsTCPWatchers( self ):
		return self.version >= (2,0,0)

	def componentName( self ):
		return self.COMPONENT_NAMES[ self.name ]

	def addr( self ):
		return (self.machine.ip, self.port())

	def port( self ):
		"""
		Returns the port number of the watcher nub for this process, but if it
		is unknown as yet, discovers it first.

		Generally, this is OK to do for small query sets because it doesn't time
		out, but if you know you're going to need a lot of watcher ports ahead
		of time, query them beforehand with Cluster.getWatcherPorts() because it
		uses broadcast and is more network efficient.
		"""

		if self._port is None:
			psm = messages.ProcessStatsMessage()
			psm.param = psm.PARAM_USE_CATEGORY | psm.PARAM_USE_PID
			psm.category = psm.WATCHER_NUB
			psm.pid = self.pid

			replies = psm.query( self.machine )
			if replies:
				if replies[0].pid > 0:
					self._port = socket.ntohs( replies[0].port )
				else:
					del self.machine.procs[ self.pid ]
			else:
				log.error( "Could not get watcher port for %s on %s",
						   self.name, self.machine.name )

		return self._port

	def user( self ):
		return self.machine.cluster.getUser( self.uid, self.machine )

	def hasWatchers( self ):
		return True

	def getWatcherData( self, path ):
		return WatcherData( self, path )

	def isServerProc( self ):
		return self.name in Process.SERVER_PROCS

	def getWatcherValue( self, path, default=None ):
		"""Slightly quicker way to query a single Watcher value."""

		# If this process has been marked as mute, then just return the default
		# immediately
		if self.mute:
			return default

		v = self.getWatcherData( path ).value
		if v != None:
			return v
		else:
			return default

	def setWatcherValue( self, path, value ):
		"""Set the watcher value at the given path to the given value.  This is
	       defined in Process rather than WatcherData because more often than
		   not a Watcher set command does not need the whole hierarchical
		   WatcherData thing going on."""

		(status, returnValue) = self.callWatcher( path, value )

		if status:
			isSame = True

			# Let's double check the value now
			import watcher_data_type as WDT
			if isinstance( value, WDT.WatcherDataType ):
				if returnValue != value.value:
					isSame = False

			elif type(returnValue) == type(value):
				if returnValue != value:
					isSame = False
			elif str(returnValue) != str(value):
				# If the response isn't a bool, or the lower case
				# conversion of both set value and response doesn't
				# match up, then we know for certain that we've
				# failed.
				if (type(returnValue) != bool) or \
						(str(returnValue).lower() != str(value).lower()):
					isSame = False

			if not isSame:
				log.info( "Value returned = '%s'. Value set = '%s'" %
							(returnValue, value) )

		return status


	def callWatcher( self, path, value ):
		"""Call or set a watcher at the given path to the given value. A tuple
		containing a success as a bool and the watcher's return value is
		returned."""

		Cluster().log( "Attempting to set watcher '%s'" % path,
			self.user() )

		# Force string conversion
		path = str( path ); #value = str( value )

		wdm = messages.WatcherDataMessage()
		wdm.message = wdm.WATCHER_MSG_SET2
		wdm.count = 0

		wdm.addSetRequest( path, value )

		sock = socketplus.socket()
		sock.sendto( wdm.get(), self.addr() )
		sock.settimeout( 2 )

		# Recv replies until the right one comes through
		while True:
			try:
				data, srcaddr = sock.recvfrom( RECV_BUF_SIZE )
			except socket.timeout:
				break

			if srcaddr != self.addr():
				log.warning( "Got reply from wrong address: %s:%d", *srcaddr )
				continue

			# Re-use the same WDM as was used to send the request so we
			# can use the sequence number as validation of response.
			wdm.set( data )

			if wdm.count == 0:
				log.error( "Expected single reply on set watcher reply packet, "
						   "got empty packet instead" )
				continue

			if wdm.count > 1:
				log.warning( "Expected single reply to " +
							 "setWatcherValue(), got:\n%s" % wdm )
				continue

			reply = wdm.getReply(0)
			replyPath = wdm.getWatcherValue( reply[0] )
			if replyPath != path:
				log.warning( "Incorrect reply to setWatcherValue(): %s" % \
							 replyPath )
				continue
			else:
				# Watcher protocol 2 specifies the status of the set operation
				# as part of the response, so let's use it.
				status = reply[4]
				returnValue = reply[3]

				return (status, returnValue)

		return (False, None)

	def kill( self, signal = None ):
		self.machine.killProc( self, signal )

	#--------------------------------------------------------------------------
	# Subsection: Static methods
	#--------------------------------------------------------------------------

	@staticmethod
	def cmpByLoad( p1, p2 ):
		return Machine.cmpByLoad( p2.machine, p1.machine )

	@staticmethod
	def cmpByName( n1, n2 ):
		ordering = Process.ALL_PROCS
		n1 = n1.lower()
		n2 = n2.lower()
		if n1 in ordering and n2 in ordering:
			return cmp( ordering.index( n1 ), ordering.index( n2 ) )
		elif n1 in ordering:
			return -1
		elif n2 in ordering:
			return 1
		else:
			return cmp( n1, n2 )

	@staticmethod
	def clean( name ):
		"""Strip digits from a process name to reveal its type."""
		return re.sub( "[0-9]", "", name )

	@staticmethod
	def getProcess( machine, mgm ):

		# I'm defining this in here instead of in the class or global scope to
		# avoid having to declare the specific class implementations before
		# this.
		name2proc = { "cellapp" : CellAppProcess,
					  "baseapp" : BaseAppProcess,
					  "cellappmgr" : CellAppMgrProcess,
					  "baseappmgr" : BaseAppMgrProcess,
					  "loginapp" : LoginAppProcess,
					  "dbmgr" : DBMgrProcess,
					  "bots" : BotProcess,
					  "reviver": ReviverProcess,
					  "client": ClientProcess,
					  "message_logger": MessageLoggerProcess }

		if Process.INTERFACE_NAMES.has_key( mgm.name ):
			name = Process.INTERFACE_NAMES[ mgm.name ]
		else:
			name = mgm.name

		if name2proc.has_key( name ):
			return name2proc[ name ]( machine, mgm )
		else:
			return Process( machine, mgm )

	@staticmethod
	def getPlural( name, count = 0 ):
		if count == 1:
			return name

		if name[-1] == "s":
			return name
		else:
			return "%ss" % name

#------------------------------------------------------------------------------
# Section: StoppableProcess
#------------------------------------------------------------------------------

class StoppableProcess( Process ):

	def __init__( self, machine, mgm ):
		Process.__init__( self, machine, mgm )

	#--------------------------------------------------------------------------
	# Subsection: Exposed stuff
	#--------------------------------------------------------------------------

	@Exposed.expose()
	def stop( self, signal = None ):

		if signal is None:
			signal = messages.SignalMessage.SIGINT

		mgm = messages.SignalMessage()
		mgm.signal = signal
		mgm.pid = self.pid
		mgm.uid = self.uid
		mgm.param = mgm.PARAM_USE_UID | mgm.PARAM_USE_PID
		mgm.send( socketplus.socket(), self.machine.ip )


	def stopNicely( self ):
		self.stop()


#------------------------------------------------------------------------------
# Section: ScriptProcess
#------------------------------------------------------------------------------

class ScriptProcess( Process ):

	def __init__( self, machine, mgm ):
		Process.__init__( self, machine, mgm )


	@Exposed.expose()
	def reloadScript( self ):
		import run_script
		return run_script.runscript( [self], "BigWorld.reloadScript()", True )

#------------------------------------------------------------------------------
# Section: Specific Process implementations
#------------------------------------------------------------------------------

class CellAppMgrProcess( StoppableProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )


	def shouldOffload( self, enable ):
		import memory_stream
		stream = memory_stream.MemoryStream()
		stream.pack( ("BBB", 0, 9, enable) )
		sock = socketplus.socket()
		sock.sendto( stream.data(), (self.machine.ip, self.mercuryPort) )


class CellAppProcess( StoppableProcess, ScriptProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )

	def stopNicely( self ):
		self.callWatcher( "command/stopCellAppNicely", () )

	def retireApp( self ):
		self.callWatcher( "command/retireCellApp", "" )

class BaseAppProcess( StoppableProcess, ScriptProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )

	def retireApp( self ):
		self.callWatcher( "command/retireBaseApp", "" )


class BaseAppMgrProcess( StoppableProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )


class LoginAppProcess( StoppableProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )

	def statusCheck( self, verbose = True ):
		(isWatcherOkay, returnValue) = \
			self.callWatcher( "command/statusCheck", () )

		try:
			(output, status) = returnValue
		except TypeError:
			return False

		if output.value.strip() and verbose:
			print output.value,

		return isWatcherOkay and status.value


class DBMgrProcess( StoppableProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )


class ReviverProcess( StoppableProcess ):

	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )

	def hasWatchers( self ):
		# Revivers only support Watchers in 2.0 onwards
		return (self.version.major >= 2)



class BotProcess( StoppableProcess ):
	# technically, it is a script process, but it does not have a
	# BigWorld.reloadScript method
	def __init__( self, machine, mgm ):
		StoppableProcess.__init__( self, machine, mgm )
		self._nbots = None


	def __str__( self ):
		return StoppableProcess.__str__( self ) + " [%d bots]" % self.nbots()


	@Exposed.expose( args = [("num", "the number of bots to add", 1)] )
	def addBots( self, num ):
		"""
		Add bots to this bot process.
		"""
		self.setWatcherValue( "command/addBots", num )


	@Exposed.expose( args = [("num", "the number of bots to delete", 1)] )
	def delBots( self, num ):
		"""
		Delete bots from this bot process.
		"""
		self.setWatcherValue( "command/delBots", num )


	def nbots( self, n = None ):
		"""
		Setter/getter for the number of bots hosted on this bot process.
		"""

		# Get
		if n is None:
			if self._nbots is None:
				self._nbots = int( self.getWatcherValue( "numBots", 0 ) )
			return self._nbots

		# Set
		else:
			self._nbots = n


class ClientProcess( Process ):

	def __init__( self, machine, component, id, pid, uid, load, mem ):
		Process.__init__( self, machine, component, id, pid, uid, load, mem )
		self.name = "client"


class MessageLoggerProcess( Process ):

	def __init__( self, machine, mgm ):
		Process.__init__( self, machine, mgm )


	@Exposed.expose( label = "Roll Logs" )
	def breakSegments( self ):
		mgm = messages.SignalMessage()
		mgm.signal = signal.SIGHUP
		mgm.pid = self.pid
		mgm.uid = self.uid
		mgm.param = mgm.PARAM_USE_UID | mgm.PARAM_USE_PID
		mgm.send( socketplus.socket(), self.machine.ip )


	@Exposed.expose( args = [("user", "the username to log as"),
							 ("message", "the log message")] )
	def sendMessage( self, message, user, severity = "INFO" ):
		"""
		Send the message to this logger, as the given user.  'user' can be
		passed as a string, in which case the User object is looked up.
		"""

		# We have to do all this crap because Windows can't load bwlog.so
		MESSAGE_LOGGER_MSG = 107
		MESSAGE_LOGGER_REGISTER = MESSAGE_LOGGER_MSG + 1
		MESSAGE_LOGGER_PROCESS_DEATH = MESSAGE_LOGGER_REGISTER + 2

		try:
			modName = "bin.%s.bwlog" % util.MF_CONFIG()
			bwlog = __import__( modName, globals(), None, [ "bwlog" ] )

			assert bwlog.MESSAGE_LOGGER_MSG == MESSAGE_LOGGER_MSG
			assert bwlog.MESSAGE_LOGGER_REGISTER == MESSAGE_LOGGER_REGISTER
			assert bwlog.MESSAGE_LOGGER_PROCESS_DEATH == \
				   MESSAGE_LOGGER_PROCESS_DEATH
			assert log.SEVERITY_LEVELS == bwlog.SEVERITY_LEVELS

		except ImportError, e:
			log.warning( "Failed to import bwlog.so on this system: %s", e )
			log.warning( "Recompiling the extension in "
						 "bigworld/src/server/tools/message_logger "
						 "will probably fix this" )

		if type( user ) == str:
			user = self.machine.cluster.getUser( user )

		# Make sure socket is bound to a specific address (not INADDR_ANY) so
		# that it can deregister properly
		sock = socketplus.socket()
		uid = user.uid
		lcm = messages.LoggerComponentMessage( uid, MESSAGE_LOGGER_NAME )
		wdm = messages.WatcherDataMessage()

		# Register this process with the logger
		stream = wdm.getExtensionStream( MESSAGE_LOGGER_REGISTER )
		lcm.write( stream )
		sock.sendto( wdm.get(), self.addr() )

		# Send the message
		stream = wdm.getExtensionStream( MESSAGE_LOGGER_MSG )
		stream.pack( ("BB", 0, log.SEVERITY_LEVELS[ severity ]), message )
		sock.sendto( wdm.get(), self.addr() )

		# Deregister this process with the logger
		stream = wdm.getExtensionStream( MESSAGE_LOGGER_PROCESS_DEATH )
		addr, port = sock.getsockname()
		stream.pack( ("4sHxx",
					  socket.inet_aton( "0.0.0.0" ), socket.htons( port )) )
		sock.sendto( wdm.get(), self.addr() )

from watcher_data import WatcherData
from cluster import Cluster
from machine import Machine

# process.py
