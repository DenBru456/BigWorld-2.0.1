"""
Utility module.
"""
import bz2
import logging
import os
import shutil
import zipfile

from md5_interface import md5

log = logging.getLogger( "patcherlib.utils" )

def getFileContents( path ):
	f = open( path, 'rb' )
	contents = readFromStream( f )
	f.close()
	return contents


def writeToFile( dstPath, contents ):
	dstFile = open( dstPath, 'wb' )
	dstFile.write( contents )
	dstFile.close()

def readFromStream( stream, bufSize = None ):
	output = ''
	if not bufSize:
		chunk = stream.read()
	else:
		chunk = stream.read( bufSize )

	while chunk:
		output += chunk
		if not bufSize:
					chunk = stream.read()
		else:
			chunk = stream.read( bufSize )

	return output

def verifyMD5( path, md5sumHex ):
	h = md5()
	f = open( path, 'rb' )
	chunk = f.read( 4096 )
	h.update( chunk )
	while chunk:
		chunk = f.read( 4096 )
		h.update( chunk )
	f.close()
	return h.hexdigest() == md5sumHex


def filesHaveDiffPy( pathA, pathB, bufferSize=4096 ):
	"""
	Return True if files differ between pathA and pathB, otherwise return
	False.
	"""
	lenA = os.stat( pathA ).st_size
	lenB = os.stat( pathB ).st_size

	if lenA != lenB:
		return True

	a = open( pathA, 'rb' )
	b = open( pathB, 'rb' )

	lenLeft = lenA

	while lenLeft:
		blockA = a.read( bufferSize )
		blockB = b.read( bufferSize )

		lenLeft -= len( blockA )
		if blockA != blockB:
			a.close()
			b.close()
			return True
	a.close()
	b.close()
	return False

try:
	from bsdiff import haveDiffs as filesHaveDiff
except ImportError:
	filesHaveDiff = filesHaveDiffPy


def zipExtractAll( zipFilePath, outputPath ):
	"""
	Extract a zip archive to the given destination directory.

	@param zipFilePath 	The path to the zip file.
	@param outputPath 	The output directory path.
	"""


	try:
		zipFile = zipfile.ZipFile( zipFilePath, "r",
			allowZip64=True )
	except:
		# Python 2.4 doesn't support allowZip64 parameter
		zipFile = zipfile.ZipFile( zipFilePath, "r" )

	for filename in zipFile.namelist():
		if filename.endswith( '/' ):
			dirPath = os.path.join( outputPath, filename )
			if not os.path.exists( dirPath ):
				log.debug( 'extracting from zip %s dir %s', 
					zipFilePath, filename )
				os.makedirs( os.path.join( outputPath, filename ) )
		else:
			dirPath = os.path.join( outputPath,
				os.path.dirname( filename ) )
			if not os.path.exists( dirPath ):
				os.makedirs( dirPath )
			log.debug( "extracting from zip %s file %s", 
				zipFilePath, filename )
			writeToFile( os.path.join( outputPath, filename ),
				zipFile.read( filename ) )
	zipFile.close()


def zipCreateFromDir( inputPath, zipFilePath, removeDir=True, 
		compression=zipfile.ZIP_DEFLATED ):
	"""
	Create a zip file from the contents of a directory.

	@param inputPath	The directory.
	@param zipFilePath	The zip file output path.
	@param removeDir	Remove the directory after creating the zip file.
	"""

	try:
		outZipFile = zipfile.ZipFile( zipFilePath, mode="w",
			compression=compression, allowZip64=True )
	except:
		# Python 2.4 doesn't support compression and allowZip64 parameters.
		outZipFile = zipfile.ZipFile( zipFilePath, mode="w" )

	for dirPath, dirnames, filenames in os.walk( inputPath,
			topdown=False ):
		arcPath = dirPath[len( inputPath ) + 1:]
		for filename in filenames:
			outZipFile.write( os.path.join( dirPath, filename ),
				os.path.join( arcPath, filename ),
				compression )
			if removeDir:
				os.remove( os.path.join( dirPath, filename ) )
		for dirname in dirnames:
			outZipFile.writestr( 
				os.path.join( arcPath, dirname ) + "/",
				"" )
			if removeDir:
				os.rmdir( os.path.join( dirPath, dirname ) )
	
	if removeDir:
		os.rmdir( inputPath )

	outZipFile.close()


def hostToCanonicalPathSep( hostPath ):
	"""
	This is used to do canonicalise relative path names by forcing 
	path component separators to be the forward-slash.
	
	@param 	hostPath 	The host path to canonicalise.
	"""
	if os.sep == "\\":
		# Only have to do this for Windows.
		return hostPath.replace( '\\', '/' )
	else:
		return hostPath

def bzipCompressFile( inputPath, outputPath ):
	outFile = open( outputPath, "wb" )
	outFile.write( bz2.compress( getFileContents( inputPath ) ) )
	outFile.close()

def bzipDecompressFile( inputPath, outputPath ):
	outFile = open( outputPath, "wb" )
	outFile.write( bz2.decompress( getFileContents( inputPath ) ) )
	outFile.close()

# utils.py

