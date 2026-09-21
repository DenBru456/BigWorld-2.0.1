
	-- BigWorld Load BigWorld Material Library
	-- 
	-- Version: 1.0
	-- Date: 2010
	-- Author: Adam Maxwell
	-- Website: http://www.bigworldtech.com
	-- Works on: MAX 2010
	--
	-- Description
	-- Search for and load BigWorld_MaterialLibrary.mat
	--
	-- Known Bugs:
	-- None	
	
global bw_hasSearchedMatLib
	
-- Loads BW material library
if bw_hasSearchedMatLib == undefined then -- only ever load material library once
(
	if loadMaterialLibrary "BigWorld_MaterialLibrary.mat" == false then 
	(
		print "Did not find BigWorld Material Library"
	)
	else
	(
		print "Found BigWorld Material Library"
		bw_hasSearchedMatLib = true
	)
	
)
