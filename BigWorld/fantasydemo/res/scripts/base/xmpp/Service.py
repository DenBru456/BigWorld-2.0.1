import ResMgr

import socket

g_host = None
g_port = None
g_resolvedHost = None
g_resourceName = None
g_isEnabled = False


def isEnabled():
	return g_isEnabled


# This function provides access to the hostname and port of the XMPP Server
# that this service is refering to.
def details():
	return (g_host, g_resolvedHost, g_port)


def init( configFile ):
	sec = ResMgr.openSection( configFile )
	if not sec:
		return (False, "Invalid config file '%s'" % configFile )

	enabled = sec.readBool( "enabled", False )
	if not enabled:
		return (False, "Disabled in %s" % configFile)

	global g_resourceName
	host = sec.readString( "xmppServer/host" )
	port = sec.readString( "xmppServer/port" )
	g_resourceName = sec.readString( "xmppServer/resourceName" )

	# TODO: even though this happens before the critical time where we
	#       need to prevent blocking, it might be useful to add this
	#       as a registerWriteFileDescriptor()
	print "xmpp.Service::init: Verifying XMPP server is alive" 
	sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
	try:
		resolvedHost = socket.gethostbyname( host )
		sock.connect( (resolvedHost, int( port )) )
		sock.close()
		print "xmpp.Service::init: XMPP server '%s' (%s) is alive" % \
				( host, resolvedHost )

		global g_host, g_port, g_isEnabled, g_resolvedHost
		g_host = host
		g_port = port
		g_resolvedHost = resolvedHost
		g_isEnabled = True
		return (True, None)
	except:
		print "xmpp.Service::init: Failed to connect to XMPP server"
		return (False, "Failed to connect to XMPP server")


# Service.py
