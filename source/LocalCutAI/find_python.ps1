$ErrorActionPreference = 'SilentlyContinue'
$candidates = New-Object 'System.Collections.Generic.List[string]'

function Add-Candidate([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    $Path = [Environment]::ExpandEnvironmentVariables($Path.Trim().Trim('"'))
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        if (-not $candidates.Contains($Path)) { [void]$candidates.Add($Path) }
    }
}

# First, inspect paths known to the Python Launcher (works even when PATH is not set).
$launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($launcher) {
    $launcherLines = & $launcher.Source -0p 2>$null
    foreach ($line in $launcherLines) {
        if ($line -match '([A-Za-z]:\\.*?python\.exe)\s*$') { Add-Candidate $Matches[1] }
    }
}

# Look in standard registry locations for Python 3.12 / 3.11.
foreach ($version in @('3.12', '3.11')) {
    $keys = @(
        "HKCU:\Software\Python\PythonCore\$version\InstallPath",
        "HKLM:\Software\Python\PythonCore\$version\InstallPath",
        "HKLM:\Software\WOW6432Node\Python\PythonCore\$version\InstallPath"
    )
    foreach ($keyPath in $keys) {
        $key = Get-Item -LiteralPath $keyPath -ErrorAction SilentlyContinue
        if ($key) {
            $exe = $key.GetValue('ExecutablePath')
            if ($exe) { Add-Candidate $exe }
            $folder = $key.GetValue('')
            if ($folder) { Add-Candidate (Join-Path $folder 'python.exe') }
        }
    }
}

# Check standard per-user / all-users install locations.
foreach ($path in @(
    "$env:LocalAppData\Programs\Python\Python312\python.exe",
    "$env:LocalAppData\Programs\Python\Python311\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "$env:ProgramFiles\Python311\python.exe",
    "$env:SystemDrive\Python312\python.exe",
    "$env:SystemDrive\Python311\python.exe"
)) { Add-Candidate $path }

# Finally, inspect executables available through PATH (ignore Microsoft Store aliases unless valid).
Get-Command 'python.exe' -All -ErrorAction SilentlyContinue | ForEach-Object { Add-Candidate $_.Source }
Get-Command 'python' -All -ErrorAction SilentlyContinue | ForEach-Object { Add-Candidate $_.Source }

# Accept only a real 64-bit Python 3.11 or 3.12 installation.
foreach ($candidate in $candidates) {
    & $candidate -c 'import sys,struct; raise SystemExit(0 if sys.version_info[:2] in ((3,11),(3,12)) and struct.calcsize(chr(80))*8 == 64 else 1)' 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Output $candidate
        exit 0
    }
}
exit 1
