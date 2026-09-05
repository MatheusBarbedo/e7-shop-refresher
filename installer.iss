#define AppName "E7 Shop Refresher"
#define AppVersion "1.0.0"
#define AppPublisher "Matheus Barbedo"
#define AppExe "E7ShopRefresher.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=E7-Shop-Refresher_{#AppVersion}_x64-setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "dist\E7ShopRefresher\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "platform-tools\*"; DestDir: "{app}\platform-tools"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "tesseract\*"; DestDir: "{app}\tesseract"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "config.ini"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
