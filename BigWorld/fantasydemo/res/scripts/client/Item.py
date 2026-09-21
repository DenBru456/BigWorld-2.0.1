import random
from functools import partial

import FantasyDemo
import BigWorld
import ItemBase
import Math
from Helpers import PSFX
from Helpers import Caps
from Helpers import BWKeyBindings
import traceback


ItemNumberList = ItemBase.ItemNumberList
price = ItemBase.price


# ------------------------------------------------------------------------------
# Class Item:
#
# The Item class is a base class for the items in the game. Each item contains
# game mechanic information but does not actually exist on its own in the game.
# An in-game item exists when it becomes part of a DroppedItem entity. An item
# can also exist as part of an entity's inventory.
# ------------------------------------------------------------------------------

class Item( ItemBase.ItemBase ):
	"TODO: Document"

	canShoot = 0
	canSwing = 0

	# --------------------------------------------------------------------------
	# Method: __init__
	# Description:
	#	- Loads all base-class data members.
	#	- Derived classes must call the base class __init__ method, supplying it
	#	  the derived class and its type.
	# --------------------------------------------------------------------------
	def __init__( self, child, itemType, prereqs = None ):
		methodName = "Item.__init__: "

		#
		# Check the itemType.
		#
		if not itemType in child.typeRange:
			raise AssertionError, methodName + "illegal item type."
		else:
			self.itemType = itemType

		#
		# Check the model name for the item.
		#
		if self.itemType in child.modelNames.keys():
			modelName = child.modelNames[ self.itemType ]
		else:
			modelName = child.modelNames[ child.UNKNOWN_TYPE ]
			print methodName + "itemType: " + \
				str( self.itemType ) + " has no corresponding model."

		#
		# Load the model for the item.
		#
		if modelName != None:
			if prereqs != None:
				try:
					self.model = prereqs.pop(modelName)
				except KeyError:
					traceback.print_stack()
					self.model = None
			else:
				self.model = BigWorld.Model(modelName)
			if self.model == None:
				print methodName + "failed to load model " + modelName
		else:
			self.model = None

		#
		# Check the display name for the item.
		#
		if not self.itemType in child.displayNames.keys():
			print methodName + "itemType: " + \
				str( self.itemType ) + " has no display name."
			self.displayName = child.displayNames[ child.UNKNOWN_TYPE ]
		else:
			self.displayName = child.displayNames[ self.itemType ]


	# --------------------------------------------------------------------------
	# Method: use
	# Description:
	#	- Uses the item.
	#	- This method is called by the local client for any entities controlled
	#	  by the client. Items know the conditions under which they can be
	#	  used. The logic for this is handled by this method.
	#	- Accepts a user (subject) and target (indirect object).
	# Note:
	#	If the item can't be used, or if it can't be used with the given target,
	#	then this function must return the value false. Otherwise, if it is
	#	used, it should return the value true. It should never return None.
	# --------------------------------------------------------------------------
	def use( self, user, target ):
		return 0


	# --------------------------------------------------------------------------
	# Method: enact
	# Description:
	#	- Acts out the use of the item.
	#	- This method is called by the local client for all entities when
	#	  wanting to know how to use the item. Items know the steps involved
	#	  in using itself and how to portray it to the game world. The logic
	#	  for this is handled by this method.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def enact( self, user, target ):
		pass


	# --------------------------------------------------------------------------
	# Method: enactIdle
	# Description:
	#	- Tells the item's model to begin its idle animation.
	#	- Any item model with an animation must have this called when it
	#	  enters the world as part of an Entity. This is because the models are
	#	  shared between Entities. If not, an instance will appear to have the
	#	  animation frame of the previous instance's action.
	# --------------------------------------------------------------------------
	def enactIdle( self, entity = None ):
		# Set up the entity's holding style if an entity was specified.
		if entity != None:
			if entity.model != None and entity.model.inWorld:
				try:
					entity.model.HoldUpright.stop()
				except:
					pass
		# Set up the Item's holding animation.
		if self.model != None and self.model.inWorld:
			try:
				self.model.Idle()
			except:
				pass


	def enactDrawn( self, entity = None ):
		self.enactIdle( entity )

	# --------------------------------------------------------------------------
	# Method: name
	# Description:
	#	- Returns a reference to the string containing the name of the Item.
	# --------------------------------------------------------------------------
	def name( self ):
		return self.displayName

	# Called by the player when it enters the 'using item' mode with this item
	def retain( self, owner ):
		pass

	# Called by the player when it exits the 'using item' mode with this item
	def release( self, owner ):
		pass

	# Called by anyone when they swap out the item
	def unequip( self, user ):
		pass

	def equipByPlayer( self, player ):
		"""Sets the target capabilities and gui icon and other stuff
		which should be set when the player equips this item"""

		if not player.inCombat():
			BigWorld.target.caps( Caps.CAP_CAN_USE )


	def glanceByPlayer( self, player ):
		"""Sets the gui icon and other stuff which should be set
		immediately after the player considers this item.
		equipByPlayer may not necessarily be called afterwards if it
		is switched through before the item is withdrawn"""

		# update gui
		player.itemGui.itemIcon.visible = 1
		player.itemGui.itemBack.visible = 1
		player.itemGui.itemIcon.textureName = Item.resolveIconName( self.itemType )


