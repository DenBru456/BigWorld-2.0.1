from GameData import PlayerModelData
import AvatarModel
import random
import re

def modelListToCharacterClassString( models ):
	"""
	Return a string identifying what character class the given model list
	represents, e.g. ranger or warrior.

	@param models 	The list of resource paths pointing to models that
					are composed into a particular character class's
					in-game avatar.
	"""
	charClass = None

	# Just pick the first model in the list, and extract the path component
	# after characters/avatars
	if len( models ) > 0:
		matches = re.search( r'characters/avatars/([^/]+)/', models[0] )
		if matches:
			charClass = matches.group( 1 )

	# If we don't have one, try an NPC model
	if charClass is None:
		if len( models ) > 0:
			matches = re.search( r'characters/npc/([^/]+)/', models[0] )
			if matches:
				charClass = matches.group( 1 )

	# Fallback
	if charClass is None:
		charClass = "(unknown)"

	return charClass


def defaultPlayerModel():
	return {'models':['characters/avatars/ranger/ranger_body.model',
					  'characters/avatars/ranger/ranger_head.model',],
			'dyes':[],
			'sfx':[] }

def randomPlayerModel( realm=None ):
	filteredModels = PlayerModelData.PLAYER_MODELS
	if realm is not None:
		filteredModels = [ x for x in filteredModels if x.realm == realm ]
		
	if len(filteredModels) == 0:
		print "ERROR: randomPlayerModel - no player models available for realm '%s'." % realm
		filteredModels = PlayerModelData.PLAYER_MODELS

	baseModel = random.choice( filteredModels )
	return baseModel.createInstanceWithRandomCustomisations()


def reCustomisePlayerModel( unpackedAvatarModel ):
	for model in PlayerModelData.PLAYER_MODELS:
		if set( model.models ).issubset( set( unpackedAvatarModel['models'] ) ):
			return model.createInstanceWithRandomCustomisations()
	assert "source model is not a player model. ['%s']" % "', '".join( unpackedAvatarModel['models'] )



# This is a temporary solution until the character customisation screen is
# implemented.
def nextPresetModel( oldAvatarModel ):
	if oldAvatarModel in PRESET_MODELS:
		return PRESET_MODELS[(PRESET_MODELS.index( oldAvatarModel ) + 1) % len(PRESET_MODELS)]
	else:
		return PRESET_MODELS[0]

def previousPresetModel( oldAvatarModel ):
	if oldAvatarModel in PRESET_MODELS:
		return PRESET_MODELS[PRESET_MODELS.index( oldAvatarModel ) - 1]
	else:
		return PRESET_MODELS[0]


# created using [PlayerModel.randomPlayerModel() for i in range( 6 )]
PRESET_MODELS = \
	[
		{'models': ['characters/avatars/ranger/ranger_body.model', 'characters/avatars/ranger/ranger_head.model'], 'dyes': [{'tint': 'Default', 'materialGroup': 'Single_material_skinned'}, {'tint': 'Merchant', 'materialGroup': 'Legs_skinned'}], 'sfx': []},
		{'models': ['characters/avatars/ranger/ranger_body.model', 'characters/avatars/ranger/ranger_head.model'], 'dyes': [{'tint': 'CustomTorso', 'materialGroup': 'Single_material_skinned'}, {'tint': 'Default', 'materialGroup': 'Legs_skinned'}], 'sfx': []},
		{'models': ['characters/avatars/female_warrior/models/fw_body_00.model', 'characters/avatars/female_warrior/models/fw_head_00.model', 'characters/avatars/female_warrior/models/fw_hair_short_thick_00.model', 'characters/avatars/female_warrior/models/fw_1b_tiara_00.model', 'characters/avatars/female_warrior/models/fw_1b_pantsclipdecoration_00.model', 'characters/avatars/female_warrior/models/fw_1b_pantsarmour_00.model', 'characters/avatars/female_warrior/models/fw_1b_chestarmour_00.model', 'characters/avatars/female_warrior/models/fw_1b_boots_00.model' ], 'dyes': [{'tint': 'Default', 'materialGroup': '_1B_Body_skinned'}], 'sfx': []},
		{'models': ['characters/avatars/female_warrior/models/fw_body_00.model', 'characters/avatars/female_warrior/models/fw_head_00.model', 'characters/avatars/female_warrior/models/fw_hair_long_00.model', 'characters/avatars/female_warrior/models/fw_1a_belt_00.model', 'characters/avatars/female_warrior/models/fw_1a_boots_00.model', 'characters/avatars/female_warrior/models/fw_1a_breastarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_chestarmour01_00.model', 'characters/avatars/female_warrior/models/fw_1a_forearmarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_gloves_00.model', 'characters/avatars/female_warrior/models/fw_1a_leftlegarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_ribarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_rightlegarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_shoulderarmour_00.model', 'characters/avatars/female_warrior/models/fw_1a_upperarmarmour_00.model'], 'dyes': [{'tint': '1a', 'materialGroup': '_1B_Body_skinned'}], 'sfx': []},
		{'models': ['sets/urban/characters/npc/ped_male/models/ped_male.model'], 'dyes': [{'tint': 'Default', 'materialGroup': 'empty_skinned'}], 'sfx': []},
		{'models': ['sets/urban/characters/npc/ped_male/models/ped_male.model'], 'dyes': [{'tint': 'variant_c', 'materialGroup': 'empty_skinned'}], 'sfx': []},
		{'models': ['sets/urban/characters/npc/ped_male/models/ped_male.model'], 'dyes': [{'tint': 'variant_d', 'materialGroup': 'empty_skinned'}], 'sfx': []},
		{'models': ['sets/minspec/characters/avatars/barbarian/models/barbarian_body.model', 'sets/minspec/characters/avatars/barbarian/models/barbarian_head.model'], 'dyes': [], 'sfx': []},
		{'models': ['sets/minspec/characters/avatars/barbarian/models/barbarian_body.model', 'sets/minspec/characters/avatars/barbarian/models/barbarian_head_helmet.model', 'sets/minspec/characters/avatars/barbarian/models/helmet.model', 'sets/minspec/characters/avatars/barbarian/models/shoulder_armour.model'], 'dyes': [], 'sfx': []},
	]

# PlayerModel.py
