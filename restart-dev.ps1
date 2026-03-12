<#
.SYNOPSIS
    Manage the kith dev stack (backend, frontend, Inngest) on Windows.
.DESCRIPTION
    Native Windows PowerShell equivalent of restart-dev.sh.
    Starts/stops/restarts backend (FastAPI/uvicorn), frontend (Vite),
    and Inngest dev server. PID files are stored in .run\, logs in .logs\.
.PARAMETER Action
    start | stop | restart | status  (default: restart)
.EXAMPLE
    .\restart-dev.ps1 restart
    .\restart-dev.ps1 status
.NOTES
    Environment overrides (same as the .sh):
      KITH_CONDA_EXE, KITH_CONDA_ENVS_DIR, KITH_CONDA_ENV,
      KITH_FALLBACK_CONDA_ENV, KITH_BACKEND_PYTHON,
      KITH_USE_INNGEST_DEV_SERVER, KITH_FLYCTL_EXE,
      BACKEND_PORT, FRONTEND_PORT, INNGEST_PORT
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("start","stop","restart","status")]
    [string]$Action = "restart",

    [switch]$WslShutdown   # accepted for CLI parity; no-op on native Windows
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ─────────────────────────────────────────────────────────────────────
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir  = Join-Path $RootDir ".run"
$LogDir  = Join-Path $RootDir ".logs"

# ── Helper: return $a if non-empty, else $b ───────────────────────────────────
function Use-Default { param($a, $b); if ($a) { $a } else { $b } }

# ── Config (with env-var overrides) ──────────────────────────────────────────
$BackendPort       = Use-Default $env:BACKEND_PORT  "8000"
$FrontendPort      = Use-Default $env:FRONTEND_PORT "5173"
$InngestPort       = Use-Default $env:INNGEST_PORT  "8288"
$PreferredCondaEnv = Use-Default $env:KITH_CONDA_ENV "kith_venv"
$FallbackCondaEnv  = Use-Default $env:KITH_FALLBACK_CONDA_ENV "base"
$UseInngest        = Use-Default $env:KITH_USE_INNGEST_DEV_SERVER "1"

$_condaCmd = Get-Command conda   -ErrorAction SilentlyContinue
$CondaExe  = if ($env:KITH_CONDA_EXE)  { $env:KITH_CONDA_EXE  }
             elseif ($_condaCmd)        { $_condaCmd.Source     }
             else                       { "" }

if ($env:KITH_CONDA_ENVS_DIR) {
    $CondaEnvsDir = $env:KITH_CONDA_ENVS_DIR
} else {
    $CondaEnvsDir = Join-Path $env:USERPROFILE "miniconda3\envs"
    if (-not (Test-Path $CondaEnvsDir)) {
        $alt = Join-Path $env:USERPROFILE "anaconda3\envs"
        if (Test-Path $alt) { $CondaEnvsDir = $alt }
    }
}

$BackendPythonExe = if ($env:KITH_BACKEND_PYTHON) {
    $env:KITH_BACKEND_PYTHON
} else {
    Join-Path $CondaEnvsDir "$PreferredCondaEnv\python.exe"
}

$_flyctlCmd = Get-Command flyctl -ErrorAction SilentlyContinue
$FlyctlExe  = if ($env:KITH_FLYCTL_EXE) { $env:KITH_FLYCTL_EXE }
              elseif ($_flyctlCmd)        { $_flyctlCmd.Source   }
              else                        { "" }

# ── PID / log files ───────────────────────────────────────────────────────────
$BackendPidFile  = Join-Path $RunDir "backend.pid"
$FrontendPidFile = Join-Path $RunDir "frontend.pid"
$InngestPidFile  = Join-Path $RunDir "inngest.pid"
$BackendLog      = Join-Path $LogDir "backend.log"
$FrontendLog     = Join-Path $LogDir "frontend.log"
$InngestLog      = Join-Path $LogDir "inngest.log"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Log { param([string]$Msg); Write-Host "[kith-dev] $Msg" }

function Get-PortListenerCount {
    param([string]$Port)
    try { @(Get-NetTCPConnection -LocalPort ([int]$Port) -State Listen -ErrorAction SilentlyContinue).Count }
    catch { 0 }
}