# ------------------------------------------------------------------------------
# Class Food:
#
# The Food class is a derived class representing all edible items in the game.
# It extends the use() and enact() methods for the Item class.
# ------------------------------------------------------------------------------

class Food(Item):
	# --------------------------------------------------------------------------
	# The different types of food are listed below. The value of ALLOWED_TYPE
	# should always be set to the highest value that the itemType can take.
	# --------------------------------------------------------------------------
	typeRange = xrange( 10, 19 )
	STRIFF_DRUMSTICK	= 11
	SPIDER_LEG			= 12
	WINE_GOBLET			= 13


	# --------------------------------------------------------------------------
	# The dictionary of food models is listed below. A model name is the name
	# of the file containing model information for drawing and animating
	# food in the game world.
	# --------------------------------------------------------------------------
	modelNames = {
		STRIFF_DRUMSTICK:	"sets/items/item_food_drumstick.model",
		SPIDER_LEG:			"characters/npc/spider/spider_leg.model",
		WINE_GOBLET:		"sets/items/grail.model"
	}


	# --------------------------------------------------------------------------
	# The dictionary of food names is listed below. A display name is the
	# default text displayed to the client when targeting food.
	# --------------------------------------------------------------------------
	displayNames = {
		STRIFF_DRUMSTICK:	"Striff Drumstick",
		SPIDER_LEG:			"Spider Leg",
		WINE_GOBLET:		"Wine Goblet"
	}


	# --------------------------------------------------------------------------
	# The dictionary of food icons is listed below. A GUI icon name is the
	# file containing the bitmap for food when selected in the GUI.
	# --------------------------------------------------------------------------
	guiIconNames = {
		STRIFF_DRUMSTICK:	"gui/maps/icon_items/icon_food_drumstick.tga",
		SPIDER_LEG:			"gui/maps/icon_items/icon_spider_leg.tga",
		WINE_GOBLET:		"gui/maps/icon_items/icon_grail.tga"
	}


	# --------------------------------------------------------------------------
	# Method: __init__
	# Description:
	#	- Overrides base-class data.
	#	- Sets all member data to sensible values.
	# --------------------------------------------------------------------------
	def __init__( self, itemType, prereqs = None ):
		# methodName = "Item.Food.__init__: "
		Item.__init__( self, Food, itemType, prereqs )

	# This method returns the basic prerequisites required for the item
	def prerequisites( itemType ):
		return [Food.modelNames[lookupItem(itemType)[1]]]

	prerequisites = staticmethod(prerequisites)

	# --------------------------------------------------------------------------
	# Method: use
	# Description:
	#	- Uses the food. This is an interface method defined by the Item
	#	  class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def use( self, user, target ):
		if target != None: return 0

		if not user.inCombat():
			# TBD: For now, this is being done for backwards compatibility
			# until Avatar is cleaned up.
			user.eat( self.itemType )
			user.cell.eat( self.itemType )
			# How can the user ever be in combat mode with a food item in hand??

		return 1

	# --------------------------------------------------------------------------
	# Method: enact
	# Description:
	#	- Acts out the use of the food. This is an interface method defined by
	#	  the Item class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def enact( self, user, target ):
		pass

	# --------------------------------------------------------------------------
	# Method: enactIdle
	# Description:
	#	- Tells the item's model to begin its idle animation.
	#	- Any item model with an animation must have this called when it
	#	  enters the world as part of an Entity. This is because the models are
	#	  shared between Entities. If not, an instance will appear to have the
	#	  animation frame of the previous instance's action.
	# --------------------------------------------------------------------------
	def enactIdle( self, entity = None ):
		# Set up the entity's holding style if an entity was specified.
		if entity != None:
			if entity.model != None and entity.model.inWorld:
				try:
					entity.model.Idle.stop()
					entity.model.HoldUpright()
				except:
					pass
		# Set up the Item's holding animation.
		if self.model != None and self.model.inWorld:
			try:
				self.model.Idle()
			except:
				pass

	# --------------------------------------------------------------------------
	# Method: setHoldingStyle
	# Description:
	#	- Sets the action matcher capabilities for a particular item. This
	#	  allows an Item to specify what type of idle is used when it is
	#	  equiped.
	# --------------------------------------------------------------------------
	def setHoldingStyle( self, entity ):
		entity.model.HoldUpright()



