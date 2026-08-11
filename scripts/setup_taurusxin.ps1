#Requires -Version 5.1
<#
.SYNOPSIS
    Download and extract taurusxin/Ofd2Pdf Windows EXE into bin/.
.DESCRIPTION
    Fetches the latest stable release asset from GitHub and places
    Ofd2Pdf.exe under the project bin/ directory so that ofd2pdf can
    use the taurusxin backend.
#>
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $projectRoot "bin"
$zipPath = Join-Path $binDir "Ofd2Pdf_1.2.zip"
$exePath = Join-Path $binDir "Ofd2Pdf.exe"

New-Item -ItemType Directory -Force -Path $binDir | Out-Null

if (Test-Path $exePath) {
    Write-Host "Ofd2Pdf.exe already exists at $exePath"
    exit 0
}

$releaseUrl = "https://github.com/taurusxin/Ofd2Pdf/releases/download/1.2.0.0/Ofd2Pdf_1.2.zip"

Write-Host "Downloading $releaseUrl ..."
try {
    Invoke-WebRequest -Uri $releaseUrl -OutFile $zipPath -UseBasicParsing -MaximumRetryCount 3
} catch {
    Write-Error "Download failed: $_"
    exit 1
}

Write-Host "Extracting to $binDir ..."
Expand-Archive -Path $zipPath -DestinationPath $binDir -Force
Remove-Item $zipPath -Force

if (-not (Test-Path $exePath)) {
    # Some releases put the EXE inside a subfolder
    $nested = Get-ChildItem -Path $binDir -Recurse -Filter "Ofd2Pdf.exe" | Select-Object -First 1
    if ($nested) {
        Move-Item $nested.FullName $exePath -Force
    } else {
        Write-Error "Ofd2Pdf.exe not found after extraction"
        exit 1
    }
}

Write-Host "Ofd2Pdf.exe installed at $exePath"
Write-Host "Usage: ofd2pdf input.ofd -o output.pdf --backend taurusxin"
