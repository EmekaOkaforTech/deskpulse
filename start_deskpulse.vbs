' DeskPulse Windows Client Silent Launcher
' Runs completely hidden (no console, no window flash)

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get script directory
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Change to project directory
objShell.CurrentDirectory = strScriptDir

' Run pythonw.exe (no console) with Windows client
objShell.Run "pythonw.exe -m app.windows_client", 0, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing
