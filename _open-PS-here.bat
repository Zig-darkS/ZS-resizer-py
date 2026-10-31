@echo off
set "CurrentDir=%~dp0"
for %%I in ("%CurrentDir:~0,-1%") do set "FolderName=%%~nxI"
powershell -NoExit -Command "$host.ui.RawUI.WindowTitle = '%FolderName%'; Clear-Host"
