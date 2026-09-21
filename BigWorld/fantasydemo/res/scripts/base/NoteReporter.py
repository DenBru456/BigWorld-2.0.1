import NoteDataStore

from BackgroundTask import BackgroundTask
try:
	from AsyncSQLAlchemy import warn_exception
except:
	pass


class AddNoteTask( BackgroundTask ):
	"""This class creats a new note in the note reporting database."""

	def __init__( self, noteReporter, description ):
		self.noteReporter = noteReporter
		self.description = description
		self.note = None
		self.status = None


	def doBackgroundTask( self, bgTaskMgr, threadData ):
		session = NoteDataStore.createSession()

		# TODO: determine space information / position
		self.note = NoteDataStore.Note( self.description )
		session.add( self.note )

		(self.status, result) = warn_exception( session.flush )

		session.close()

		bgTaskMgr.addMainThreadTask( self )


	def doMainThreadTask( self, bgTaskMgr ):
		assert( self.status != None )

		noteid = 0
		if self.status:
			noteid = self.note.id

		self.noteReporter.onAddNote( noteid )


class GetNoteTask( BackgroundTask ):
	"""This class retrieves notes from the note reporting database."""

	def __init__( self, noteReporter ):

		self.noteReporter = noteReporter
		self.status = None
		self.result = []


	def doBackgroundTask( self, bgTaskMgr, threadData ):
		session = NoteDataStore.createSession()
		query = session.query( NoteDataStore.Note )

		(self.status, self.result) = warn_exception( query.all )

		session.close()
		session = None

		bgTaskMgr.addMainThreadTask( self )


	def doMainThreadTask( self, bgTaskMgr ):
		assert( self.status != None )

		self.noteReporter.onGetNotes( self.result )


class NoteReporter( object ):
	"""This class manages the interface for note addition and retrieval."""

	def addNote( self, description ):
		# Only add a note if the connection the DB has been established and
		# the tables have been reflected.
		if not NoteDataStore.isEnabled():
			print "Unable to add note, NoteDataStore isn't ready"
			return

		task = AddNoteTask( self, description )
		NoteDataStore.bgTaskMgr.addBackgroundTask( task )


	def onAddNote( self, id ):
		pass


	def getNotes( self ):

		# Only add a note if the connection the DB has been established and
		# the tables have been reflected.
		if not NoteDataStore.isEnabled():
			print "Unable to add note, NoteDataStore isn't ready"
			return

		task = GetNoteTask( self )
		NoteDataStore.bgTaskMgr.addBackgroundTask( task )


	def onGetNotes( self, notes ):
		pass
