"""
BackgroundTask provides a set of classes to offload tasks from the main
python thread within a BigWorld process. This allows blocking operations
such as file access or network operations to databases to be performed in
an asynchronous manner.

In order to use background tasks, a task manager needs to be started which
is responsible for managing a pool of threads that the tasks will be
executed in. The number of threads used can be controlled per manager
instance.

EXAMPLE:

class MyTask( BackgroundTask.BackgroundTask ):
	def doBackgroundThreadTask( self, mgr ):
		print 'Hello from the background thread'
		mgr.addMainThreadTask( self )

	def doMainThreadTask( self, mgr ):
		print 'Hello from the main thread'


def init():
	...
	threadManager = BackgroundTask.Manager()
	threadManager.startThreads( 1 )

def main():
	...
	threadManager.addBackgroundTask( MyTask() )

def fini():
	...
	threadManager.stopAll()
"""

import BigWorld
import thread
import os
import sys
import threading
import traceback
from Queue import Queue
from time import sleep


# ------------------------------------------------------------------------------
# Section: class Manager
# ------------------------------------------------------------------------------

class Manager:
	"""
	This class defines a background task manager that manages a pool
	of working threads. BackgroundTask objects are added to be processed by
	a background thread and then, possibly by the main thread again.
	"""

	def __init__( self ):
		self.numRunningThreads = 0
		self.__bgThreads = []
		# List of tasks to be performed in the background and foreground threads
		self.__bgTasks = Queue()
		self.__fgTasks = Queue()

		self._readFD, self._writeFD = os.pipe()

		BigWorld.registerFileDescriptor( self._readFD, self.doMainThreadTasks )

		self._writeLock = thread.allocate_lock()


	def __del__( self ):
		self.stopAll()
		os.close( self._readFD )
		os.close( self._writeFD )


	def doMainThreadTasks( self, fd = None ):
		"""
		This method processes queued main thread tasks.
		"""
		# Take off any data from the pipe as we're about to process
		os.read( self._readFD, 1024 )

		while True:
			try:
				fgTask = self.__fgTasks.get( False )
			except:
				break

			try:
				fgTask.doMainThreadTask( self )
			except Exception, e:
				print e


	def startThreads( self, numThreads, threadDataCreator = lambda : None ):
		"""
		This method starts background worker threads. It should be called by
		the main thread.
		"""
		for i in range( 0, numThreads ):
			thread = _Thread( self, threadDataCreator )
			self.__bgThreads.append( thread )
			thread.start()

		self.numRunningThreads += numThreads


	def stopAll( self ):
		"""
		This method stops background worker threads. It should be called by
		the main thread.
		"""
		for i in range( 0, self.numRunningThreads ):
			self.addBackgroundTask( None )


	def onThreadFinished( self, thread ):
		"""
		This method is called by the _ThreadFinisher to ensure the thread
		count of the manager is kept up to date on thread destruction.
		"""
		self.__bgThreads.remove( thread )
		self.numRunningThreads -= 1


	def addMainThreadTask( self, task ):
		"""This method adds a task back into the main thread for execution."""
		if not issubclass( task.__class__, BackgroundTask ):
			raise TypeError( "Main thread tasks must inherit from BackgroundTask" )

		self.__fgTasks.put( task )

		# Magic number '1' is just to send something over the pipe
		self._writeLock.acquire()
		os.write( self._writeFD, '1' )
		self._writeLock.release()


	def addBackgroundTask( self, task ):
		"""This method adds a task into the background thread for execution."""
		if task and not issubclass( task.__class__, BackgroundTask ):
			raise TypeError( "Background tasks must inherit from BackgroundTask" )
		self.__bgTasks.put( task )


	def pullBackgroundTask( self ):
		"""
		This method removes and returns an item from the background task
		queue in a blocking manner.
		"""
		return self.__bgTasks.get( True )


# ------------------------------------------------------------------------------
# Section: class BackgroundTask
# ------------------------------------------------------------------------------

class BackgroundTask( object ):
	"""
	This class provides the interface that should be inherited from and
	implemented by any code wishing to place a job in a BackgroundTask
	Manager.
	"""

	def doBackgroundTask( self, bgTaskMgr, threadData ):
		"""
		This method is called in a background thread to perform potentially
		thread blocking functionality.
		"""
		raise Exception( "Sub classes must implement this method" )


	def doMainThreadTask( self, bgTaskMgr ):
		"""
		This method is invoked in a foreground thread and can be used for
		invoking callbacks to code executing in the main Python thread.
		"""
		raise Exception( "Sub classes must implement this method" )



# ------------------------------------------------------------------------------
# Section: class _Thread
# ------------------------------------------------------------------------------

class _Thread( threading.Thread ):
	"""
	This class encapsulates a worker thread which is used for processing
	background queue tasks.
	"""

	def __init__( self, bgTaskMgr, dataCreator ):
		threading.Thread.__init__( self )
		self._bgTaskMgr = bgTaskMgr
		self._dataCreator = dataCreator


	def run( self ):
		"""
		This method continously pulls and executes background thread tasks.
		"""
		threadData = self._dataCreator()

		while True:
			bgTask = self._bgTaskMgr.pullBackgroundTask()

			if bgTask == None:
				break

			try:
				bgTask.doBackgroundTask( self._bgTaskMgr, threadData )
			except:
				threadName = threading.currentThread().getName()
				print "Caught exception in", threadName
				traceback.print_exc()

				# TODO: Should be a better way to do this. Deleting sys.exc_*
				# and sys.last_* did not work.
				# Generate a dummy exception to clear thread state so that the
				# bgTask will be deleted.
				try:
					raise Exception()
				except:
					pass

				print "Continuing thread", threadName

			# Do not keep a reference to the task while waiting for the next
			# one.
			del bgTask

		self._bgTaskMgr.addMainThreadTask( _ThreadFinisher( self ) )


# ------------------------------------------------------------------------------
# Section: class _ThreadFinisher
# ------------------------------------------------------------------------------

class _ThreadFinisher( BackgroundTask ):
	"""
	This class notifies the BackgroundTask.Manager that a thread has been
	destroyed.
	"""

	def __init__( self, thread ):
		BackgroundTask.__init__( self )
		self.thread = thread


	def doBackgroundTask( self, bgTaskMgr, threadData ):
		"""This method is not used. The class only works in the main thread"""
		raise Exception( "This method is not implemented" )


	def doMainThreadTask( self, bgTaskMgr ):
		"""This method notifies the BackgroundTask.Manager of thread death."""
		bgTaskMgr.onThreadFinished( self.thread )


# ------------------------------------------------------------------------------
# Section: Example BackgroundTasks
# ------------------------------------------------------------------------------

class _GILHoggingTask( BackgroundTask ):
	"""
	This class tests behaviour of monopolising the Python's Global Interpretor
	Lock. (ie: this is an example of what not to do)
	"""

	def __init__( self ):
		self.lower = 1
		self.upper = 9999999


	def doBackgroundTask( self, bgTaskMgr, threadData ):
		"""
		This method is an example of code not releasing the GIL.
		"""

		from random import randrange

		# Randomize a large list of integers
		# The GIL is released every N bytecodes
		numbers = range( self.lower, self.upper)
		for number in numbers:
			rnd = randrange( 0, len(numbers) - 1 )
			number, numbers[rnd] = numbers[rnd], number

		# Sorts the list
		# This actually calls a C function which does not release the GILL
		numbers.sort()

		bgTaskMgr.addMainThreadTask( self )


	def doMainThreadTask( self, bgTaskMgr ):
		print "GILHoggingTask done"

# BackgroundTask.py
