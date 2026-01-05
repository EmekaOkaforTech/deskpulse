; Inno Setup installer script for DeskPulse Windows desktop client
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php
;
; Build command:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer.iss
;
; Output:
;   build/windows/Output/DeskPulse-Setup-v1.0.0.exe

[Setup]
; Application information
AppName=DeskPulse
AppVersion=1.0.0
AppPublisher=DeskPulse Team
AppPublisherURL=http://192.168.10.126:2221/Emeka/deskpulse
AppSupportURL=http://192.168.10.126:2221/Emeka/deskpulse/issues
AppUpdatesURL=http://192.168.10.126:2221/Emeka/deskpulse/releases

; Installation directories
DefaultDirName={autopf}\DeskPulse
DefaultGroupName=DeskPulse
DisableProgramGroupPage=yes

; Output configuration
OutputDir=build\windows\Output
OutputBaseFilename=DeskPulse-Setup-v1.0.0
Compression=lzma2/ultra64
SolidCompression=yes

; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Visual style
WizardStyle=modern
SetupIconFile=assets\windows\icon.ico
UninstallDisplayIcon={app}\DeskPulse.exe
UninstallDisplayName=DeskPulse

; Privileges (admin required to install to Program Files)
PrivilegesRequired=admin

; Version info
VersionInfoVersion=1.0.0.0
VersionInfoCompany=DeskPulse Team
VersionInfoDescription=DeskPulse Windows Desktop Client Installer
VersionInfoCopyright=Copyright (C) 2026 DeskPulse Team
VersionInfoProductName=DeskPulse
VersionInfoProductVersion=1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Copy entire PyInstaller distribution
Source: "..\..\dist\DeskPulse\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcuts
Name: "{group}\DeskPulse"; Filename: "{app}\DeskPulse.exe"
Name: "{group}\Uninstall DeskPulse"; Filename: "{uninstallexe}"

; Auto-start shortcut (created only if user selects the task)
Name: "{userstartup}\DeskPulse"; Filename: "{app}\DeskPulse.exe"; Tasks: startupicon

[Tasks]
; Auto-start option (unchecked by default - user opt-in)
Name: "startupicon"; Description: "Start DeskPulse automatically when Windows starts"; GroupDescription: "Startup Options:"; Flags: unchecked

[Run]
; Launch application after installation (user can uncheck)
Filename: "{app}\DeskPulse.exe"; Description: "Launch DeskPulse"; Flags: nowait postinstall skipifsilent

[Code]
{ User Data Preservation on Uninstall }
{ Best practice: Prompt user before deleting config and logs }

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
  DialogResult: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { Check if user data directory exists }
    ConfigDir := ExpandConstant('{userappdata}\DeskPulse');

    if DirExists(ConfigDir) then
    begin
      { Prompt user with detailed explanation }
      DialogResult := MsgBox(
        'Do you want to delete your configuration and logs?' + #13#10 + #13#10 +
        'Location: ' + ConfigDir + #13#10 + #13#10 +
        'This includes:' + #13#10 +
        '  • Backend URL configuration (config.json)' + #13#10 +
        '  • Application logs (logs/)' + #13#10 + #13#10 +
        'If you plan to reinstall DeskPulse, choose "No" to keep your settings.',
        mbConfirmation,
        MB_YESNO
      );

      if DialogResult = IDYES then
      begin
        { User chose to delete data }
        if DelTree(ConfigDir, True, True, True) then
        begin
          MsgBox('Configuration and logs deleted successfully.', mbInformation, MB_OK);
        end
        else
        begin
          MsgBox(
            'Failed to delete some files in:' + #13#10 +
            ConfigDir + #13#10 + #13#10 +
            'You may need to delete them manually.',
            mbError,
            MB_OK
          );
        end;
      end
      else
      begin
        { User chose to preserve data }
        MsgBox(
          'Configuration and logs preserved at:' + #13#10 +
          ConfigDir + #13#10 + #13#10 +
          'Your settings will be available if you reinstall DeskPulse.',
          mbInformation,
          MB_OK
        );
      end;
    end;
  end;
end;
