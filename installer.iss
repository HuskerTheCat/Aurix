; The installer carries the app, the voice, the speech model and the wake
; word. The language model is downloaded during installation, which keeps
; this file small enough for a GitHub release.

#define AppName "Aurix"
#define AppVersion "0.3.0"
#define AppPublisher "Casen Clark"
#define AppExe "Aurix.exe"

#define ModelFile "Qwen3.5-4B-UD-Q4_K_XL.gguf"
#define ModelUrl "https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/main/Qwen3.5-4B-UD-Q4_K_XL.gguf"
#define ModelSha "b252c5610a42ca82d20fe2a12813e9d069eed89292907e26c783eeb0bc961bc7"
#define ModelBytes "2912109728"

[Setup]
AppId={{7E4C1A96-2B3D-4F58-9E01-6A7B8C9D0E1F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=D:\AurixBuild
OutputBaseFilename=AurixSetup-{#AppVersion}
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExe}
; Space for the downloaded model.
ExtraDiskSpaceRequired=2912109728

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Start Aurix when Windows starts"; GroupDescription: "Additional shortcuts:"
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\Aurix\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Aurix\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "runtime\*"; DestDir: "{app}\runtime"; Excludes: "models\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{tmp}\{#ModelFile}"; DestDir: "{app}\runtime\models"; Flags: external ignoreversion; Check: NeedsModelDownload

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start Aurix now"; Flags: nowait postinstall skipifsilent

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
    'Aurix needs a language model, about 2.8 GB. This is the only download, and'
    + ' it happens once. Everything else is already in this installer.',
    @OnDownloadProgress);
end;

function NeedsModelDownload(): Boolean;
var
  Installed: String;
  ExistingSize: Int64;
begin
  Result := True;
  Installed := ExpandConstant('{app}\runtime\models\{#ModelFile}');
  if FileExists(Installed) then
    if FileSize64(Installed, ExistingSize) then
      Result := ExistingSize <> Int64({#ModelBytes});
end;

{ Not on a wizard button: a silent install never presses one, and would end up
  with no model and no explanation. PrepareToInstall runs either way. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';

  if not NeedsModelDownload() then
  begin
    Log('The language model is already installed. Skipping the download.');
    Exit;
  end;

  Downloader.Clear;
  { The hash is verified, so a truncated model fails here rather than later. }
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
