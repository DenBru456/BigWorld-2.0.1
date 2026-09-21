from controls import *

envSetup = \
"""
t = None
"""

args = \
(
	CheckBox( "Blur_Effect_Enabled",
		updateCommand = "",
		
		setCommand = """
		if Blur_Effect_Enabled and t == None: import Button; t = Button.TestTeleportBlur();
		if Blur_Effect_Enabled and not Blur_Amount == None: t.setBlurAmount(Blur_Amount)
		if not Blur_Effect_Enabled: t.setBlurAmount(0.0); t.killTeleportBlur(); t = None
		""",
		),
		
	FloatSlider( "Blur_Amount",
	
		updateCommand = "",
		
		setCommand = """
		if not t == None: t.setBlurAmount(Blur_Amount)
		""",
		
		minMax = (0.0, 1.0)
		),
)

commands = \
(
)