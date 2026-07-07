# Autonomous Boris Lawsuit ingestion — wrapper for Windows Task Scheduler.
# Runs one idempotent pass of the auto-ingest orchestrator and appends a
# timestamped transcript to logs\auto_ingest_runner.log. Safe to run on a
# schedule; the orchestrator itself locks so runs never overlap.

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
$Label = "__....Boris Lawsuit"

Set-Location $Repo
New-Item -ItemType Directory -Force -Path "$Repo\logs" | Out-Null
$RunnerLog = "$Repo\logs\auto_ingest_runner.log"
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

# Resolve python (prefer a local venv if present, else PATH)
$Py = "python"
if (Test-Path "$Repo\.venv\Scripts\python.exe") { $Py = "$Repo\.venv\Scripts\python.exe" }
elseif (Test-Path "$Repo\venv\Scripts\python.exe") { $Py = "$Repo\venv\Scripts\python.exe" }

Add-Content $RunnerLog "===== $stamp  START (py=$Py) ====="
try {
    & $Py "scripts\auto_ingest_folder.py" --label $Label 2>&1 |
        Tee-Object -FilePath $RunnerLog -Append
    $code = $LASTEXITCODE
    Add-Content $RunnerLog "===== $stamp  END exit=$code ====="
    exit $code
} catch {
    Add-Content $RunnerLog "===== $stamp  RUNNER ERROR: $_ ====="
    exit 1
}
