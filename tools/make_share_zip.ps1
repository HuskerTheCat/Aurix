# Wrap the installer and its note into one zip for sending to a tester.
#
# Stored, not compressed: the installer is already LZMA-compressed, so
# squeezing it again costs many minutes and saves almost nothing. The zip
# exists because chat and email services refuse a bare .exe, not to save space.

Add-Type -AssemblyName System.IO.Compression.FileSystem

$source = "D:\GabShare"
$target = "D:\Gab-for-testing.zip"

if (Test-Path $target) { Remove-Item $target -Force }

[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $source,
    $target,
    [System.IO.Compression.CompressionLevel]::NoCompression,
    $false
)

$size = (Get-Item $target).Length / 1GB
Write-Output ("DONE: {0} is {1:N2} GB" -f $target, $size)
