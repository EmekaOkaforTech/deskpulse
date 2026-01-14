; Inno Setup installer script for DeskPulse Standalone Windows Edition
; Requires Inno Setup 6: https://jrsoftware.org/isinfo.php
;
; Build command:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
;
; Output:
;   build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe
;
; Key Differences from Epic 7 Client:
;   - Bundles full backend (Flask, OpenCV, MediaPipe)
;   - Larger installer size: 150-250 MB (vs Epic 7: 60-100 MB)
;   - No Pi required, uses PC webcam
;   - Includes database (deskpulse.db) in user data

[Setup]
; Application information
AppName=DeskPulse Standalone Edition
AppVersion=2.0.0
AppPublisher=DeskPulse Team
AppPublisherURL=https://github.com/EmekaOkaforTech/deskpulse
AppSupportURL=https://github.com/EmekaOkaforTech/deskpulse/issues
AppUpdatesURL=https://github.com/EmekaOkaforTech/deskpulse/releases

; Installation directories
DefaultDirName={autopf}\DeskPulse
DefaultGroupName=DeskPulse
DisableProgramGroupPage=yes

; Output configuration (relative to .iss file location in build\windows)
OutputDir=Output
OutputBaseFilename=DeskPulse-Standalone-Setup-v2.0.0
Compression=lzma2/ultra64
SolidCompression=yes

; Expected installer size: 150-250 MB (compressed)
; Distribution size: 200-300 MB (uncompressed, full backend)

; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Visual style
WizardStyle=modern
SetupIconFile=..\..\assets\windows\icon_professional.ico
UninstallDisplayIcon={app}\DeskPulse.exe
UninstallDisplayName=DeskPulse Standalone Edition

; Privileges (admin required to install to Program Files)
PrivilegesRequired=admin

; Version info
VersionInfoVersion=2.0.0.0
VersionInfoCompany=DeskPulse Team
VersionInfoDescription=DeskPulse Standalone Edition Installer
VersionInfoCopyright=Copyright (C) 2026 DeskPulse Team
VersionInfoProductName=DeskPulse Standalone Edition
VersionInfoProductVersion=2.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Copy entire PyInstaller distribution (one-folder mode)
; Source: dist/DeskPulse-Standalone/ (from build_standalone.ps1)
Source: "..\..\dist\DeskPulse-Standalone\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcuts (inside DeskPulse folder)
Name: "{group}\DeskPulse"; Filename: "{app}\DeskPulse.exe"; Comment: "Launch DeskPulse Posture Monitor"
Name: "{group}\Uninstall DeskPulse"; Filename: "{uninstallexe}"; Comment: "Uninstall DeskPulse"

; Desktop shortcut (optional - user can select during install)
Name: "{commondesktop}\DeskPulse"; Filename: "{app}\DeskPulse.exe"; Tasks: desktopicon; Comment: "Launch DeskPulse Posture Monitor"

; Auto-start shortcut (optional - created only if user selects task)
Name: "{commonstartup}\DeskPulse"; Filename: "{app}\DeskPulse.exe"; Tasks: startupicon

[Tasks]
; Desktop shortcut option (checked by default for visibility)
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checked
; Auto-start option (unchecked by default - user opt-in)
Name: "startupicon"; Description: "Start DeskPulse automatically when Windows starts"; GroupDescription: "Startup Options:"; Flags: unchecked

[Run]
; Launch application after installation (user can uncheck)
Filename: "{app}\DeskPulse.exe"; Description: "Launch DeskPulse"; Flags: nowait postinstall skipifsilent

[Code]
{ User Data Preservation on Uninstall }
{ Standalone Edition: Includes configuration, database, and logs }
{ Best practice: Prompt user before deleting data }

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
  DialogResult: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { User data directory for Standalone Edition }
    ConfigDir := ExpandConstant('{userappdata}\DeskPulse');

    if DirExists(ConfigDir) then
    begin
      { Prompt user with detailed explanation }
      DialogResult := MsgBox(
        'Do you want to delete your configuration, database, and logs?' + #13#10 + #13#10 +
        'Location: ' + ConfigDir + #13#10 + #13#10 +
        'This includes:' + #13#10 +
        '  • Configuration (config.json)' + #13#10 +
        '  • Posture database (deskpulse.db)' + #13#10 +
        '  • Application logs (logs/)' + #13#10 + #13#10 +
        'If you plan to reinstall DeskPulse, choose "No" to keep your data.',
        mbConfirmation,
        MB_YESNO
      );

      if DialogResult = IDYES then
      begin
        { User chose to delete data }
        if DelTree(ConfigDir, True, True, True) then
        begin
          MsgBox('Configuration, database, and logs deleted successfully.', mbInformation, MB_OK);
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
          'Configuration, database, and logs preserved at:' + #13#10 +
          ConfigDir + #13#10 + #13#10 +
          'Your data will be available if you reinstall DeskPulse.',
          mbInformation,
          MB_OK
        );
      end;
    end;
  end;
end;
