/******************************************************************************
BigWorld Technology 
Copyright BigWorld Pty, Ltd.
All Rights Reserved. Commercial in confidence.

WARNING: This computer program is protected by copyright law and international
treaties. Unauthorized use, reproduction or distribution of this program, or
any portion of this program, may result in the imposition of civil and
criminal penalties as provided by law.
******************************************************************************/

#include "../../llmozlib_virtual_wrapper.h"
#define FROM_WITHIN
#include "llmozlib_dll.h"

static LLMozlibVirtualWrapper* pObj = NULL;

extern "C" LLMozlibVirtualWrapper* getInstance()
{
	if (pObj == NULL)
	{
		pObj = new LLMozlibVirtualWrapper;
	}
	return pObj;
}

extern "C" void deleteInstance()
{
	delete pObj;
	pObj = NULL;
}
