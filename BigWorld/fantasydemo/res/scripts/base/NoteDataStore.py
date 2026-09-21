# 
# NOTE:
#
# There is a known issue with using the BackgroundTaskMgr where performing
# any operation that can modify an Entity's data (for example either property
# set operations or remote method calls) from within the doBackgroundTask()
# method may cause network packet corruption and in turn a process crash.
#
# To avoid this issue, when using Python BackgroundTasks perform all entity
# modifications and interactions from within the doMainThreadTask() callback.
#

import ResMgr

import BackgroundTask

try:
	import AsyncSQLAlchemy
	from sqlalchemy import Column, Integer, UnicodeText
	from sqlalchemy.ext.declarative import declarative_base
	import MySQLdb
	import _mysql
	hasRequiredModules = True
except Exception, e:
	print e
	print "To enable the Note Data Store example please see " \
			"fantasydemo/res/server/examples/note_data_store/instructions.txt"
	hasRequiredModules = False



NOTEREPORTING_THREADS = 5

conn = None
bgTaskMgr = None
isReady = False


def init( config_file ):

	global conn
	if conn != None:
		print "NoteDataStore.init: A connection already exists, failing."
		return False

	if not hasRequiredModules:
		return False

	status = True

	sec = ResMgr.openSection( config_file )
	if sec == None:
		print "NoteDataStore.init: %s not found." % config_file
		return False

	enabled = sec.readBool( "enabled", False )
	if enabled == None or enabled == False:
		return False

	host = sec.readString( "database/host" )
	username = sec.readString( "database/username" )
	password = sec.readString( "database/password" )
	dbname = sec.readString( "database/databaseName" )
	dbtype = sec.readString( "database/type" )

	dburi = "%s://%s:%s@%s/%s" % (dbtype, username, password, host, dbname)

	try:
		conn = AsyncSQLAlchemy.SQLAlchemyConnInfo( dburi )

	except Exception, e:
		print "NoteDataStore.init: Failed to init SQLAlchemy: %s" % dburi
		print e
		return False

	global bgTaskMgr
	bgTaskMgr = BackgroundTask.Manager()
	bgTaskMgr.startThreads( NOTEREPORTING_THREADS )

	# Go and load the tables from the DB now
	task = LoadTableTask( conn )
	bgTaskMgr.addBackgroundTask( task )

	return True


def fini():
	global isReady
	isReady = False

	if bgTaskMgr != None:
		bgTaskMgr.stopAll()
		global bgTaskMgr
		bgTaskMgr = None

	if conn != None:
		global conn
		conn = None


def isEnabled():
	return isReady and hasRequiredModules


def createSession():
	return conn.createSession()


#--------------
# Table loading
#--------------
class LoadTableTask( BackgroundTask.BackgroundTask ):
	"""This class creates a new note in the note reporting database."""

	def __init__( self, conn ):

		self.conn = conn


	def doBackgroundTask( self, bgTaskMgr, threadData ):

		session = conn.createSession()
		status = True

		try:
			Note.__table__.create( bind=conn.db_engine, checkfirst=True )
		except:
			status = False

		session.close()
		session = None

		global isReady
		isReady = status


#---------------------------
# Database Table definitions
#---------------------------
if hasRequiredModules:
	SQLAlchemyBase = declarative_base()
	class Note( SQLAlchemyBase ):
		__tablename__ = 'notes'

		id = Column( Integer, autoincrement = True,
					nullable = False, primary_key = True )
		description = Column( UnicodeText )


		def __init__( self, description ):
			self.description = unicode( description )

# NoteDataStore.py
