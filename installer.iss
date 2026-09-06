; Inno Setup script for Gab.
;
; Takes the PyInstaller output in dist\Gab and the model files in runtime\,
; and produces one installer that leaves a working app behind. Nothing is
; downloaded afterwards and there is nothing to sign into.

#define AppName "Gab"
#define AppVersion "0.1.0"
#define AppPublisher "Casen Clark"
#define AppExe "Gab.exe"

[Setup]
AppId={{7E4C1A96-2B3D-4F58-9E01-6A7B8C9D0E1F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Built to a roomier drive: the models make this a three gigabyte installer
; and the C: drive has no space to spare.
OutputDir=D:\GabBuild
OutputBaseFilename=GabSetup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; The models are already compressed, so squeezing harder costs minutes and
; saves almost nothing.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Start Gab when Windows starts"; GroupDescription: "Additional shortcuts:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; The application itself.
Source: "dist\Gab\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Gab\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; The models: the language model, the voice, speech recognition, the wake word.
; Taken from the project folder rather than from dist, so the build never has
; to hold a second three gigabyte copy.
Source: "runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start Gab now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\_internal"
