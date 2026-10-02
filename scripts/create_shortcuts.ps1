# Creates "Patent-Assistent" shortcuts on the desktop and in the start menu.
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "start.bat"
$shell = New-Object -ComObject WScript.Shell

$folders = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("Programs")
)

foreach ($folder in $folders) {
    $shortcut = $shell.CreateShortcut((Join-Path $folder "Patent-Assistent.lnk"))
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $root
    $shortcut.WindowStyle = 7          # 7 = start minimized
    $shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,111"
    $shortcut.Description = "Patent-Assistent starten"
    $shortcut.Save()
}