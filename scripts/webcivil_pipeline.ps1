# Chain the WebCivil stages with self-healing:
#   OCR shards -> embed shards -> entity/graph backfill.
# A stage is only "done" when the DATABASE says so. Workers have been observed
# to die silently mid-document, so absence of a process is not proof of
# completion -- any shard that vanishes with work outstanding is relaunched.
$repo = "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
$logs = "E:\WEBCIVIL_logs"
Set-Location $repo

function Log([string]$msg) {
    "$(Get-Date -f HH:mm:ss)  $msg" | Tee-Object -Append "$logs\pipeline.log"
}

function Live([string]$match) {
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -match $match }) 
}

function LiveShards([string]$match) {
    $s = @{}
    foreach ($p in Live $match) {
        if ($p.CommandLine -match '--shard (\d+)/(\d+)') { $s[[int]$matches[1]] = $true }
    }
    return $s
}

# Remaining counts straight from Mongo.
function Remaining([string]$stage) {
    $out = python -m scripts.webcivil_remaining $stage 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return -1 }
    return [int]($out | Select-Object -Last 1).ToString().Trim()
}

function Run-Stage([string]$stage, [string]$match, [int]$N) {
    while ($true) {
        Start-Sleep -Seconds 45
        $rem = Remaining $stage
        $live = LiveShards $match
        Log "$stage : remaining=$rem  live_shards=$($live.Count)"

        if ($rem -eq 0) {
            if ($live.Count -gt 0) { continue }   # let them exit cleanly
            Log "$stage : COMPLETE"
            return
        }
        if ($live.Count -ge $N) { continue }

        # Something died with work left. Relaunch only the missing shards.
        for ($k = 0; $k -lt $N; $k++) {
            if ($live.ContainsKey($k)) { continue }
            if ($stage -eq "ocr") {
                $a = "-m scripts.ingest_webcivil --live --workers 2 " +
                     "--vision-concurrency 3 --budget 200 --shard $k/$N"
            } else {
                $a = "-m scripts.chunk_embed_documents " +
                     "--instrument-subtype nyscef_efiled --ctx-batch 16 --shard $k/$N"
            }
            Start-Process -FilePath "python" -ArgumentList $a -WorkingDirectory $repo `
                -RedirectStandardOutput "$logs\$stage\w$k.log" `
                -RedirectStandardError "$logs\$stage\w$k.err" -WindowStyle Hidden
            Log "$stage : RESTARTED dead shard $k (work outstanding)"
            Start-Sleep -Milliseconds 500
        }
    }
}

Log "=== pipeline start ==="
Run-Stage "ocr" "ingest_webcivil" 10

# Contextual summarisation is the slow leg, so embed runs wider than OCR and
# with a larger context batch (fewer cached-document re-reads per chunk).
$EMBED_N = 14
New-Item -ItemType Directory -Force -Path "$logs\embed" | Out-Null
powershell -ExecutionPolicy Bypass -File "$repo\scripts\webcivil_launch.ps1" `
    -Stage embed -N $EMBED_N -CtxBatch 16 *>&1 | Tee-Object -Append "$logs\pipeline.log"

Run-Stage "embed" "chunk_embed_documents" $EMBED_N

Log "starting provenance + entity/graph backfill"
python -m scripts.webcivil_link_chunks --live *>&1 | Tee-Object -Append "$logs\link.log"
python -m scripts.backfill_chunk_entities *>&1 | Tee-Object -Append "$logs\entities.log"
Log "PIPELINE DONE"
