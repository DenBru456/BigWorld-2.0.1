# This module is automatically imported.

# This code copied from Python's site.py module.
import __builtin__

import encodings

import pydoc

# If you change the default encoding, you should also change this for WebConsole
# in bigworld/tools/server/web_console/common/encoding.py
DEFAULT_ENCODING = "utf-8"
# DEFAULT_ENCODING = "gb18030"

class _Helper(object):
    """Define the built-in 'help'.
    This is a wrapper around pydoc.help (with a twist).

    """

    def __repr__(self):
        return "Type help() for interactive help, " \
               "or help(object) for help about object."
    def __call__(self, *args, **kwds):
        return pydoc.help(*args, **kwds)

def sethelper():
    __builtin__.help = _Helper()


# Set up the default encoding

def setDefaultEncoding():
	import sys
	if hasattr( sys, "setdefaultencoding" ):
		sys.setdefaultencoding( DEFAULT_ENCODING )
		del sys.setdefaultencoding
	print "Default encoding set to", sys.getdefaultencoding()

def testUnicode():
	import unicode_test
	unicode_test.run()

def main():
	sethelper()
	setDefaultEncoding()
	testUnicode()

main()

# BWAutoImport.py
