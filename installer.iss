; Inno Setup script for Gab.
;
; The installer carries the app, the voice, the speech model and the wake
; word - about 500 MB, which fits under GitHub's 2 GB release limit. The
; language model is nearly 3 GB and is downloaded during installation
; instead. The person still does nothing but run this.

#define AppName "Gab"
#define AppVersion "0.2.0"
#define AppPublisher "Casen Clark"
#define AppExe "Gab.exe"

#define ModelFile "Qwen3.5-4B-UD-Q4_K_XL.gguf"
#define ModelUrl "https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-UD-Q4_K_XL.gguf"
#define ModelSha "b252c5610a42ca82d20fe2a12813e9d069eed89292907e26c783eeb0bc961bc7"

[Setup]
AppId={{7E4C1A96-2B3D-4F58-9E01-6A7B8C9D0E1F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=D:\GabBuild
OutputBaseFilename=GabSetup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExe}
; Roughly 500 MB of installer plus a 2.8 GB download.
ExtraDiskSpaceRequired=2912109728

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Start Gab when Windows starts"; GroupDescription: "Additional shortcuts:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\Gab\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Gab\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Everything in runtime except the language model, which arrives by download.
Source: "runtime\*"; DestDir: "{app}\runtime"; Excludes: "models\*"; Flags: ignoreversion recursesubdirs createallsubdirs
; The downloaded model, already sitting in the temporary folder by this point.
Source: "{tmp}\{#ModelFile}"; DestDir: "{app}\runtime\models"; Flags: external ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start Gab now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\_internal"

[Code]
var
  Downloader: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then
    Downloader.SetText(
      'Downloading the language model...',
      Format('%.0f MB of %.0f MB', [Progress / 1048576.0, ProgressMax / 1048576.0]));
  Result := True;
end;

procedure InitializeWizard;
begin
  Downloader := CreateDownloadPage(
    'Downloading the language model',
    'Gab needs a language model, about 2.8 GB. This is the only download, and'
    + ' it happens once. Everything else is already in this installer.',
    @OnDownloadProgress);
end;

{ The download happens here rather than on a wizard button, because a silent
  install never presses one - which would leave an installed app with no
  language model and no explanation. PrepareToInstall runs either way, and
  returning a message from it stops the install and shows that message. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  Downloader.Clear;
  { The hash is verified for us. A truncated model would otherwise fail much
    later in some baffling way, instead of here where it can be explained. }
  Downloader.Add('{#ModelUrl}', '{#ModelFile}', '{#ModelSha}');

  if not WizardSilent then
    Downloader.Show;
  try
    try
      Downloader.Download;
    except
      Result :=
        'The language model could not be downloaded.'#13#10#13#10
        + AddPeriod(GetExceptionMessage) + #13#10#13#10
        + 'Check your internet connection and run this installer again.';
    end;
  finally
    if not WizardSilent then
      Downloader.Hide;
  end;
end;
