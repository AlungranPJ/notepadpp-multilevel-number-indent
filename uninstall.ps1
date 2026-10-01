# Multilevel Number Indent for Notepad++ : uninstaller
# Removes everything install.ps1 added. The PythonScript plugin stays, because
# other scripts may use it; remove it in Plugins > Plugins Admin if you want.
#   irm https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/uninstall.ps1 | iex

$ErrorActionPreference = 'Stop'
$Section = 'Multilevel list section'
$MenuItems = @('Reset numbering', 'Add numbering', 'Remove numbering', 'Clear formatting', 'Tidy up list',
    'Convert to numbered list', 'Change list level', 'Number headings', 'Remove heading numbers', 'Copy as plain text',
    'Numbering keys on or off')
$Utf8 = New-Object System.Text.UTF8Encoding($false)

try {
    if (Get-Process notepad++ -ErrorAction SilentlyContinue) {
        $a = if ($env:MNI_YES -eq '1') { 'y' } else { Read-Host '  Notepad++ is open and has to be closed first. Close it now? [Y/n]' }
        if ($a -match '^[nN]') { throw 'Close Notepad++ and run the uninstaller again.' }
        Get-Process notepad++ | ForEach-Object { [void]$_.CloseMainWindow() }
        for ($i = 0; $i -lt 120 -and (Get-Process notepad++ -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Milliseconds 500 }
        if (Get-Process notepad++ -ErrorAction SilentlyContinue) { throw 'Notepad++ is still open.' }
    }
    $userDir = Join-Path $env:APPDATA 'Notepad++'
    $config = Join-Path $userDir 'plugins\config'
    $scripts = Join-Path $config 'PythonScript\scripts'

    $startup = Join-Path $scripts 'startup.py'
    if (Test-Path $startup) {
        $t = [IO.File]::ReadAllText($startup)
        $t = [regex]::Replace($t, '(?s)\r?\n?# --- Multilevel Number Indent \(start\) ---.*?# --- Multilevel Number Indent \(end\) ---\r?\n?', "`n")
        [IO.File]::WriteAllText($startup, $t, $Utf8)
    }
    $cnf = Join-Path $config 'PythonScriptStartup.cnf'
    if (Test-Path $cnf) {
        $lines = @([IO.File]::ReadAllText($cnf) -split "\r?\n" | Where-Object {
                $_ -ne '' -and -not ($_ -like 'ITEM/*' -and $MenuItems -contains [IO.Path]::GetFileNameWithoutExtension($_.Substring(5)))
            })
        [IO.File]::WriteAllText($cnf, (($lines -join "`n") + "`n"), $Utf8)
    }
    $menu = Join-Path $userDir 'contextMenu.xml'
    if (Test-Path $menu) {
        $x = [IO.File]::ReadAllText($menu)
        $x = [regex]::Replace($x, '\s*<Item [^>]*FolderName="' + [regex]::Escape($Section) + '"[^>]*/>', '')
        $x = [regex]::Replace($x, '\s*<!-- Multilevel Number Indent -->\s*<Item id="0"\s*/>', '')
        [IO.File]::WriteAllText($menu, $x, $Utf8)
    }
    foreach ($n in $MenuItems + @('mni_npp')) { Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $scripts "$n.py") }
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $config 'MultilevelNumberIndent')
    Write-Host '  Multilevel Number Indent removed. Backups (*.mni-backup) were left in place.' -ForegroundColor Green
} catch { Write-Host "  $($_.Exception.Message)" -ForegroundColor Red }
