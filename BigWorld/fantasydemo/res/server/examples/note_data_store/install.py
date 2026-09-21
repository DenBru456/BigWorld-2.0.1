#!/usr/bin/env python

import glob
import os
import platform
import shutil
import sys

ARCH = ""
if platform.machine() == "x86_64":
	ARCH = "64"

MF_CONFIG = "Hybrid" + ARCH

NOTE_DATA_STORE_DIR = os.path.dirname( os.path.abspath( __file__ ) )
BIGWORLD_DIR = os.path.abspath(
		NOTE_DATA_STORE_DIR + "/../../../../../bigworld" )
LIB_DIR = ''.join( (BIGWORLD_DIR, "/src/lib/bin/", MF_CONFIG) )
INCLUDE_DIR = BIGWORLD_DIR + "/src/lib/python/Include"

DESTINATION = os.path.abspath( "../../../scripts/common" )

MYSQLDB_PACKAGE = "MySQL-python-1.2.2"
MYSQLDB_INSTALL_LIST = [
( "MySQLdb", "%s/Lib/MySQLdb" % DESTINATION, "dir" ),
( "_mysql_exceptions.py", "%s/Lib/_mysql_exceptions.py" % DESTINATION, "file" ),
( "_mysql.so", "%s/lib-dynload%s/_mysql.so" % (DESTINATION, ARCH), "file" )
]

SQLALCHEMY_PACKAGE = "SQLAlchemy-0.4.8"
SQLALCHEMY_INSTALL_LIST = [
( "sqlalchemy", "%s/Lib/sqlalchemy" % DESTINATION, "dir" )
]


def checkDir( dirName ):
	isDir = os.path.isdir( dirName )

	if not isDir:
		print "ERROR: No such directory -", dirName

	return isDir


def installMySQLdb():
	# Point to our Python redist
	if not checkDir( BIGWORLD_DIR ) or \
		not checkDir( LIB_DIR ) or \
		not checkDir( INCLUDE_DIR ):

		print "ERROR: Unable to validate BigWorld root directory"
		sys.exit( 1 )


	os.chdir( NOTE_DATA_STORE_DIR )

	if not checkDestinations( MYSQLDB_INSTALL_LIST ):
		return

	unpack( MYSQLDB_PACKAGE )
	os.chdir( MYSQLDB_PACKAGE )

	# Remove any old builds
	if os.path.isdir( "build" ):
		print "* Removing old build directory"
		shutil.rmtree( "build" )

	# Set the linking flags to use for compiling the _mysql.so module. We need
	# to ensure we override the default distro if it is older (eg: Python 2.4)
	LDFLAGS="LDFLAGS='-L%s -lpython2.6 -lcrypto'" % LIB_DIR

	lines = [ "[DEFAULT]\n",
			"include_dirs = %s\n" % INCLUDE_DIR,
			"lib_dirs = %s\n" % LIB_DIR ]
	FILE = open( "site.cfg", "a" )
	FILE.writelines( lines )
	FILE.close()

	# Try and build the new package
	status = os.system( "%s python setup.py build" % LDFLAGS )
	if status != 0:
		sys.exit( status )
	print

	# Now copy the new directory over
	os.chdir( "build" )
	dirs = glob.glob( "lib.*" )
	if len( dirs ) > 1:
		print "WARNING: There seems to be more than one build dir."

	print "* Copying build from %s" % dirs[0]
	os.chdir( dirs[0] )
	copyItems( MYSQLDB_INSTALL_LIST )


def installSQLAlchemy():
	os.chdir( NOTE_DATA_STORE_DIR )
	if not checkDestinations( SQLALCHEMY_INSTALL_LIST ):
		return

	unpack( SQLALCHEMY_PACKAGE )
	os.chdir( SQLALCHEMY_PACKAGE )

	# Now copy the directory over
	print "* Copying module from %s/lib" % SQLALCHEMY_PACKAGE
	os.chdir( "lib" )
	copyItems( SQLALCHEMY_INSTALL_LIST )


def checkDestinations( items ):
	"""
	This function checks whether the provided paths exists for copying an
	installation into, and whether an existing installation already exists.
	"""
	for item in items:
		path = item[ 1 ]
		destPath = os.path.dirname( path )

		if not os.path.isdir( destPath ):
			os.makedirs( destPath )


	return True


def unpack( package ):
	# Only extract the package if it hasn't already been performed.
	if not os.path.isdir( package ):
		status = os.system( "tar zxf %s.tar.gz" % package )
		if status != 0:
			sys.exit( status )


def copyItems( items ):
	for item in items:

		print " -", item[ 0 ]
		if item[2] == "dir":
			if os.path.exists( item[ 1 ] ):
				shutil.rmtree( item[ 1 ] )

			shutil.copytree( item[ 0 ], item[ 1 ] )
		else:
			shutil.copy( item[ 0 ], item[ 1 ] )


installMySQLdb()
installSQLAlchemy()
