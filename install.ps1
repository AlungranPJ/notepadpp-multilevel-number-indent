# Multilevel Number Indent for Notepad++ : installer
#
# Double-click install.cmd in the downloaded folder, or paste this into PowerShell:
#   irm https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/install.ps1 | iex
#
# What it does, in order:
#   1. finds Notepad++ and asks to close it (it rewrites its settings on exit)
#   2. finds Node.js, or offers to install it with winget
#   3. installs the PythonScript 3 plugin if it is missing (one admin prompt)
#   4. copies the engine and scripts into your Notepad++ settings folder
#   5. adds the menu entries and the right-click "Multilevel list section"
# Every Notepad++ file it edits is copied to <name>.mni-backup first.
# Set $env:MNI_YES = '1' to answer yes to every question.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo = 'AlungranPJ/notepadpp-multilevel-number-indent'
$PythonScriptTag = 'v3.0.27'
$PythonScriptVersion = '3.0.27.0'
$Section = 'Multilevel list section'
$ContextItems = @('Reset numbering', 'Add numbering', 'Remove numbering', 'Clear formatting', 'Tidy up list',
    'Convert to numbered list', 'Change list level', 'Number headings', 'Remove heading numbers', 'Copy as plain text')
$MenuItems = $ContextItems + @('Numbering keys on or off')
$Utf8 = New-Object System.Text.UTF8Encoding($false)

