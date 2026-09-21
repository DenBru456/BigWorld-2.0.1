"""
This is an example of how to disable/enable garbage collection, and how to
activate debugging. Debugging output is sent to stdout.

By default, all components that use Python have its garbage collection disabled.
However, script developers may find garbage collection to be useful to identify
leaks due to cyclical memory references.

More information about how the Python garbage collection facility works can be
found in the Python documentation for the gc module.

This script can be used in the personality script (BaseApp, CellApp or client)
to activate the functions on BigWorld component start up.
"""

try:
	import gc
	# These are documented in the gc module section of the Python manual
	GC_DEBUG_FLAGS =  gc.DEBUG_STATS | gc.DEBUG_COLLECTABLE | \
		gc.DEBUG_INSTANCES | gc.DEBUG_OBJECTS
except ImportError:
	GC_DEBUG_FLAGS = 0

def gcEnable():
	"""
	Enable garbage collection. Raises a SystemError if garbage collection is
	not supported.
	"""
	try:
		import gc
		gc.enable()
	except ImportError:
		raise RuntimeError, "Garbage collection is not supported"

def gcDisable():
	"""
	Disable garbage collection.
	"""
	try:
		import gc
		gc.disable()
	except ImportError:
		# do nothing
		return

def gcDebugEnable():
	"""
	Call this function to enable garbage collection debugging. Prints a warning
	message if there is no support for garbage collection.
	"""
	try:
		import gc
		gc.set_debug( GC_DEBUG_FLAGS )
	except ImportError:
		print "Could not import gc module; "\
			"garbage collection support is not compiled in"

#GarbageCollectionDebug.py
