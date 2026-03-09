param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "restart",

    [switch]$WslShutdown,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bashExe = "C:\Program Files\Git\bin\bash.exe"
$scriptPath = Join-Path $root "restart-dev.sh"

if ($ExtraArgs -contains "--wsl-shutdown") {
    $WslShutdown = $true
}

if (-not (Test-Path $bashExe)) {
    throw "Git Bash not found at $bashExe"
}

if (-not (Test-Path $scriptPath)) {
    throw "restart-dev.sh not found at $scriptPath"
}

$wslFlag = if ($WslShutdown) { " --wsl-shutdown" } else { "" }
$command = "./restart-dev.sh $Action$wslFlag"

Push-Location $root
try {
    & $bashExe -lc $command
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
