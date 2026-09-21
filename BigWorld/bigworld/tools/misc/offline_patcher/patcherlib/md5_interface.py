import sys


major, minor, patch = sys.version_info[:3]
if major == 2 and minor < 5:
	# use md5 module deprecated in 2.5
	from md5 import new as md5
else:
	# use hashlib
	import hashlib
	from hashlib import md5

# md5_interface.py
