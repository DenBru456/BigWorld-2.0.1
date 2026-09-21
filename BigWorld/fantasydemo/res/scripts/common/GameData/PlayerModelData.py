'''The module contains data about available player models and their posible
customisations. All models and their customisations (dyes etc.) are required
to be present in the AvatarModelData module.
'''

import ResMgr
import AvatarModelData
import CustomisableModel

PLAYER_MODELS = None

def init():
	global PLAYER_MODELS
	PLAYER_MODELS = CustomisableModel.load( ResMgr.openSection( "scripts/data/player_model_data.xml" ) )

init()
