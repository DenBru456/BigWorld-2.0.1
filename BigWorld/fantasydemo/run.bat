@ECHO OFF

REM Note that --res parameters are relative to the executable itself.
start ..\bigworld\bin\client\bwclient.exe --res %~dp0\res;..\..\res