# ------------------------------------------------------------------------------
# Class Gadget:
#
# The Gadget class is a derived class representing a catch-all category of
# useful to semi-useful items in the game. The Gadget class extends the use()
# and enact() methods for the Item class.
# ------------------------------------------------------------------------------

class Gadget(Item):
	"TODO: Document"

	# --------------------------------------------------------------------------
	# The different types of gadgets are listed below. The value of
	# ALLOWED_TYPE should always be set to the highest value that the itemType
	# can take.
	# --------------------------------------------------------------------------
	typeRange = xrange(20,29)
	BINOCULARS			= 23


	# --------------------------------------------------------------------------
	# The dictionary of gadget models is listed below. A model name is the name
	# of the file containing model information for drawing and animating the
	# gun in the game world.
	# --------------------------------------------------------------------------
	modelNames = {
		BINOCULARS:			"sets/items/binocver2.model"
	}


	# --------------------------------------------------------------------------
	# The dictionary of gadget names is listed below. A display name is the
	# default text displayed to the client when targeting the gadget.
	# --------------------------------------------------------------------------
	displayNames = {
		BINOCULARS:			"Binoculars"
	}


	# --------------------------------------------------------------------------
	# The dictionary of gadget icons is listed below. A GUI icon name is the
	# file containing the bitmap for the gadget when selected in the GUI.
	# --------------------------------------------------------------------------
	guiIconNames = {
		BINOCULARS:			"gui/maps/icon_items/icon_tek_binoc2.tga"
	}


	class BinocularsActionHandler( BWKeyBindings.BWActionHandler ):

		def __init__( self, owner ):
			self.owner = owner
			BWKeyBindings.BWActionHandler.__init__( self )

		@BWKeyBindings.BWKeyBindingAction( "CameraKey" )
		def cameraKey( self, isDown ):
			if isDown:
				return True
			else:
				return False

		@BWKeyBindings.BWKeyBindingAction( "EscapeKey" )
		def escapeKey( self, isDown ):
			if isDown:
				owner = self.owner
				owner.binocularsMode( 0 ) # escape out of binoculars gui mode
				owner.setUsingCurrentItem( 0 )
				return True
			else:
				return False

	# --------------------------------------------------------------------------
	# Method: __init__
	# Description:
	#	- Overrides base-class data.
	#	- Sets all member data to sensible values.
	# --------------------------------------------------------------------------
	def __init__( self, itemType, prereqs = None ):
		Item.__init__( self, Gadget, itemType, prereqs )
		if self.itemType == Gadget.BINOCULARS:
			self.binocularsActionHandler = None

	# This method returns the basic prerequisites required for the item
	def prerequisites( itemType ):
		return [Gadget.modelNames[lookupItem(itemType)[1]]]

	prerequisites = staticmethod(prerequisites)

	# --------------------------------------------------------------------------
	# Method: use
	# Description:
	#	- Uses the gadget. This is an interface method defined by the Item
	#	  class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def use( self, user, target ):
		handled = 0
		if not user.inCombat():
			if self.itemType == Gadget.BINOCULARS:
				# TBD: For now, this is being done for backwards compatibility
				# until Avatar is cleaned up.
				#if target == None:
				user.setUsingCurrentItem( 1 )
				handled = 1

		return handled


	# --------------------------------------------------------------------------
	# Method: enact
	# Description:
	#	- Acts out the use of the gun. This is an interface method defined by
	#	  the Item class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def enact( self, user, target ):
		pass


	# Called by the player when it enters the 'using item' mode with this item
	def retain( self, owner ):
		if self.itemType == Gadget.BINOCULARS:
			owner.binocularsMode( 1 )
			self.binocularsActionHandler = Gadget.BinocularsActionHandler( owner )
			FantasyDemo.rds.keyBindings.addHandler( self.binocularsActionHandler )

	# Called by the player when it exits the 'using item' mode with this item
	def release( self, owner ):
		if self.itemType == Gadget.BINOCULARS:
			owner.binocularsMode( 0 )
			FantasyDemo.rds.keyBindings.removeHandler( self.binocularsActionHandler )
			self.binocularsActionHandler = None


	# --------------------------------------------------------------------------
	# Method: equipByPlayer
	# Description:
	#	- Sets the target capabilities and gui icon and other stuff
	#		which should be set when the player equips this item
	# --------------------------------------------------------------------------
	#def equipByPlayer( self, player ):
	#	print "Gadget.equipByPlayer", self, player
	#	Item.equipByPlayer( self, player )



