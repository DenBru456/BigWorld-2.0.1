// include file for adapting rt/shader created .fx files

#include "stdinclude.fxh"

BW_SPECULAR_LIGHTING

float2x3 LightArray(		
		uniform int nDirectionals,
		float4 surfPos,
		float3 surfNorm,
		float4 eyePos,
		float specPow)
{
	float2x3 illum = float2x3(0, 0, 0, 0, 0, 0);	
	float3 eyeVec = normalize(eyePos.xyz-surfPos);
	if (nDirectionals != 0)
	{
		for (int i = 0;i<nDirectionals; i = (i+1))
		{
			float3 lightVect = specularDirectionalLights[i].direction;
			float3 halfVec = normalize(lightVect+eyeVec);
			float NdotL = dot(lightVect, surfNorm);
			float NdotH = dot(surfNorm, halfVec);
			float4 l = lit(NdotL, NdotH, specPow);
			illum[0] = (illum[0]+(l.y*specularDirectionalLights[i].colour.xyz));
			illum[1] = (illum[1]+(l.z*specularDirectionalLights[i].colour.xyz));
		}
	}
	else
	{
		// Use a constant light direction and light colour if there are no
		// directional lights so that we can show off the toon shader indoors
		float3 lightVect = float3(-0.568456, 0.821450, 0.045586);
		float3 colour = float3( 241.0 / 255.0, 209.0 / 255.0, 160.0 / 255.0 );

		float3 halfVec = normalize(lightVect+eyeVec);
		float NdotL = dot(lightVect, surfNorm);
		float NdotH = dot(surfNorm, halfVec);
		float4 l = lit(NdotL, NdotH, specPow);
		illum[0] = (illum[0]+(l.y * colour));
		illum[1] = (illum[1]+(l.z * colour));
	}
	return illum;
}