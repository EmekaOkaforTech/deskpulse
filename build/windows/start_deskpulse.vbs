' DeskPulse Windows Client Silent Launcher
' Runs the standalone DeskPulse.exe completely hidden

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get script directory
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Change to installation directory
objShell.CurrentDirectory = strScriptDir

' Run DeskPulse.exe (standalone executable, no console)
objShell.Run """" & strScriptDir & "\DeskPulse.exe""", 0, False

' Clean up
Set objShell = Nothing
Set objFSO = Nothing