# ------------------------------------------------------------------------------
# Class Wield:
#
# The Wield class is a derived class representing all weildable items in the
# game. It extends the use() and enact() methods for the Item class.
# ------------------------------------------------------------------------------

class Wield(Item):
	typeRange = xrange( 30, 39 )
	SWORD_BASTARD			= 31
	SWORD_BASTARD_MITHRIL	= 32

	maximumSparks = 10
	minimumSparks =  5

	# swords (wield) can swing
	canSwing = 1

	modelNames = {
		SWORD_BASTARD:			"sets/items/sword_bastard.model",
		SWORD_BASTARD_MITHRIL:	"sets/items/sword_bastard.model",
	}

	dyeNames = {
		SWORD_BASTARD:			[("Blade","Default"), ("Flat","Default")],
		SWORD_BASTARD_MITHRIL:	[("Blade","Mithril"), ("Flat","Mithril")],
	}


	displayNames = {
		SWORD_BASTARD:			"Fine Bastard Sword",
		SWORD_BASTARD_MITHRIL:	"Mithril Bastard Sword",
	}


	guiIconNames = {
		SWORD_BASTARD:			"gui/maps/icon_items/icon_sword_bastard.tga",
		SWORD_BASTARD_MITHRIL:	"gui/maps/icon_items/icon_sword_bastard_mithril.tga",
	}


	# --------------------------------------------------------------------------
	# Method: __init__
	# Description:
	#	- Overrides base-class data.
	#	- Sets all member data to sensible values.
	# --------------------------------------------------------------------------
	def __init__( self, itemType, prereqs = None ):
		# methodName = "Item.Wield.__init__: "
		Item.__init__( self, Wield, itemType, prereqs )

		try:
			for dye in Wield.dyeNames[ itemType ]:
				setattr( self.model, dye[0], dye[1] )
		except:
			pass

	# This method returns the basic prerequisites required for the item
	def prerequisites( itemType ):
		return [Wield.modelNames[lookupItem(itemType)[1]]]

	prerequisites = staticmethod(prerequisites)

	# --------------------------------------------------------------------------
	# Method: use
	# Description:
	#	- Wields this item. This is an interface method defined by the Item
	#	  class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def use( self, user, target ):
		#user.closeCombatCommence( self, target )

		if BigWorld.player() is user:
			try:
				user.playGesture( 46 )
			except AttributeError:
				pass

		return 1

	# --------------------------------------------------------------------------
	# Method: enact
	# Description:
	#	- Acts out the use of the wield. This is an interface method defined
	#	  by the Item class.
	#	- Accepts a user (subject) and target (indirect object).
	# --------------------------------------------------------------------------
	def enact( self, user, target ):
		target

		# delay swing noise till the 2nd half of animation
		# BigWorld.playFxDelayed("sword/med/swish", 0.334, user.position)
		user.model.SwingSword();


	# --------------------------------------------------------------------------
	# Method: createSparks
	# Description:
	#	- Helper method to create sparks from the sword.
	# --------------------------------------------------------------------------
	def createSparks( self ):
		numSparks = random.random() * ( Wield.maximumSparks -
			Wield.minimumSparks ) + Wield.minimumSparks
		PSFX.attachSparks( self.model, None, numSparks )


from Staff import Staff

