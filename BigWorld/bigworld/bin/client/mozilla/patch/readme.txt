----------------------------------------------------------------------------------------------------------------------
**********************************************************************************************************************
----------------------------------------------------------------------------------------------------------------------
PLEASE Redistribute this directory as part of your game distribution as it is required for licensing issues when using llmozlib and mozilla.
----------------------------------------------------------------------------------------------------------------------
**********************************************************************************************************************
----------------------------------------------------------------------------------------------------------------------

BigWorld contains a mozilla and llmozlib redistribution.

Based on this software license we need to specify what changes were done to these libraries and when these changes were done.

Changes were done on the period between 12/01/2009-23/01/2009

1. minimal change were done to the mozilla source code changes include:
   a. llmozlib related changes: see http://svn.secondlife.com/trac/llmozlib/browser/trunk/llmozlib2/README-win32.txt
   b. changes in mozilla_diff.txt (mainly linden patch, removing all DebugBreak realated code and preventing some windows 	hook code from happening).
2. minimal changes were done to the llmozlib source code:
   a. Fixing the ubrowser to compile as ascii (this is not redistributed with our client exe but is provided here just in case)
   b. creating a dll wrapper using llmozlib (no source changes to the original files), but still the new files are attached:
	llmozlib_virtual_wrapper.h
	llmozlib_virtual_wrapper.cpp
	llmozlib_dll.h
	llmozlib_dll.cpp
   c. Preventing an Access Violation when rendering caret in llembeddedbrowser.cpp (available here as well)
   d. supporting flash mouse interaction in llembeddedbrowserwindow.cpp.

GECKO is written by the mozilla foundation see http://www.mozilla.org/


LLMozlib was written by Callum Prentice see http://ubrowser.com/