function Stop-PortListeners {
    param([string]$Port)
    try {
        $conns = Get-NetTCPConnection -LocalPort ([int]$Port) -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop } catch {}
        }
    } catch {}
    Start-Sleep -Seconds 2
}

function Stop-PidFile {
    param([string]$PidFile, [string]$Label)
    if (Test-Path $PidFile) {
        $raw = (Get-Content $PidFile -Raw).Trim()
        if ($raw -match '^\d+$') {
            $savedPid = [int]$raw
            # Kill children first (cmd.exe wrapper spawns the real service)
            try {
                Get-CimInstance Win32_Process -Filter "ParentProcessId=$savedPid" -ErrorAction SilentlyContinue |
                    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
            } catch {}
            try { Stop-Process -Id $savedPid -Force -ErrorAction Stop } catch {}
        }
        Remove-Item $PidFile -Force
        Write-Log "Stopped $Label from pid file"
    }
}

function Resolve-CondaEnv {
    if (Test-Path (Join-Path $CondaEnvsDir $PreferredCondaEnv)) { return $PreferredCondaEnv }
    if ($CondaExe -and (Test-Path $CondaExe)) {
        try {
            $names = & $CondaExe env list 2>$null |
                Where-Object { $_ -notmatch '^\s*#' -and $_ -match '\S' } |
                ForEach-Object { ($_.Trim() -split '\s+')[0] }
            if ($names -contains $PreferredCondaEnv) { return $PreferredCondaEnv }
        } catch {}
    }
    return $FallbackCondaEnv
}

function Resolve-FlyApiToken {
    if ($env:FLY_API_TOKEN) { return $env:FLY_API_TOKEN }
    if ($FlyctlExe -and (Test-Path $FlyctlExe)) {
        try {
            $t = (& $FlyctlExe auth token 2>$null | Select-Object -Last 1).Trim()
            if ($t) { return $t }
        } catch {}
    }
    return ""
}

function Resolve-BackendPython {
    if (Test-Path $BackendPythonExe) { return $BackendPythonExe }
    $envPy = Join-Path $CondaEnvsDir "$PreferredCondaEnv\python.exe"
    if (Test-Path $envPy) { return $envPy }
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) { return $pyCmd.Source }
    throw "Cannot locate Python. Set KITH_BACKEND_PYTHON or KITH_CONDA_ENVS_DIR."
}

function Wait-ForUrl {
    param([string]$Url, [string]$Label, [int]$Attempts = 45, [int]$Delay = 1)
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop | Out-Null
            Write-Log "$Label is ready at $Url"
            return
        } catch {}
        Start-Sleep -Seconds $Delay
    }
    Write-Log "Warning: $Label did not become ready at $Url"
}

