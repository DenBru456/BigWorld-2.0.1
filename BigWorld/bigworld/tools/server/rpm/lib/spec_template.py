"""
Module for parsing a RPM spec file template.

A RPM spec file template has the same format as a regular RPM spec file,
except for custom macro definitions and placeholders.

Macro definitions occur at the top in one contiguous block and cannot
themselves contain macros.

Placeholders are used to indicate where the SpecTemplate class should add its
generated content to. 

There are three such placeholders:

PLACEHOLDER: FILES FOR RPM

This is where the RPM package file entries go.

PLACEHOLDER: PACKAGE SPECIFIC MACROS

This is where the custom macro definitions go.

PLACEHOLDER: BUILDROOT

This is where the BuildRoot: entry goes.
"""


from macro_expander import MacroExpander

import logging
import sys

log = logging.getLogger( 'spec_template' )

PLACEHOLDER_RPM_FILES = "PLACEHOLDER: FILES FOR RPM"
PLACEHOLDER_MACROS = "PLACEHOLDER: PACKAGE SPECIFIC MACROS"
PLACEHOLDER_BUILDROOT = "PLACEHOLDER: BUILDROOT"

class SpecTemplate( object ):
	"""
	This class parses a spec template.
	"""
	def __init__( self, templatePath ):
		"""
		Constructor.

		@param templatePath 	The template path.
		"""

		self.templatePath = templatePath
		self.macros = {}

		lineNum = 1
		hasBlockStarted = False
		for line in self._lines():
			tokens = line.split( None, 2 )

			if len( tokens ) == 0:
				# Empty line.
				continue;

			elif tokens[0] != "%define":
				# Non-macro line.
				if hasBlockStarted:
					break

				continue

			elif len( tokens ) != 3:
				# A macro definition should have three parts:
				# %define <macro_name> <macro_value>
				print "ERROR: Syntax Error: Line %i: Invalid macro " \
					"definition." % (lineNum) 
				sys.exit()


			self.macros[tokens[1]] = tokens[2].strip()
			hasBlockStarted = True

			lineNum += 1

		self.originalMacros = dict( self.macros )

	def _lines( self ):
		return open( self.templatePath ).xreadlines()

	def macroExpander( self ):
		"""
		Return a new MacroExpander object with custom macros from the parsed
		RPM spec template.
		"""
		return MacroExpander( **self.macros )

	def _writePackageFile( self, f, packageFile ):
		f.write( "%s\n" % packageFile.specFileEntry() )

		log.debug( "writing spec file entry for %s => %s", 
			packageFile.source, packageFile.destination )

	def _writePackageFiles( self, f, packageFiles ):
		for packageFile in packageFiles:
			self._writePackageFile( f, packageFile )

	def _writeMacros( self, f, macroExpander ):
		for macro, value in macroExpander.customMacros().iteritems():
			if not macro in self.originalMacros:
				# only need to write out the new macros
				f.write( "%%define %s\t%s\n" % (macro, value) )

	def _writeBuildRoot( self, f, buildRoot ):
		f.write( "BuildRoot: %s\n" % buildRoot )

	def writeSpecFile( self, path, buildRoot, packageFiles, macroExpander ):
		"""
		Write out the spec file, writing out the appropriate build root path,
		file entries for each of the package files, and writing out the custom
		macros from macroExpander.

		@param path 			The spec file output path.
		@param buildRoot		The build root path.
		@param packageFiles		The package file list.
		@param macroExpander	The macro expander. 
		"""

		outFile = open( path, "w" )
		for line in self._lines():

			if PLACEHOLDER_RPM_FILES in line:
				self._writePackageFiles( outFile, packageFiles )

			elif PLACEHOLDER_MACROS in line:
				self._writeMacros( outFile, macroExpander )

			elif PLACEHOLDER_BUILDROOT in line:
				self._writeBuildRoot( outFile, buildRoot )

			else:
				outFile.write( line )
		outFile.close()

# spec_template.py

