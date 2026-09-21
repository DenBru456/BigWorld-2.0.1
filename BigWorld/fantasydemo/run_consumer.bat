@ECHO OFF

REM Note that --res parameters are relative to the executable itself.
start ..\bigworld\bin\client\bwclient_consumer.exe --res %~dp0\res;..\..\res
