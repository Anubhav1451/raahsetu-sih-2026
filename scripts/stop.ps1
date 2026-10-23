$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$PidFile = Join-Path $ProjectRoot 'work\dev-processes.json'
if (Test-Path -LiteralPath $PidFile) {
    $SavedProcesses = @(Get-Content -Raw -LiteralPath $PidFile | ConvertFrom-Json)
    foreach ($Entry in $SavedProcesses) {
        $Process = Get-Process -Id $Entry.id -ErrorAction SilentlyContinue
        if ($Process) {
            try {
                if ($Process.StartTime.ToUniversalTime().ToString('o') -eq $Entry.start) {
                    Stop-Process -Id $Entry.id -ErrorAction SilentlyContinue
                }
            } catch {
                # The process may have exited between lookup and cleanup.
            }
        }
    }
    Remove-Item -LiteralPath $PidFile
}
