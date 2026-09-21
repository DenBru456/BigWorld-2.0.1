-- macroScript Is_Planar
-- 	category:"BigWorld"
-- 	toolTip:"Check if object is Planar"
-- 	Icon:#("bigworld_icons", 1)
-- 	
-- BigWorld coplanar test
	-- 
	-- Version: 1.0
	-- Date: 2010
	-- Author: Adam Maxwell
	-- Website: http://www.bigworldtech.com
	-- Works on: MAX 2010
	--
	-- Description:
	-- Tests if an objects verts are coplanar by
	-- Create array of verts, Use vert 1 and everyother vert to create an array of edges
	-- Cross product of edge 1 and i normalized then compared with each other, if same then planar
	-- Note: discards verts too close together, discards edge vectors that are the normalized same
	--
	-- ToDo:
	--
	-- Known Bugs:
	-- Crashes if you run it with a camera lookat controller which is superclass geometry	

function IsPlanar selectedObject =
(	
	global AngleDivergence = 0.98 -- filter tolerance angle between two edges (1 = same edge, 0 = perpendicular edge, i.e 1 is more sensitive)
	global VertTolerance = 0.01 -- filter tolerence distance between verts
	global VertThreshold = 15 -- maximum number of verts in object before prompt continue
	global filteringUsed = false -- switched if vert tolerance or edge tolerance is used
	
	global vertCount
	global hasSearchedMatLib -- was persistent
	global vertArray = #()
	global filteredVertArray = #()
	global edgeArray = #()
	global normalArray = #()
	global filteredEdgeArray = #()
	bwMacroScriptsPath = (pathConfig.GetDir #usermacros)
		
	if superClassOf selectedObject == GeometryClass then
	(
		----------------------------
		--------Vert Array-------
		----------------------------
		
		for vertEx in selectedObject.mesh.verts do 
		(					
			append vertArray vertEx.pos					
		)
		
		-- Vert number threshold				
		vertCountOK = true
		if vertArray.count > VertThreshold then
		(
			vertCountOK = querybox (selectedObject.name + " contains more than the usual number of vertices for a typical portal.\nAre you sure you want to continue?")
		)
		
		if vertCountOK == true then
		(
			------------------------------------
			--Remove verts close to vert 1--
			------------------------------------
			
			vertArrayLength = vertArray.count
			append filteredVertArray vertArray[1] -- we are comparing everything to vertArray[1], it cannot be filtered out
			for i = 2 to vertArrayLength do 
			(				
				if length (vertArray[1] - vertArray[i]) > VertTolerance then
				(
					append filteredVertArray vertArray[i]
				)
				else
				(
					filteringUsed = true 
				)
			)
			
			-----------------------------
			--CREATE EDGE ARRAY--
			-----------------------------
		
			-- Create array of edge vectors
			vertArrayLength = filteredVertArray.count
			for i = 2 to vertArrayLength do 
			(
				newEdge = filteredVertArray[i] - filteredVertArray[1]
				append edgeArray newEdge
			)			
			
			-------------------------------------
			--CREATE Filtered Edge Array --
			-------------------------------------
			
			edgeArrayLength = edgeArray.count
			append filteredEdgeArray edgeArray[1] -- not filtering 1, because all others are compared to 1
			
			for i = 2 to edgeArrayLength do 
			(
				-- Discard same vector edges by dot prodcut. if the dot product is ~ 1 then the angle between them is 0
				norm_1 = normalize(edgeArray[1])
				norm_i = normalize(edgeArray[i])
				if dot norm_1 norm_i > AngleDivergence then
				(
					-- print "An edge was filtered"
				)
				else
				(
					-- print "edge accepted"
					append filteredEdgeArray edgeArray[i]
				)					
			)
			
			-------------------------------------
			--CREATE NormCROSS ARRAY--
			-------------------------------------
			
			filteredEdgeArrayLength = filteredEdgeArray.count
			for i = 2 to filteredEdgeArrayLength do
			(						
				crossProd = cross filteredEdgeArray[1] filteredEdgeArray[i]						
				newNormalVector = normalize crossProd
				append normalArray newNormalVector					
			)
				
			-----------------------------
			--Compare Normal Array--
			-----------------------------
						
			normalArrayLength = NormalArray.count
			for i = 2 to normalArrayLength do
			(
				if normalArray[1] != normalArray[i] do
				(
					failCase = "Not planar"
					return failCase 
				)
			)
			if filteringUsed == true do
			(
				messagebox "Some vertices were ignored during coplanar testing because they were too close to each other, portal may fail"
			)
			failCase = "Is planar"
			return failCase			
		)
		else -- vertCount OK
		(
			failCase = "Too many verts"
			return failCase
		)
	)
	else -- Is geometry
	(
		failCase = "Not geometry"
		return failCase
	)	
)
	

