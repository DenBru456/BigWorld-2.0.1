from controls import *

args = \
(
	WatcherCheckBox( "Show Friction", "Targeting/Show Friction" ),
	WatcherCheckBox( "Show Total Yaw", "Targeting/Show Total Yaw" ),
	WatcherCheckBox( "Show Forward Yaw", "Targeting/Show Forward Yaw" ),
	WatcherCheckBox( "Show Strafe Yaw", "Targeting/Show Strafe Yaw" ),
	WatcherCheckBox( "Show Turn Yaw", "Targeting/Show Turn Yaw" ),
	WatcherCheckBox( "Show Total Pitch", "Targeting/Show Total Pitch" ),
	Divider(),
	WatcherCheckBox( "Reverse Adhesion Style", "Targeting/Reverse Adhesion Style" ),
	WatcherFloatSlider( "Friction", "Targeting/Friction", (0, 2) ),
	WatcherFloatSlider( "Forward Adhesion", "Targeting/Forward Adhesion", (0, 1) ),
	WatcherFloatSlider( "Strafe Adhesion", "Targeting/Strafe Adhesion", (0, 2) ),
	WatcherFloatSlider( "Turn Adhesion", "Targeting/Turn Adhesion", (0, 4) ),
	WatcherFloatSlider( "Pitch/Yaw Adhesion Ratio", "Targeting/Adhesion Pitch::Yaw Ratio", (0, 1) ),
	WatcherIntSlider( "Yaw And Pitch Scale", "Targeting/Yaw&Pitch Scale", (0, 20) ),
	WatcherIntSlider( "Number Of Samples", "Targeting/Number of Samples", (1, 100) ),
)

commands = \
(
)