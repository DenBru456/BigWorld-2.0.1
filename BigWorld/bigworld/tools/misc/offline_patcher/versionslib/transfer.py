"""
Module for various transfer handlers for patches.
"""

import bwsetup
bwsetup.addPath( "..", 0 )

from patcherlib import utils, md5_interface

import httplib
import logging
import os
import time
import urlparse

log = logging.getLogger( "versionslib.transfer" )

def _joinPathString( path, params, query, fragment ):
	"""Helper method for joining URL path components."""
	if params:
		path += ";" + params
	if query:
		path += "?" + query
	if fragment:
		path += "#" + fragment
	return path

def _formatByteCount( byteCount ):
	"""Helper method for formatting byte counts into human-readable form."""
	if byteCount < 1024:
		return "%d bytes" % byteCount
	if byteCount < 1024 ** 2:
		return "%.02f Kb" % (byteCount / float( 1024 ))
	if byteCount < 1024 ** 3:
		return "%.02f Mb" % (byteCount / float(1024 * 1024))
	if byteCount < 1024 ** 4:
		return "%.02f Gb" % (byteCount / float(1024 * 1024))


class HTTPLogProgressListener( object ):
	"""
	Progress listener that logs progress callbacks.
	"""

	def __init__( self, level=logging.INFO ):
		"""
		Constructor.

		@param level		the logging level to log at
		"""
		self._level = level

	def __call__( self, progress, description ):
		"""
		Progress notification callback method.
		"""
		if progress == -1:
			log.error( "%s: %s", description['url'], description["errorMsg"] )
		else:
			log.log( self._level, "%s: %d%% (%d bytes of %d)",
				description['url'], progress,
				description.get( 'bytesReceived', 0 ),
				description.get( 'bytesTotal', 0 ) )


class PatchTransferHandler( object ):
	# registered transfer handler classes
	_patchTransferClasses = {}

	@staticmethod
	def register( transferTypeName, klass ):
		"""
		Registers a class under a transfer type string.

		@param transferTypeName		the transfer type string
		@param klass				the class to register
		"""
		PatchTransferHandler._patchTransferClasses[transferTypeName] = klass

	@staticmethod
	def create( transferTypeName, destPath, **properties ):
		"""
		Creates a new transfer handler from a registered class.

		@param transferTypeName 	the transfer type, e.g. 'http'
		@param destPath				the destination path of the transfer
		@param properties			The transport properties, these will be
									passed to the constructor of the
									underlying handler class.
		"""
		if transferTypeName not in PatchTransferHandler._patchTransferClasses:
			raise ValueError, "no such transfer type"

		klass = PatchTransferHandler._patchTransferClasses[transferTypeName]
		return klass( destPath, **properties )

	def __init__( self, destPath ):
		"""
		Constructor. Shouldn't be called directly, subclasses call this in their 
		__init__.

		@param destPath		The destination path of the transfer.
		"""
		self._destPath = destPath

		# progress listeners
		self._listeners = []

	def retrieve( self ):
		"""
		Subclasses override this method to actually do the retrieval of the
		patch.
		"""
		raise NotImplementedError

	def addProgressListener( self, listener ):
		"""
		Register a progress listener with this handler. Progress listeners are
		callbacks that take parameters ( progress, description ).

		The progress parameter is an integer from 0 to 100, or -1 if the 
		transfer failed.

		The description parameter is a dictionary containing key-value pairs
		describing the current progress of this PatchTransferHandler.
		Subclasses of PatchTransferHandler should document what keys they
		populate in this dictionary when they notify of their progress.

		@param listener 	The listener callback to register.
		"""
		self._listeners.append( listener )


	def removeProgressListener( self, listener ):
		"""
		De-register a previously registered progress listener from this
		handler.

		@param listener 	The listener to de-register.
		"""
		self._listeners.remove( listener )

	def _notifyProgress( self, progress, description ):
		"""
		General notification method for all listeners registered.
		@param progress		The progress amount, should be an integer from 0
							to 100.
		@param description 	A dictionary containing data that describes the
							progress. Each transfer handler can define more
							fine-grained progress information.
		"""
		for listener in self._listeners:
			listener( progress, description )


