#ifndef MAX_PREVIEW_INCLUDE_FXH
#define MAX_PREVIEW_INCLUDE_FXH

// This value is there so that the bool check boxes work properly.
string ParamID = "0x0001";

//-----------------------------------------
// Includes for ALL max preview effects.
//-----------------------------------------

// 3d studio max lighting values
float4 lightDir : Direction 
<
string UIName = "Light Direction";
string Object = "TargetLight";
int RefID = 0;
> = {-0.577, -0.577, 0.577,1.0};

float4 lightColour : LightColor 
<
int LightRef = 0;
> = float4( 1.0f, 1.0f, 1.0f, 1.0f );    // diffuse

#if DUAL_UV
// same as the macro but with some extra max specific info.
texture diffuseMap
<
	bool artistEditable = true;
	string UIName = "Diffuse Map";
	string UIDesc = "The diffuse map for the material";
	int Texcoord = 0;
	int MapChannel = 1;
>;

texture diffuseMap2
<
	bool artistEditable = true;
	string UIName = "Diffuse Map2";
	string UIDesc = "The diffuse map2 for the material";
	int Texcoord = 1;
	int MapChannel = 2;
>;
#else
BW_ARTIST_EDITABLE_DIFFUSE_MAP
#endif
BW_ARTIST_EDITABLE_SELF_ILLUMINATION
BW_ARTIST_EDITABLE_MOD2X
BW_ARTIST_EDITABLE_DOUBLE_SIDED
BW_ARTIST_EDITABLE_ALPHA_TEST
BW_ARTIST_EDITABLE_ADDRESS_MODE(BW_WRAP)

#include "unskinned_effect_include.fxh"

float4x4 worldInverse : WorldI;
float4x4 viewInverse  : ViewI;
float4x4 worldViewProj : WorldViewProjection;
float4x4 worldView : WorldView;
float4x4 worldViewInverse : WorldViewI;


#endif //MAX_PREVIEW_INCLUDE_FXH