$script:TempDirs = @()
function NewTemp($prefix) {
    $d = Join-Path $env:TEMP ($prefix + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory $d | Out-Null
    $script:TempDirs += $d
    return $d
}
function Say($m) { Write-Host "  $m" }
function Step($m) { Write-Host ''; Write-Host "> $m" -ForegroundColor Magenta }
function Fail($m) { throw [System.Exception]::new($m) }
function Ask($q, $defaultYes) {
    if ($env:MNI_YES -eq '1') { return $true }
    $hint = if ($defaultYes) { '[Y/n]' } else { '[y/N]' }
    $a = Read-Host "  $q $hint"
    if ($defaultYes) { return ($a -notmatch '^[nN]') }
    return ($a -match '^[yY]')
}
function ReadText($p) { return [IO.File]::ReadAllText($p) }
function WriteText($p, $t) { [IO.File]::WriteAllText($p, $t, $Utf8) }
function Backup($p) { if ((Test-Path $p) -and -not (Test-Path "$p.mni-backup")) { Copy-Item $p "$p.mni-backup" } }

function Find-Npp {
    foreach ($k in 'HKLM:\SOFTWARE\Notepad++', 'HKLM:\SOFTWARE\WOW6432Node\Notepad++', 'HKCU:\SOFTWARE\Notepad++') {
        $v = (Get-ItemProperty $k -ErrorAction SilentlyContinue).'(default)'
        if ($v -and (Test-Path (Join-Path $v 'notepad++.exe'))) { return $v }
    }
    foreach ($d in "$env:ProgramFiles\Notepad++", "${env:ProgramFiles(x86)}\Notepad++") {
        if (Test-Path (Join-Path $d 'notepad++.exe')) { return $d }
    }
    $running = Get-Process notepad++ -ErrorAction SilentlyContinue | Select-Object -First 1
    try { if ($running -and $running.Path) { return (Split-Path $running.Path) } } catch { }
    return $null
}

function Get-Arch($exe) {
    $fs = [IO.File]::OpenRead($exe)
    try {
        $b = New-Object byte[] 4096
        [void]$fs.Read($b, 0, 4096)
    } finally { $fs.Close() }
    $pe = [BitConverter]::ToInt32($b, 0x3C)
    switch ([BitConverter]::ToUInt16($b, $pe + 4)) {
        0x14c { return 'x86' }
        0xAA64 { return 'arm64' }
        default { return 'x64' }
    }
}

# Notepad++ keeps settings next to the exe only for a portable copy outside Program Files.
function Get-UserDir($npp) {
    $inProgramFiles = $npp.StartsWith($env:ProgramFiles, 'OrdinalIgnoreCase') -or
        (${env:ProgramFiles(x86)} -and $npp.StartsWith(${env:ProgramFiles(x86)}, 'OrdinalIgnoreCase'))
    if ((Test-Path (Join-Path $npp 'doLocalConf.xml')) -and -not $inProgramFiles) { return $npp }
    return (Join-Path $env:APPDATA 'Notepad++')
}

function Close-Npp {
    if (-not (Get-Process notepad++ -ErrorAction SilentlyContinue)) { return }
    Say 'Notepad++ is open. It rewrites its settings when it closes, so it has to be closed first.'
    if (-not (Ask 'Close it now? Unsaved files will ask you first.' $true)) { Fail 'Close Notepad++ and run the installer again.' }
    Get-Process notepad++ | ForEach-Object { [void]$_.CloseMainWindow() }
    for ($i = 0; $i -lt 120 -and (Get-Process notepad++ -ErrorAction SilentlyContinue); $i++) { Start-Sleep -Milliseconds 500 }
    if (Get-Process notepad++ -ErrorAction SilentlyContinue) { Fail 'Notepad++ is still open (maybe a save dialog). Close it and run the installer again.' }
    Say 'closed'
}

# Prefer a Node.js the user installed (Program Files, winget, nvm, PATH) over
# private copies that other apps ship for themselves and may delete on update.
function Find-Node {
    $candidates = @("$env:ProgramFiles\nodejs\node.exe")
    $candidates += @(Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS*\*\node.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | ForEach-Object { $_.FullName })
    if ($env:NVM_SYMLINK) { $candidates += Join-Path $env:NVM_SYMLINK 'node.exe' }
    $onPath = @(Get-Command node -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    $private = '\\(hermes|cursor|code|microsoft vs code|jetbrains|electron)[^\\]*\\'
    $candidates += @($onPath | Where-Object { $_ -notmatch $private }) + @($onPath | Where-Object { $_ -match $private })
    foreach ($c in $candidates) { if ($c -and (Test-Path $c)) { return $c } }
    return $null
}

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Runs a short script as admin (one UAC prompt), or directly when already elevated.
function Invoke-Elevated($script) {
    if (Test-Admin) { & ([scriptblock]::Create($script)); return }
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("`$ErrorActionPreference='Stop'; $script"))
    try {
        $p = Start-Process powershell -Verb RunAs -Wait -PassThru -WindowStyle Hidden -ArgumentList '-NoProfile', '-EncodedCommand', $enc
    } catch { Fail 'The admin prompt was declined, so PythonScript could not be copied into Notepad++.' }
    if ($p.ExitCode -ne 0) { Fail "The admin step failed (exit code $($p.ExitCode))." }
}

function Q($s) { return "'" + $s.Replace("'", "''") + "'" }

function Get-Package {
    $here = $PSScriptRoot
    if ($here -and (Test-Path (Join-Path $here 'server\mni-server.js'))) { return $here }
    Step 'Downloading Multilevel Number Indent'
    $tmp = NewTemp 'mni-npp-'
    $zip = Join-Path $tmp 'package.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing "https://github.com/$Repo/releases/latest/download/npp-multilevel-number-indent.zip" -OutFile $zip
    Expand-Archive $zip $tmp
    $dir = Get-ChildItem $tmp -Directory | Select-Object -First 1
    Say "downloaded to $($dir.FullName)"
    return $dir.FullName
}

function Install-PythonScript($npp) {
    $dir = Join-Path $npp 'plugins\PythonScript'
    $dll = Join-Path $dir 'PythonScript.dll'
    if (Test-Path $dll) {
        $v = (Get-Item $dll).VersionInfo.FileVersion
        if ($v -and $v.StartsWith('3')) { Say "PythonScript $v is already installed"; return }
        Say "PythonScript $v runs Python 2 and cannot run this. It will be replaced with $PythonScriptVersion (your own scripts are kept)."
    }
    $arch = Get-Arch (Join-Path $npp 'notepad++.exe')
    $suffix = @{ x64 = '_x64'; x86 = ''; arm64 = '_arm64' }[$arch]
    $name = "PythonScript_Full_${PythonScriptVersion}${suffix}_PluginAdmin.zip"
    Say "downloading $name ($arch Notepad++)"
    $tmp = NewTemp 'mni-ps-'
    $zip = Join-Path $tmp $name
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing "https://github.com/bruderstein/PythonScript/releases/download/$PythonScriptTag/$name" -OutFile $zip
    $out = Join-Path $tmp 'PythonScript'
    Expand-Archive $zip $out
    if (-not (Test-Path (Join-Path $out 'PythonScript.dll'))) { Fail "$name does not contain PythonScript.dll" }
    Say 'copying it into the Notepad++ plugins folder (Windows asks for admin once)'
    Invoke-Elevated ("if (Test-Path {0}) {{ Remove-Item -Recurse -Force {0} }}; Copy-Item -Recurse -Force {1} {0}" -f (Q $dir), (Q $out))
    if (-not (Test-Path $dll)) { Fail 'PythonScript was not copied.' }
    Say "PythonScript $PythonScriptVersion installed"
}

function Install-Files($src, $userDir, $node) {
    $config = Join-Path $userDir 'plugins\config'
    $mni = Join-Path $config 'MultilevelNumberIndent'
    $scripts = Join-Path $config 'PythonScript\scripts'
    New-Item -ItemType Directory -Force $mni, $scripts | Out-Null
    foreach ($f in 'mni-server.js', 'mni-core.js', 'CORE_VERSION') { Copy-Item -Force (Join-Path $src "server\$f") $mni }
    Copy-Item -Force (Join-Path $src 'pythonscript\mni_npp.py') $scripts
    Get-ChildItem (Join-Path $src 'pythonscript\commands') -Filter *.py | Copy-Item -Destination $scripts -Force

    $settingsPath = Join-Path $mni 'settings.json'
    $existing = $null
    if (Test-Path $settingsPath) {
        try { $existing = ReadText $settingsPath | ConvertFrom-Json -ErrorAction Stop } catch {
            Say 'settings.json could not be read; saving it as settings.json.damaged and writing a fresh one'
            Copy-Item -Force $settingsPath "$settingsPath.damaged"
        }
    }
    if ($existing -and $existing -is [pscustomobject]) {
        if (-not $existing.node -or -not (Test-Path $existing.node) -or ($existing.node -match '\\hermes\\' -and $node -notmatch '\\hermes\\')) {
            $existing | Add-Member -Force -NotePropertyName node -NotePropertyValue $node
            WriteText $settingsPath ($existing | ConvertTo-Json)
        }
        Say 'kept your settings.json'
        if ($existing.enabled -eq $false) { Say 'note: "enabled" is false in settings.json, so the number keys are off (Plugins > Python Script > Scripts > Numbering keys on or off)' }
    } else {
        $s = [ordered]@{ enabled = $true; node = $node; formats = @('1.', '1.1.', '1.1.1.', '1)', '1.1)', '1.1.1)') }
        WriteText $settingsPath ($s | ConvertTo-Json)
    }

    # startup.py: one marked block that hooks the editor when Notepad++ starts
    $startup = Join-Path $scripts 'startup.py'
    $body = if (Test-Path $startup) { ReadText $startup } else { "from Npp import *`n" }
    Backup $startup
    $body = [regex]::Replace($body, '(?s)\r?\n?# --- Multilevel Number Indent \(start\) ---.*?# --- Multilevel Number Indent \(end\) ---\r?\n?', '')
    $snippet = ReadText (Join-Path $src 'pythonscript\startup_snippet.py')
    WriteText $startup ($body.TrimEnd("`r", "`n") + "`n" + $snippet)

    # PythonScriptStartup.cnf: the menu entries, and start PythonScript with Notepad++
    $cnf = Join-Path $config 'PythonScriptStartup.cnf'
    Backup $cnf
    $lines = if (Test-Path $cnf) { @((ReadText $cnf) -split "\r?\n" | Where-Object { $_ -ne '' }) } else { @() }
    $lines = @($lines | Where-Object {
            -not ($_ -like 'SETTING/STARTUP/*') -and
            -not ($_ -like 'ITEM/*' -and $MenuItems -contains [IO.Path]::GetFileNameWithoutExtension($_.Substring(5)))
        })
    $lines += $MenuItems | ForEach-Object { "ITEM/\$_.py" }
    $lines += 'SETTING/STARTUP/ATSTARTUP'
    WriteText $cnf (($lines -join "`n") + "`n")
    return $mni
}

function Install-ContextMenu($userDir) {
    $path = Join-Path $userDir 'contextMenu.xml'
    if (-not (Test-Path $path)) {
        Say 'contextMenu.xml is not there yet: open Notepad++ once, close it, and run the installer again to get the right-click menu.'
        return
    }
    Backup $path
    $xml = ReadText $path
    $xml = [regex]::Replace($xml, '\s*<Item [^>]*FolderName="' + [regex]::Escape($Section) + '"[^>]*/>', '')
    $xml = [regex]::Replace($xml, '\s*<!-- Multilevel Number Indent -->\s*<Item id="0"\s*/>', '')
    $items = "`n        <!-- Multilevel Number Indent -->`n        <Item id=`"0`" />"
    foreach ($n in $ContextItems) {
        $items += "`n        <Item FolderName=`"$Section`" PluginEntryName=`"Python Script`" PluginCommandItemName=`"$n`" />"
    }
    $i = $xml.LastIndexOf('</ScintillaContextMenu>')
    if ($i -lt 0) { Say 'contextMenu.xml has no ScintillaContextMenu section; skipped the right-click menu.'; return }
    WriteText $path ($xml.Substring(0, $i).TrimEnd() + $items + "`n    " + $xml.Substring($i))
}

