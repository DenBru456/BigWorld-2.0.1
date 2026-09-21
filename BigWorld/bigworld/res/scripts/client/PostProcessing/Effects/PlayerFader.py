import BigWorld
from PostProcessing.RenderTargets import *
from PostProcessing import Effect
from PostProcessing.Phases import *
from PostProcessing.Effects import implementEffectFactory


@implementEffectFactory( "Player fader", "Fade out the player when they get too close to the camera." )
def playerFader():
	'''This method creates and returns a post-process effect that fades
	out the player when they get too close to the camera.
	This effect only works in the client, as there is no player in the tools.'''
	
	backBufferCopy = rt("backBufferCopy")
	
	e = Effect()
	e.name = "Player Fader"
	
	try:
		from _PostProcessing import PlayerFader
		p = PlayerFader()
	except:
		p = None
		
	if p is not None:
		c = buildBackBufferCopyPhase(backBufferCopy)

		p.renderTarget = backBufferCopy	#draw player over the offscreen bb
		p.clearRenderTarget = False
		p.name = "Player Fader"

		t = buildTransferPhase( backBufferCopy.texture, BW_BLEND_SRCALPHA, BW_BLEND_INVSRCALPHA )
		t.material.alphaOverdrive = 255.0
		t.material.alpha = p.opacity
		t.material.alphaTestEnable = True
		t.material.alphaReference = 1		

		e.bypass = p.opacity
		e.phases = [c,p,t]
	else:
		e.phases = []
	
	return e


#PlayerFader effects placed in the WorldEditor end up being saved as an
#empty effect, since the PlayerFader phase is not linked into the tools
#(see above factory method).  So we need to listen at pre-chain change
#level and instantiate the correct phases where appropriate.
def instantiatePlayerFader(ch):
	if ch != None:
		for e in ch:
			if e.name == "Player Fader":
				pf = playerFader()
				e.phases = pf.phases
				e.bypass = pf.bypass
	return True

from PostProcessing import preChainListeners
preChainListeners.append( instantiatePlayerFader )