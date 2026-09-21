@echo Please examine settings below and modify if necessary
cd %~dp0
set MF_ROOT=%~dp0..\..\..
set BW_RES_PATH=%MF_ROOT%\fantasydemo\res;%MF_ROOT%\bigworld\res
@if exist main.py (python main.py) else (python main.pyc)
pause
