# Launch N disjoint shards of a WebCivil pipeline stage, one log per worker.
param(
    [ValidateSet("ocr", "embed")] [string]$Stage = "ocr",
    [int]$N = 10,
    [int]$VisionConcurrency = 3,
    [int]$CtxBatch = 12
)

$repo = "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
$logs = "E:\WEBCIVIL_logs\$Stage"
New-Item -ItemType Directory -Force -Path $logs | Out-Null
Get-ChildItem $logs -Filter *.log -ErrorAction SilentlyContinue | Remove-Item -Force

for ($k = 0; $k -lt $N; $k++) {
    if ($Stage -eq "ocr") {
        $args = "-m scripts.ingest_webcivil --live --workers 1 " +
                "--vision-concurrency $VisionConcurrency --budget 200 --shard $k/$N"
    } else {
        $args = "-m scripts.chunk_embed_documents " +
                "--instrument-subtype nyscef_efiled --ctx-batch $CtxBatch --shard $k/$N"
    }
    $log = "$logs\w$k.log"
    Start-Process -FilePath "python" -ArgumentList $args -WorkingDirectory $repo `
        -RedirectStandardOutput $log -RedirectStandardError "$logs\w$k.err" `
        -WindowStyle Hidden
    Write-Host "launched $Stage worker $k -> $log"
    Start-Sleep -Milliseconds 700
}
Write-Host "`n$N $Stage workers running. Logs in $logs"
