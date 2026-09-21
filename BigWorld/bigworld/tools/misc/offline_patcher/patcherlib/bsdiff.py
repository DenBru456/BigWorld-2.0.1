"""
Module that wraps the _bsdiff module functions, takes care of importing the
correct _bsdiff for the current platform.
"""
import platform

PLATFORM_ARCH = (platform.system() + "_" + platform.architecture()[0]).lower()

# Import the right module.
try:
	_bsdiff = __import__( "bin." + PLATFORM_ARCH + "._bsdiff",
		globals(), None, ["_bsdiff"] )
except ImportError, e:
	raise ImportError, "Couldn't load appropriate _bsdiff.so " \
		"for architecture %s: %s" % (PLATFORM_ARCH, e)


def haveDiffs( path1, path2, bufSize=4096 ):
	"""
	Return True if path1 and path2 differ, otherwise None. bufSize is an
	optional parameter denoting how many bytes to read from each file at a time
	to compare.
	"""

	return _bsdiff.haveDiffs( path1, path2, bufSize )

def diffFilesToFile( srcPath, dstPath, patchPath ):
	"""
	Compute the deltas between the files at srcPath and dstPath and write them
	to patchPath. The format of the file conforms to the file format used in
	the original bsdiff patch utility, and can be used with the patchFromFile
	function.
	"""
	return _bsdiff.diffFilesToFile( srcPath, dstPath, patchPath )

def patchFilesFromFile( srcPath, dstPath, patchPath ):
	"""
	Patch a file at srcPath using a patch created from the diffToFile function
	at patchPath, and write it to dstPath. dstPath can be the same as srcPath
	for in-place patching.
	"""
	return _bsdiff.patchFilesFromFile( srcPath, dstPath, patchPath )

# bsdiff.py

