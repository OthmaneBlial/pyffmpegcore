param(
    [ValidateSet("Auto", "Pipx", "Pip")]
    [string]$Method = "Auto",
    [string]$PackageSpec = "",
    [string]$PythonCommand = "py",
    [switch]$SkipDoctor,
    [switch]$Help
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Usage {
    @"
Install PyFFmpegCore as a terminal command on Windows.

Usage:
  .\install.ps1 [-Method Auto|Pipx|Pip] [-PackageSpec VALUE] [-PythonCommand VALUE] [-SkipDoctor]

Examples:
  .\install.ps1
  .\install.ps1 -Method Pipx
  .\install.ps1 -PackageSpec .
"@ | Write-Host
}

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Resolve-PackageSpec {
    if ($PackageSpec) {
        return $PackageSpec
    }

    if ($env:PYFFMPEGCORE_PACKAGE_SPEC) {
        return $env:PYFFMPEGCORE_PACKAGE_SPEC
    }

    return "pyffmpegcore"
}

function Invoke-PipxInstall {
    param([Parameter(Mandatory = $true)][string]$Spec)
    if (-not (Test-Command "pipx")) {
        throw "pipx is not installed. Re-run with -Method Pip or install pipx first."
    }

    Write-Host "Installing $Spec with pipx"
    & pipx install --force $Spec
}

function Invoke-PipInstall {
    param(
        [Parameter(Mandatory = $true)][string]$Spec,
        [Parameter(Mandatory = $true)][string]$PythonExe
    )
    if (-not (Test-Command $PythonExe)) {
        throw "Python executable not found: $PythonExe"
    }

    Write-Host "Installing $Spec with $PythonExe -m pip --user"
    & $PythonExe -m pip install --user --upgrade $Spec
}

function Test-Install {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExe,
        [switch]$SkipDoctorCheck
    )

    if (Test-Command "pyffmpegcore") {
        & pyffmpegcore --version
        if (-not $SkipDoctorCheck) {
            try {
                & pyffmpegcore doctor
            } catch {
                Write-Warning $_
            }
        }
        return
    }

    Write-Warning "pyffmpegcore is not on PATH yet. Open a new shell if needed."
    if (Test-Command $PythonExe) {
        try {
            & $PythonExe -m pyffmpegcore --version
        } catch {
            Write-Warning $_
        }
    }
}

if ($Help) {
    Show-Usage
    exit 0
}

$resolvedSpec = Resolve-PackageSpec

if ($Method -eq "Auto") {
    if (Test-Command "pipx") {
        $Method = "Pipx"
    } else {
        $Method = "Pip"
    }
}

if ($Method -eq "Pipx") {
    Invoke-PipxInstall -Spec $resolvedSpec
} else {
    Invoke-PipInstall -Spec $resolvedSpec -PythonExe $PythonCommand
}

Test-Install -PythonExe $PythonCommand -SkipDoctorCheck:$SkipDoctor