# ------------------------------------------------------------------------------
# Method: resolveIconName
# Description:
#	- returns the icon name for the item class if one exists
# ------------------------------------------------------------------------------
def resolveIconName( itemType ):
	methodName = "resolveIconName"
	itemTup = lookupItem( itemType )

	if itemTup == None:
		print methodName + "itemType: " + \
			str( itemType ) + " is not an item."
		return ""
	else:
		itemClass = itemTup[0]
		itemID = itemTup[1]

		if itemID in itemClass.guiIconNames.keys():
			return itemClass.guiIconNames[ itemID ]
		else:
			print methodName + "itemType: " + \
				str( itemID ) + " has no GUI Icon."
			return itemClass.guiIconNames[ itemClass.UNKNOWN_TYPE ]


# ------------------------------------------------------------------------------
# Method: newItem
# Description:
#	- Creates a new Item when supplied with an item type.
#	- The itemType supplied is the old-style item value. This method is for
#	  compatibility with the old-style code until new-style revolution takes
#	  over.
#	- Now if we have prerequisites, and the item constructor accepts them,
#	  we pass them in.  Support legacy constructor for now as well.
# ------------------------------------------------------------------------------
def newItem( itemType, prereqs = None ):
	r = lookupItem( itemType )
	if not r:
		#~ print "Item.newItem: lookup for", itemType, "failed"
		#~ import traceback
		#~ traceback.print_stack()
		return None
	return r[0]( r[1], prereqs )


# This dictionary maps an old item type to the new item class and class subtype
oldItemTypeDict = {
	Item.STAFF_TYPE:			( Staff,		Staff.SNAKE ),
	Item.STAFF_TYPE_2:			( Staff,		Staff.LIGHTNING ),
	Item.DRUMSTICK_TYPE:		( Food,		Food.STRIFF_DRUMSTICK )	,
	Item.SPIDER_LEG_TYPE:		( Food,		Food.SPIDER_LEG )	,
	Item.BINOCULARS_TYPE:		( Gadget,	Gadget.BINOCULARS ),
	Item.SWORD_TYPE:			( Wield,		Wield.SWORD_BASTARD ),
	Item.SWORD_TYPE_2:			( Wield,		Wield.SWORD_BASTARD_MITHRIL ),
	Item.GOBLET_TYPE:			( Food,		Food.WINE_GOBLET ),
}

# This method returns information for this old-style item type
# The info is the class and the new-style item type
def lookupItem( itemType ):
	try:
		return oldItemTypeDict[ itemType ]
	except:
		return None



# ------------------------------------------------------------------------------
# A Helper class to load an item in the loading thread.
#
# When the callbackFn is called, self.resourceRefs holds the necessary resources
# for the item's construction.
# ------------------------------------------------------------------------------
class LoadBG:
	def __init__( self, itemNo, callbackFn ):
		self.itemNo = itemNo
		self.resourceRefs = None
		self.itemTypeDict = lookupItem(itemNo)
		if not self.itemTypeDict:
			if callbackFn != None:
				callbackFn( self )
			return

		self.itemType = self.itemTypeDict[0]
		self.callbackFn = callbackFn
		if hasattr( self.itemType, "prerequisites" ):
			resourceList = tuple(set(self.itemType.prerequisites(itemNo)))
			BigWorld.loadResourceListBG( resourceList, self.onLoad, 128 )
		else:
			if self.callbackFn != None:
				self.callbackFn( self )
				self.callbackFn = None

	def onLoad( self, resourceRefs ):
		self.resourceRefs = resourceRefs
		if self.callbackFn != None:
			self.callbackFn( self )
			self.callbackFn = None


# ------------------------------------------------------------------------------
# A static method which is called to get a list of preload resources.
# ------------------------------------------------------------------------------
def Item_preload( list ):
	pass


def giveGuns():
	pass

def giveSwords():
	BigWorld.player().inventory += [
		Item.SWORD_TYPE,
		Item.SWORD_TYPE_2,
		]

def giveAll():
	BigWorld.player().inventory += [
		Item.STAFF_TYPE	,
		Item.STAFF_TYPE_2	,
		Item.DRUMSTICK_TYPE	,
		Item.BINOCULARS_TYPE,
		Item.SWORD_TYPE		,
		Item.SWORD_TYPE_2	,
		Item.GOBLET_TYPE	,
		]

#Item.py
