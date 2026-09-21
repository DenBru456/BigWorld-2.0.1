macroScript Import_HardPoint
	category:"BigWorld"
	toolTip:"Import Hard Point"
	Icon:#("bigworld_icons", 4)
	
(	
	-- BigWorld Import Hard Point
	-- 
	-- Version: 1.0
	-- Date: 2010
	-- Author: Adam Maxwell
	-- Website: http://www.bigworld.com
	-- Works on: MAX 2010
	--
	-- Description
	-- Imports a hard point model from hard_point.fbx located in the 3dsMax imports folder
	-- if the file is not found it will prompt the user for file location
	-- If no or multiple objects are selected when the script is executed the HP will be placed in the scene root
	-- If a single object is selected the HP will be parented to that object and aligned to its position/rotation
	-- The imported HP is scaled to match the scenes system unit size. The HP model will always be ~ 20cm squared
	-- The HP model is coloured to represent the BW axis
	-- The script will ask for a name and append the prefix "HP_". Does not allow the name "", "HP_", HP_00"
	-- 
	-- Known Bugs:
	-- If an existing hard point in the scene is named "HP_00" nothing will be imported and the existing "HP_00" will be used. 
	--
	-- ToDo:
	-- Renamer should accept enter to close renamer
		
	attachToMe = "" -- The parent object to attach the HP too
	
	---------------------------
	-- FBX Import parameters --
	---------------------------	
	sysScaleAmount = 1 / units.SystemScale
	FbxImporterSetParam "ScaleFactor" sysScaleAmount -- Scale the incomming HP model to match scene units
	FbxImporterSetParam "mode" #merge
	FbxImporterSetParam "ScaleConversion" true -- This automatically scales between unit types, e.g. #feet -> #meters
	
	----------------------------
	-- Renaming the HardPoint --
	----------------------------		
	try(destroyDialog Name_HP)catch() -- needs testing
	rollout Name_HP "Hard Point renamer" width:300
	(
		label label1 "Enter Hard Point name"
		label label2 "\"HP_\" prefix will be added automatically"
		edittext nameField ""		
		button renameHP "OK" 		
				
		on renameHP pressed do
		(
			if nameField.text == "" or (matchPattern nameField.text pattern:"HP_*") or (matchPattern nameField.text pattern:"00") then
			(
				messagebox "Please enter a valid name, \n \"HP_\" is added automatically"
			)
			else
			(
				$.name = "HP_" + nameField.text
			)
			destroyDialog Name_HP	
		)
	)
		
	-----------------------------------------	
	-- If one object selected store it  --
	-----------------------------------------
	if selection.count == 1 then
	(
		attachToMe = $
	)
	
	-----------------
	-- import file --
	-----------------	
	bwScriptsPath = (pathConfig.GetDir #usermacros)
	pathOfFile = ""
	failing = false
	
	if importFile "hard_point.fbx" #noPrompt using:FBXIMP  == false then
	(
		messagebox "Cannot import Hard Point because file cannot be found. Please locate the file \"hard_point.fbx\""		
		pathOfFile = getOpenFileName caption:"Select hard_point.fbx" \
		types:"FBX(*.FBX)|*.fbx*|"	filename: (bwScriptsPath + "hard_point.fbx")
		if pathOfFile != undefined then
		(			
			importFile (pathOfFile) #noPrompt using:FBXIMP			
		)
		else
		(
			messagebox 
			( "hard_point.fbx was not found, import failed. \nChanging project folders can cause the hard point to be lost." +
				"\nTry reinstalling the scripts, or copy the HardPoint from the previous 3dsmax project /import folder" +
				"\nCopy this file to 3dsMax's current project folder /imports"
			)
			failing = true
		)
	)
	
	-----------------------------------------------
	-- Attach HP to object attachToMe and Rename --
	-----------------------------------------------
	if failing != true do
	(
		select $HP_00	
		$HP_00.name = uniqueName "HP_" -- prevents cyclical hierarchy on script run twice before object renamed
		createdialog Name_HP 
				
		if attachToMe != "" then
		(
			$.parent = attachToMe
			$.transform = attachToMe.transform
			$.rotation = attachToMe.rotation -- redundant
			messageBox ("Hard Point attached and aligned to " + (attachToMe.name) + ". Please adjust accordingly")
		)
		else
		(
			messagebox "No parent object was selected. HP placed at origin"
		)
		actionMan.executeAction 0 "310"  -- Tools: Zoom Extents Selected
	)
)
