# This module contains constant data associated with the Merchant entity type.

import ResMgr
import AvatarModel
import ItemBase

AVATAR_MODE_DATA = None
MERCHANT_ITEMS = None

def init():
	global AVATAR_MODEL_DATA
	global MERCHANT_ITEMS

	AVATAR_MODEL_DATA = AvatarModel.pack( {
		'models':[	'characters/avatars/ranger/ranger_body.model',
					'characters/avatars/ranger/ranger_head.model'],
		'dyes':[	{'materialGroup':'Head_skinned', 'tint':'Merchant'},
					{'materialGroup':'Hair_skinned', 'tint':'Merchant'},
					{'materialGroup':'chrome_eyes_skinned', 'tint':'Merchant'},
					{'materialGroup':'Single_material_skinned', 'tint':'Merchant'},
					{'materialGroup':'ArmSkin_skinned', 'tint':'Merchant'},
					{'materialGroup':'GloveMetal_skinned', 'tint':'Merchant'},
					{'materialGroup':'chrome_legs_skinned', 'tint':'Merchant'},
					{'materialGroup':'Legs_skinned', 'tint':'Merchant'}],
		'sfx':[] } )

	MERCHANT_ITEMS = set([
							ItemBase.ItemBase.STAFF_TYPE,
							ItemBase.ItemBase.STAFF_TYPE_2,
							ItemBase.ItemBase.DRUMSTICK_TYPE,
							#ItemBase.ItemBase.SPIDER_LEG_TYPE,
							ItemBase.ItemBase.BINOCULARS_TYPE,
							ItemBase.ItemBase.SWORD_TYPE,
							ItemBase.ItemBase.SWORD_TYPE_2,
							ItemBase.ItemBase.GOBLET_TYPE,
							])

MIN_STOCK = 1
MAX_STOCK = 1

init()
