'''This module contains constant data associated with the Guard entity type.
'''

import ResMgr
import AvatarModel
import CustomisableModel

# Guard Type Enumerations
HIGHLANDS_GUARD = 0
URBAN_GUARD = 1
MINSPEC_GUARD = 2


GUARD_TYPES = {
	HIGHLANDS_GUARD:'Highlands Guard',
	URBAN_GUARD:'Urban Guard',
	MINSPEC_GUARD:'Minspec Guard'
}

GUARD_SHOWNAMES = {
	HIGHLANDS_GUARD:'Guard',
	URBAN_GUARD:'Pedestrian',
	MINSPEC_GUARD:'Guard',
}

GUARD_MODELS = {}

def load():
	for model in CustomisableModel.load( ResMgr.openSection( "scripts/data/guard_model_data.xml" ) ):
		try:
			GUARD_MODELS[GUARD_TYPES.values().index( model.name )] = model
		except ValueError:
			print "ASSET ERROR: Base model '%s' not in GUARD_TYPES" % model.name

	for guardType in GUARD_TYPES:
		if guardType not in GUARD_MODELS:
			print "ASSET ERROR: No base model in guard_model_data.xml for guard type '%s'" % guardType

load()
