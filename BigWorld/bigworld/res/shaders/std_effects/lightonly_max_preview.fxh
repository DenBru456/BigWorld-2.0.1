#include "max_preview_include.fxh"

//Vertex Shader for lightonly
#if DUAL_UV

sampler diffuseSampler = BW_SAMPLER(diffuseMap, WRAP)
sampler diffuseSampler2 = BW_SAMPLER(diffuseMap2, WRAP)

OutputDiffuseLighting vs_max( VertexXYZNUV2 i )

#elif VERTEX_COLOURS

sampler diffuseSampler = BW_SAMPLER(diffuseMap, WRAP)
OutputDiffuseLighting vs_max( VertexXYZNUV i )

#else
sampler diffuseSampler = BW_SAMPLER(diffuseMap, WRAP)
OutputDiffuseLighting vs_max( VertexXYZNUV i )
#endif
{
	OutputDiffuseLighting o = (OutputDiffuseLighting)0;
	o.pos = mul( i.pos, worldViewProj );
	o.tcDepth.xy = i.tc;
#if DUAL_UV
	o.tc2 = i.tc2;
#endif
	o.sunlight.xyz = float3(0.1, 0.1, 0.1) + selfIllumination;
	
	float3 lDir = normalize(mul( lightDir, worldInverse ));
	
#ifdef MOD2X
	o.sunlight.xyz += saturate(dot( lDir, i.normal )) * lightColour * 0.5 * (1 + diffuseLightExtraModulation);
#else
	o.sunlight += saturate(dot( lDir, i.normal )) * lightColour;
#endif
	o.sunlight.w = 1;
	return o;
}

#if DUAL_UV
float4 ps_max( OutputDiffuseLighting input ) : COLOR0
{
	float4 diffuseMap1 = tex2D( diffuseSampler, input.tcDepth.xy );	
	float4 diffuseMap2 = tex2D( diffuseSampler2, input.tc2.xy );

	float4 diffuseMap = float4( diffuseMap1.rgb*(1-diffuseMap2.a) + diffuseMap2.rgb*(diffuseMap2.a), diffuseMap1.a );

	float4 colour;
	colour = (input.sunlight + input.diffuse) * diffuseMap;
	colour.w = diffuseMap.w;
 	return colour;
}

#elif VERTEX_COLOURS

float4 ps_max( OutputDiffuseLighting input ) : COLOR0
{

	float4 diffuseMap = tex2D( diffuseSampler, input.tcDepth.xy );
	float4 colour;
	colour = (input.sunlight + input.diffuse) * diffuseMap;
	colour.w = diffuseMap.w;
 	return colour;
}

#else

float4 ps_max( OutputDiffuseLighting input ) : COLOR0
{
	float4 diffuseMap = tex2D( diffuseSampler, input.tcDepth.xy );
	float4 colour;
	colour = input.sunlight * diffuseMap;
	colour.w = diffuseMap.w;
 	return colour;
}

#endif
