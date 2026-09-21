#include "post_processing.fxh"

//Explicit Lens Simulation

DECLARE_EDITABLE_TEXTURE( inputTexture, inputSampler, CLAMP, CLAMP, LINEAR, "Input texture/render target" )

USES_DEPTH_TEXTURE


float falloff
<
	bool artistEditable = true;
	float UIMin = 0;
	float UIMax = 10.0;
	int UIDigits = 1;
	string UIDesc = "How quickly it becomes out of focus";
> = 2.0;


float nearFalloff
<
	bool artistEditable = true;
	float UIMin = 0;
	float UIMax = 100.0;
	int UIDigits = 1;
	string UIDesc = "How quickly it becomes in focus";
> = 50.0;


float zNear
<
	bool artistEditable = true;
	float UIMin = 0;
	float UIMax = 0.1;
	int UIDigits = 4;
	string UIDesc = "Near focal distance";
> = 0.0;


float zFar
<
	bool artistEditable = true;
	float UIMin = 0;
	float UIMax = 1.0;
	int UIDigits = 4;
	string UIDesc = "Far focal distance";
> = 0.5;


struct NTF_PS_INPUT
{
	float4 pos		: POSITION;
	float3 tc0		: TEXCOORD0;
};


NTF_PS_INPUT vs_main( VS_INPUT input )
{
	NTF_PS_INPUT o = (NTF_PS_INPUT)0;
	o.pos = input.pos.xyww;
	o.tc0 = input.tc0;
	return o;
};


float4 ps_main( NTF_PS_INPUT v ) : COLOR
{
	//calculate depth of pixel and blur amount
	float4 dSample = tex2D( depthSampler, v.tc0 );
	float sceneDepth = colour4ToFloat(dSample);
	
	float downSlope = min(0, (sceneDepth-zNear) * nearFalloff);
	float upSlope = max(0, (sceneDepth-zFar) * falloff);
	float blurAmount = downSlope + upSlope;

	float4 result = float4( sceneDepth, blurAmount, 0, 0);
	return result;
};


float4 ps_preview( NTF_PS_INPUT v ) : COLOR
{
	//calculate depth of pixel and blur amount
	float4 dSample = tex2D( depthSampler, v.tc0 );
	float sceneDepth = colour4ToFloat(dSample);
	float downSlope = min(0, (sceneDepth-zNear) * nearFalloff);
	float upSlope = max(0, (sceneDepth-zFar) * falloff);
	float blurAmount = downSlope + upSlope;
	float4 result = float4( -downSlope, upSlope, 0, 1);
	return result;
};


STANDARD_PP_TECHNIQUE( compile vs_3_0 vs_main(), compile ps_3_0 ps_main() )
STANDARD_PREVIEW_TECHNIQUE( compile vs_3_0 vs_main(), compile ps_3_0 ps_preview() )