function Main {
    Write-Host ''
    Write-Host 'Multilevel Number Indent for Notepad++' -ForegroundColor Cyan

    Step 'Finding Notepad++'
    $npp = Find-Npp
    if (-not $npp) { Fail 'Notepad++ was not found. Install it from https://notepad-plus-plus.org first.' }
    $userDir = Get-UserDir $npp
    $ver = (Get-Item (Join-Path $npp 'notepad++.exe')).VersionInfo.ProductVersion
    Say "Notepad++ $ver in $npp"
    if (-not (Test-Path (Join-Path $userDir 'config.xml'))) { Fail 'Open Notepad++ once and close it, so it creates its settings, then run the installer again.' }
    Close-Npp

    Step 'Finding Node.js'
    $node = Find-Node
    if (-not $node) {
        Say 'Node.js runs the numbering engine and was not found.'
        if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Ask 'Install Node.js LTS with winget now?' $true)) {
            winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
            $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
            $node = Find-Node
        }
        if (-not $node) { Fail 'Install Node.js LTS from https://nodejs.org, then run the installer again.' }
    }
    $nodeVersion = (& $node --version).Trim()
    if ([int]($nodeVersion.TrimStart('v').Split('.')[0]) -lt 18) { Fail "Node.js $nodeVersion is too old; 18 or newer is needed." }
    Say "Node.js $nodeVersion ($node)"

    $src = Get-Package

    Step 'PythonScript plugin'
    Install-PythonScript $npp

    Step 'Copying the engine and scripts'
    $mni = Install-Files $src $userDir $node
    $check = (& $node (Join-Path $mni 'mni-server.js') --check 2>&1 | Out-String).Trim()
    if ($check -notmatch '"handled":true') { Fail "The engine did not answer: $check" }
    Say "engine OK: $check"

    Step 'Right-click menu'
    Install-ContextMenu $userDir
    Say "added '$Section'"

    Write-Host ''
    Write-Host 'Done. Open Notepad++, type "1. " in a .txt or .md file and press Enter or Tab.' -ForegroundColor Green
    Say "Settings: $(Join-Path $mni 'settings.json')"
    Say "Log:      $(Join-Path $mni 'mni.log')"
}

try { Main } catch { Write-Host ''; Write-Host "  $($_.Exception.Message)" -ForegroundColor Red } finally {
    foreach ($d in $script:TempDirs) { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $d }
}
