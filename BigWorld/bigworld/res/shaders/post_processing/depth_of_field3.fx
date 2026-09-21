#include "post_processing.fxh"

DECLARE_EDITABLE_TEXTURE( inputTexture, inputSampler, CLAMP, CLAMP, LINEAR, "Input texture/render target" )
DECLARE_EDITABLE_TEXTURE( depthBlurTexture, depthBlurSampler, CLAMP, CLAMP, LINEAR, "Depth blur texture (calculated by a Lens Simulation effect)" )
DECLARE_EDITABLE_TEXTURE( blurTexture1, blur1Sampler, CLAMP, CLAMP, LINEAR, "Mild blur render target (calculated by the Multiblur effect)" )
DECLARE_EDITABLE_TEXTURE( blurTexture2, blur2Sampler, CLAMP, CLAMP, LINEAR, "Medium blur render target (calculated by the Multiblur effect)" )
DECLARE_EDITABLE_TEXTURE( blurTexture3, blur3Sampler, CLAMP, CLAMP, LINEAR, "Strong blur render target (calculated by the Multiblur effect)" )


float alpha
<
	bool artistEditable = true;
	float UIMin = 0;
	float UIMax = 1.0;
	int UIDigits = 2;
	string UIName = "Brightness";
	string UIDesc = "Brightness of the filter";
> = 1.0;


float overdrive
<
	float UIMin = 0.0;
	float UIMax = 5.0;
	int UIDigits = 2;
	bool artistEditable = true;
	string UIName = "Overdrive";
	string UIDesc = "Saturation overdrive of the filter";
> = 1.0;


//screenDimensions is (w,h,halfw,halfh)
float4 screenDimensions : Screen;

struct NTF_PS_INPUT
{
	float4 pos		: POSITION;
	float3 tc0		: TEXCOORD0;
	float2 invS		: TEXCOORD1;
};


NTF_PS_INPUT vs_main( VS_INPUT input )
{
	NTF_PS_INPUT o = (NTF_PS_INPUT)0;
	o.pos = input.pos.xyww;
	o.tc0 = input.tc0;
	o.invS.x = 1.0 / screenDimensions.x;
	o.invS.y = 1.0 / screenDimensions.y;
	return o;
};


float4 saturateRange( float4 val, float min, float max )
{
	val = saturate( val - min );
	val = saturate( val * 1.0 / (max - min) );
	return val;
}


float4 ps_main( NTF_PS_INPUT v ) : COLOR
{
	float4 bb = tex2D( inputSampler, v.tc0 );
	float2 centerDepthBlur = tex2D( depthBlurSampler, v.tc0 );
	float4 blur1 = tex2D( blur1Sampler, v.tc0 );
	float4 blur2 = tex2D( blur2Sampler, v.tc0 );
	float4 blur3 = tex2D( blur3Sampler, v.tc0 );
	
	centerDepthBlur.y = abs(centerDepthBlur.y);
	
	float b1amt = saturateRange( centerDepthBlur.y, 0.25, 0.5 );
	float b2amt = saturateRange( centerDepthBlur.y, 0.5, 0.75 );
	float b3amt = saturateRange( centerDepthBlur.y, 0.75, 1.0 );

	float4 finalColour;	
	finalColour.a = b1amt + b2amt + b3amt;
	finalColour.rgb = b1amt * blur1 + b2amt * blur2 + b3amt * blur3;
	finalColour.rgb *= overdrive;		//saturate the blurred scene
	finalColour.rgb /= finalColour.a;	//this shader is designed for use with SRCALPHA / INVSRCALPHA blending
										//dividing here, in case finalColour.a is 3, we don't want to over-saturate.
	finalColour.a = saturate(b1amt);	//fade in entire blur map by the end of b1amt's range.
	
	
	return finalColour;
};


STANDARD_PP_TECHNIQUE( compile vs_3_0 vs_main(), compile ps_3_0 ps_main() )