# Spawn a hidden background process via cmd /c; stdout+stderr go to $LogFile.
# Returns the Start-Process handle (a cmd.exe wrapper process).
function Start-BackgroundProcess {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDir,
        [string]$LogFile,
        [hashtable]$ExtraEnv = @{}
    )
    $envParts = @($ExtraEnv.GetEnumerator() | ForEach-Object { "set `"$($_.Key)=$($_.Value)`" &" })
    $envStr   = if ($envParts.Count -gt 0) { ($envParts -join " ") + " " } else { "" }
    $cmd      = "${envStr}`"$FilePath`" $Arguments >> `"$LogFile`" 2>&1"

    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c $cmd" `
        -WorkingDirectory $WorkingDir `
        -WindowStyle Hidden `
        -PassThru
}

# ── Service start functions ───────────────────────────────────────────────────
function Start-Backend {
    $envName = Resolve-CondaEnv
    $token   = Resolve-FlyApiToken
    $python  = Resolve-BackendPython
    Write-Log "Starting backend with conda env: $envName"

    $extra = @{ PYTHONPATH = "." }
    if ($token) { $extra["FLY_API_TOKEN"] = $token }

    $proc = Start-BackgroundProcess -FilePath $python `
        -Arguments "-m uvicorn main:app --host 0.0.0.0 --port $BackendPort" `
        -WorkingDir (Join-Path $RootDir "backend") `
        -LogFile $BackendLog `
        -ExtraEnv $extra
    $proc.Id | Set-Content $BackendPidFile
}

function Start-Frontend {
    Write-Log "Starting frontend with Vite"

    $viteBin = Join-Path $RootDir "frontend\node_modules\.bin\vite.cmd"
    if (-not (Test-Path $viteBin)) {
        $viteCmd = Get-Command vite -ErrorAction SilentlyContinue
        $viteBin = if ($viteCmd) { $viteCmd.Source } else { "vite.cmd" }
    }

    $proc = Start-BackgroundProcess -FilePath $viteBin `
        -Arguments "--host 0.0.0.0" `
        -WorkingDir (Join-Path $RootDir "frontend") `
        -LogFile $FrontendLog
    $proc.Id | Set-Content $FrontendPidFile
}

function Start-Inngest {
    if ($UseInngest -ne "1") {
        Write-Log "Skipping Inngest dev server (KITH_USE_INNGEST_DEV_SERVER != 1)"
        return
    }
    Write-Log "Starting Inngest dev server"

    $npxCmd = Get-Command npx -ErrorAction SilentlyContinue
    $npxBin = if ($npxCmd) { $npxCmd.Source } else { "npx.cmd" }

    $proc = Start-BackgroundProcess -FilePath $npxBin `
        -Arguments "--yes --ignore-scripts=false inngest-cli@latest dev -u `"http://localhost:$BackendPort/api/inngest`"" `
        -WorkingDir $RootDir `
        -LogFile $InngestLog
    $proc.Id | Set-Content $InngestPidFile
}

# ── Orchestration ─────────────────────────────────────────────────────────────
function Stop-Services {
    Write-Log "Stopping backend, frontend, and Inngest"
    Stop-PidFile $BackendPidFile  "backend"
    Stop-PidFile $FrontendPidFile "frontend"
    Stop-PidFile $InngestPidFile  "inngest"
    Stop-PortListeners $BackendPort
    Stop-PortListeners $FrontendPort
    Stop-PortListeners $InngestPort

    $bc = Get-PortListenerCount $BackendPort
    $fc = Get-PortListenerCount $FrontendPort
    $ic = Get-PortListenerCount $InngestPort

    if ($bc -ne 0 -or $fc -ne 0 -or $ic -ne 0) {
        Write-Log "Warning: backend listeners=$bc  frontend listeners=$fc  inngest listeners=$ic"
    } else {
        Write-Log "Ports $BackendPort, $FrontendPort, and $InngestPort are clear"
    }
}

function Show-Status {
    $bc = Get-PortListenerCount $BackendPort
    $fc = Get-PortListenerCount $FrontendPort
    $ic = Get-PortListenerCount $InngestPort
    Write-Log "Backend  listeners on port $BackendPort : $bc"
    Write-Log "Frontend listeners on port $FrontendPort : $fc"
    Write-Log "Inngest  listeners on port $InngestPort : $ic"
    Write-Log "Backend  log : $BackendLog"
    Write-Log "Frontend log : $FrontendLog"
    Write-Log "Inngest  log : $InngestLog"
}

function Start-Services {
    Stop-PortListeners $BackendPort
    Stop-PortListeners $FrontendPort
    Stop-PortListeners $InngestPort

    Start-Backend
    Wait-ForUrl "http://127.0.0.1:$BackendPort/docs" "Backend" 45 1

    Start-Inngest
    if ($UseInngest -eq "1") {
        Wait-ForUrl "http://127.0.0.1:$InngestPort/" "Inngest" 45 1
    }

    Start-Frontend
    Wait-ForUrl "http://127.0.0.1:$FrontendPort/" "Frontend" 45 1

    Write-Log "Restart complete"
    Show-Status
}

# ── Entry point ───────────────────────────────────────────────────────────────
switch ($Action) {
    "start"   { Start-Services }
    "stop"    { Stop-Services  }
    "restart" { Stop-Services; Start-Services }
    "status"  { Show-Status    }
}
