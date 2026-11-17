<#
  setup_env.ps1 - moves this project's Python env out of OneDrive.

  Run ONCE on EACH machine, from the project folder:
      powershell -ExecutionPolicy Bypass -File .\setup_env.ps1

  What it does (safe to re-run):
    1. Installs uv if missing
    2. Deletes the broken .venv inside the project (OneDrive)
    3. Creates a local venv at C:\venvs\dtprog (Python 3.12) - or repairs it if broken
    4. Installs requirements.txt + ifcopenshell, pandas, openpyxl, streamlit
       (adds any of those missing from requirements.txt)
    5. Verifies the imports work
    6. Points VS Code at the new interpreter (workspace file + .vscode\settings.json)
#>
param(
    [string]$VenvPath = "C:\venvs\dtprog",
    [string]$PythonVersion = "3.12"
)

$ErrorActionPreference = "Continue"
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "`n    ERROR: $m" -ForegroundColor Red; exit 1 }

$Py = Join-Path $VenvPath "Scripts\python.exe"
$Required = @("ifcopenshell", "pandas", "openpyxl", "streamlit")

# --- 0. No venv may be active -------------------------------------------------
if ($env:VIRTUAL_ENV) {
    Fail "A venv is active ($env:VIRTUAL_ENV). Type 'deactivate', then run this script again."
}

# --- 1. uv ------------------------------------------------------------------
Step "Checking uv"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Warn "uv not found - installing it"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail "uv install failed. Install it manually: https://docs.astral.sh/uv/getting-started/installation/"
    }
}
Ok (uv --version)

# --- 2. Delete old .venv in the project (OneDrive) -----------------------------
Step "Removing old .venv from project folder"
$OldVenv = Join-Path $ProjectDir ".venv"
if (Test-Path $OldVenv) {
    try {
        Remove-Item -Recurse -Force $OldVenv -ErrorAction Stop
        Ok "Deleted $OldVenv"
    } catch {
        Warn "Could not fully delete .venv (a file is in use). Close VS Code, delete the folder by hand later. Continuing."
    }
} else {
    Ok "None found"
}

# --- 3. Create / repair local venv ----------------------------------------------
Step "Local venv at $VenvPath"
$Healthy = $false
if (Test-Path $Py) {
    try {
        & $Py -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $Healthy = $true }
    } catch { }
}

if ($Healthy) {
    Ok "Exists and works - keeping it"
} else {
    if (Test-Path $VenvPath) {
        Warn "Exists but broken - recreating"
        Remove-Item -Recurse -Force $VenvPath
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $VenvPath) | Out-Null
    uv venv $VenvPath --python $PythonVersion
    if ($LASTEXITCODE -ne 0) { Fail "uv venv failed" }
    Ok "Created (Python $PythonVersion)"
}

# --- 4. Packages ------------------------------------------------------------
Step "Installing packages"
$Req = Join-Path $ProjectDir "requirements.txt"
if (-not (Test-Path $Req)) { New-Item -ItemType File -Path $Req | Out-Null }

# add required packages that requirements.txt doesn't mention yet
$ReqText = (Get-Content $Req -Raw)
if ($null -eq $ReqText) { $ReqText = "" }
$Added = @()
foreach ($pkg in $Required) {
    if ($ReqText -notmatch "(?im)^\s*$pkg\b") { $Added += $pkg }
}
if ($Added.Count -gt 0) {
    if ($ReqText.Length -gt 0 -and -not $ReqText.EndsWith("`n")) { Add-Content $Req "" }
    Add-Content $Req ($Added -join "`r`n")
    Warn "Added to requirements.txt: $($Added -join ', ')"
}

uv pip install --python $Py -r $Req
if ($LASTEXITCODE -ne 0) { Fail "Package install failed (see output above)" }
Ok "Done"

# --- 5. Verify ----------------------------------------------------------------
Step "Verifying imports"
& $Py -c "import ifcopenshell, pandas, openpyxl, streamlit; print('    ifcopenshell', ifcopenshell.version, '| pandas', pandas.__version__)"
if ($LASTEXITCODE -ne 0) { Fail "Import test failed" }

# --- 6. VS Code interpreter setting -------------------------------------------------
Step "Pointing VS Code at the new interpreter"

function Set-InterpreterSetting($file, [bool]$isWorkspaceFile) {
    $raw = Get-Content $file -Raw
    try { $json = $raw | ConvertFrom-Json -ErrorAction Stop } catch { $json = $null }
    if ($null -eq $json) {
        Warn "Couldn't parse $(Split-Path $file -Leaf) (comments in JSON?). Add this line by hand:"
        Warn "  `"python.defaultInterpreterPath`": `"$($Py -replace '\\','\\')`""
        return
    }
    $target = $json
    if ($isWorkspaceFile) {
        if ($null -eq $json.settings) { $json | Add-Member -NotePropertyName settings -NotePropertyValue ([pscustomobject]@{}) }
        $target = $json.settings
    }
    $target | Add-Member -Force -NotePropertyName "python.defaultInterpreterPath" -NotePropertyValue $Py
    $json | ConvertTo-Json -Depth 20 | Set-Content $file -Encoding UTF8
    Ok "Updated $(Split-Path $file -Leaf)"
}

$Ws = Get-ChildItem $ProjectDir -Filter *.code-workspace | Select-Object -First 1
if ($Ws) { Set-InterpreterSetting $Ws.FullName $true }

$VsSettings = Join-Path $ProjectDir ".vscode\settings.json"
if (Test-Path $VsSettings) { Set-InterpreterSetting $VsSettings $false }

if (-not $Ws -and -not (Test-Path $VsSettings)) {
    Warn "No workspace/settings file found - select the interpreter manually (see below)."
}

# --- Done -------------------------------------------------------------------
Write-Host "`nAll set." -ForegroundColor Green
Write-Host "  In VS Code: Ctrl+Shift+P -> 'Python: Select Interpreter' -> $Py (once per machine)"
Write-Host "  Activate in terminal: $VenvPath\Scripts\Activate.ps1"
Write-Host "  New package? uv pip install --python $Py <name>, add it to requirements.txt, re-run this script on the other PC."