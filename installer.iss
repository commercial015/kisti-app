; Requires Inno Setup on Windows.
[Setup]
AppName=Kisti Hisab Professional
AppVersion=1.0.0
DefaultDirName={autopf}\KistiHisabProfessional
DefaultGroupName=Kisti Hisab Professional
OutputDir=installer
OutputBaseFilename=KistiHisabProfessional_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\KistiHisabProfessional.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Kisti Hisab Professional"; Filename: "{app}\KistiHisabProfessional.exe"
Name: "{commondesktop}\Kisti Hisab Professional"; Filename: "{app}\KistiHisabProfessional.exe"