class HTTPTransferHandler( PatchTransferHandler ):
	"""
	HTTP transfer handler.

	Progress description keys used in notifications are:
		* url				The URL being retrieved.
		* bytesReceived: 	Number of bytes received.
		* bytesTotal: 		Number of bytes total.
		* status: 			If not HTTP OK, this is set along with errorMsg
							and progress is set to -1.
		* errorMsg: 		If not HTTP OK, this is set with statusCode and
							progress is set to -1.
	"""

	# how much to rollback when resuming
	ROLLBACK_AMOUNT = 4096

	def __init__( self, destPath, baseURL, url, md5sum, **extraProps ):
		"""
		Constructor.

		@param destPath		the destination path to transfer the patch to
		@param baseURL		the base URL to use for relative URLs
		@param url			the URL of the HTTP download
		@param md5sum		the supposed MD5sum of the download
		"""

		log.debug( "HTTPTransferHandler: destPath = %s, "
				"baseURL = %s, url = %s, md5sum = %s",
			destPath, baseURL, url, md5sum )

		PatchTransferHandler.__init__( self, destPath )

		scheme, host, path, params, query, fragID = urlparse.urlparse( url )
		if scheme == "":
			# relative URL
			log.debug( "http transfer relative url: %s", url )
			log.debug( "baseURL = %s", baseURL )
			if not baseURL.endswith( '/' ):
				# Make sure that the end component of baseURL isn't chopped
				# off.
				baseURL += "/"

			url = urlparse.urljoin( baseURL, url )
		elif scheme != "http":
			raise ValueError, "URL scheme is not http: %s" % scheme

		# pick out our properties

		# TODO: MD5 sum of the download from the versions file. We need to
		# check this.
		self._md5sum = md5sum

		# TODO:can be used by outside threads (e.g. UIs) to cancel the download
		self._cancelled = False

		# the path string
		self._path = None

		# the download url
		self._url = None

		# HTTPConnection object
		self._conn = None

		log.debug( "http transfer url: %s", url )
		self._parseURL( url )


		# download total size (bytes)
		self._totalSize = None

		# rollback
		self._rollback = None

		# downloaded size (bytes)
		self._downloadedSize = 0

		# total size of the download (bytes), as retrieved from the HTTP
		# headers
		self._totalSize = None

		# output file object
		self._outFile = None

		# see if we need to resume
		# rollback a bit to see if we're not corrupted
		if os.path.exists( self._destPath ):
			if not os.path.isfile( self._destPath ):
				raise TypeError, "%s exists and is not a file" % \
					self._destPath
			existingSize = os.stat( self._destPath ).st_size

			if existingSize > self.ROLLBACK_AMOUNT:
				self._downloadedSize = existingSize - self.ROLLBACK_AMOUNT
				existingFile = open( self._destPath, "rb" )
				existingFile.seek( -self.ROLLBACK_AMOUNT, 2 )
				self._rollback = existingFile.read( self.ROLLBACK_AMOUNT )
				existingFile.close()

				self._outFile = open( self._destPath, "ab" )

				log.info( "rollback: existing size=%d, len=%d, position=%d",
					existingSize,
					len( self._rollback ), self._outFile.tell() )


		# output file
		if self._outFile is None:
			self._outFile = open( self._destPath, "wb" )

		# HTTP response object
		self._response = None


	def _notifyProgress( self ):

		desc = {}

		desc['url'] = self._url

		if not self._response is None:
			desc['status'] = status = self._response.status
		else:
			desc['status'] = status = None

		if not status is None and not status in \
				(200, 206):
			prog = -1
			desc['errorMsg'] = self._response.reason
		elif self._totalSize:
			prog = self._downloadedSize * 100 / self._totalSize
		else:
			prog = 0

		desc['bytesReceived'] = self._downloadedSize
		desc['bytesTotal'] = self._totalSize

		PatchTransferHandler._notifyProgress( self, prog, desc )

	def _parseURL( self, url ):
		self._url = url

		scheme, host, path, params, query, fragment = \
			urlparse.urlparse( self._url )
		self._path = _joinPathString( path, params, query, fragment )
		if scheme != "http":
			raise TypeError, "url scheme is not http: %s" % scheme

		# the HTTP connection
		if self._conn != None:
			self._conn.close()
		self._conn = httplib.HTTPConnection( host )
		self._response = None


	def _connect( self ):
		self._conn.connect()
		ok = False
		redirects = 0
		while not ok:
			headers = {}
			if self._downloadedSize:
				headers['Range'] = "bytes=%d-" % self._downloadedSize
			self._conn.request( "GET", self._path, headers=headers )
			self._response = self._conn.getresponse()
			log.info( "GET %s %s [%d %s]", self._path,
				", ".join( "%s: %s" % item for item in headers.items() ),
				self._response.status, self._response.reason )
			ok = (self._response.status in
				(httplib.OK, httplib.PARTIAL_CONTENT))

			if not ok:
				if self._response.status in \
						(httplib.MOVED_PERMANENTLY, httplib.FOUND):

					# handle redirects up to MAX_REDIRECTS

					redirects += 1
					if redirects > MAX_REDIRECTS:
						raise IOError, "too many redirects"
					url = self._response.getheader( "Location" )
					self._parseURL( self._url )
					log.info( "connect: redirected to %s", self._url )
				else:
					raise IOError,  \
						"connect: unrecoverable HTTP return code: %d %s" % \
							(self._response.status, self._response.reason)

		# get total size from header
		self._totalSize = self._downloadedSize + int(
				self._response.getheader( "Content-Length", None ) )

		self._notifyProgress()

		log.info( "%s/%s left", _formatByteCount( self._downloadedSize ),
			_formatByteCount( self._totalSize ) )

	def retrieve( self ):
		"""
		Retrieve the patch.
		"""
		self._connect()
		if not self._response:
			raise RuntimeError, "no response"

		bufSize = 1024 * 1024
		readLen = 0
		chunk = self._response.read( bufSize )
		rollbackCheck = ''

		log.debug( "rollback present: %r", not self._rollback is None )
		while chunk:
			self._notifyProgress()
			if self._rollback:
				rollbackCheck += chunk
				if len( rollbackCheck ) >= len( self._rollback ):
					if not rollbackCheck.startswith( self._rollback ):
						raise IOError, "corrupt download"
					log.info( "rollback integrity OK" )
					chunk = rollbackCheck[len( self._rollback ):]
					self._rollback = None
					continue

			self._outFile.write( chunk )

			chunkLen = len( chunk )
			readLen += chunkLen
			self._downloadedSize += chunkLen
			log.debug( "retrieve: read %s (%s buffer size), downloaded=%s"
					" (%s this session) out of %s",
				_formatByteCount( chunkLen ),
				_formatByteCount( bufSize ),
				_formatByteCount( self._downloadedSize ),
				_formatByteCount( readLen ),
				_formatByteCount( self._totalSize ) )

			chunk = self._response.read( bufSize )

		self._outFile.close()

		self._notifyProgress()

		log.info( "retrieve: finished, got %s bytes",
			_formatByteCount( self._downloadedSize ) )


PatchTransferHandler.register( "http", HTTPTransferHandler )

# transfer.py

