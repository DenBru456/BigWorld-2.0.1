# This python file sets up the system paths and launches bigworldclient.pyd.

import sys
import os

# Restore sys.setdefaultencoding so that BWAutoImport can set it. We do this here
# instead of making a site-packages/sitecustomize.py so we don't affect non-BW
# scripts running on this machine.
reload(sys)

# Make sure stdout uses the default encoding setup in BWAutoImport. This is to 
# make print behave similarly to how it works in the normal BigWorld client.
class BWStdOut(object):
	def __init__( self, fp ):
		self.fp = fp

	def write( self, s ):
		self.fp.write( str(s) )

sys.stdout = BWStdOut( sys.stdout )
sys.stderr = BWStdOut( sys.stderr )

# Add the client scripts to the path.
fantasydemoPaths = [os.path.normpath( os.path.join( os.getcwd(), r'res\scripts\client' ) ),
					os.path.normpath( os.path.join( os.getcwd(), r'res\scripts\common' ) ),
					os.path.normpath( os.path.join( os.getcwd(), r'..\bigworld\res\scripts\client' ) ),
					os.path.normpath( os.path.join( os.getcwd(), r'..\bigworld\res\scripts\common' ) ),]

sys.path[1:1] =	fantasydemoPaths

# Add client bin directory so we can find the pyd.
sys.path.append( os.path.normpath( os.path.join( os.getcwd(), r'..\bigworld\bin\client' ) ) )
import bwclient

def quoteArg(s):
	if ' ' in s:
		s = s.replace(r'"', r'\"')
		if s[-1] == '\\': s = s + '\\'
		return '"' + s  + '"'
	else:
		return s

bwclient.run(' '.join( [ quoteArg(x) for x in sys.argv] ))
