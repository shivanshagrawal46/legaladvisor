<#
.SYNOPSIS
    Re-encodes a video to fit within a target file size.

.DESCRIPTION
    Works out the bitrate budget from the clip duration and the requested size,
    then encodes to hit it. Software encoders (libx264/libx265) use a real
    two-pass encode; hardware encoders use constrained VBR. Output size is
    verified afterwards and the encode is retried at a lower bitrate if it
    overshot.

.EXAMPLE
    .\compress_video.ps1 -InputPath 'D:\VIMAL ENTERPRISES DOCUMENTARY.mp4'

.EXAMPLE
    .\compress_video.ps1 -InputPath 'D:\clip.mp4' -TargetMB 200 -Height 1080 -Encoder libx264
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [string]$OutputPath,

    # Desired maximum output size in megabytes (1 MB = 1024*1024 bytes).
    [double]$TargetMB = 480,

    [ValidateSet('auto', 'libx264', 'libx265', 'h264_qsv', 'hevc_qsv', 'h264_nvenc', 'hevc_nvenc', 'h264_amf')]
    [string]$Encoder = 'auto',

    # Downscale to this vertical resolution (e.g. 1080). 0 keeps the source size.
    [int]$Height = 0,

    [int]$AudioKbps = 192,

    # Encoder speed/quality preset. Left blank a sensible default per encoder is used.
    [string]$Preset = '',

    # How many times to re-encode at a reduced bitrate if the result overshoots.
    [int]$MaxAttempts = 3,

    [switch]$Overwrite
)

$ErrorActionPreference = 'Stop'

# winget puts ffmpeg on the machine PATH, which an already-running shell won't
# have picked up yet.
function Initialize-FfmpegPath {
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) { return }

    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [System.Environment]::GetEnvironmentVariable('Path', 'User')

    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        throw "ffmpeg was not found on PATH. Install it with: winget install --id Gyan.FFmpeg -e"
    }
}

function Get-MediaInfo {
    param([string]$Path)

    $json = & ffprobe -v error -show_format -show_streams -of json -- $Path 2>&1
    if ($LASTEXITCODE -ne 0) { throw "ffprobe could not read '$Path':`n$json" }

    $probe = $json | ConvertFrom-Json
    $video = $probe.streams | Where-Object { $_.codec_type -eq 'video' } | Select-Object -First 1
    if (-not $video) { throw "No video stream found in '$Path'." }

    $duration = [double]$probe.format.duration
    if ($duration -le 0) { throw "Could not determine the duration of '$Path'." }

    [pscustomobject]@{
        Duration = $duration
        Width    = [int]$video.width
        HeightPx = [int]$video.height
        Bytes    = [long]$probe.format.size
        HasAudio = [bool]($probe.streams | Where-Object { $_.codec_type -eq 'audio' })
    }
}

function Test-Encoder {
    param([string]$Name)

    $null = & ffmpeg -hide_banner -loglevel error `
        -f lavfi -i testsrc=size=640x480:rate=30:duration=1 `
        -c:v $Name -f null - 2>&1
    return ($LASTEXITCODE -eq 0)
}

function Select-Encoder {
    # Hardware first: this is 4K60 footage and the bitrate budget is generous
    # enough that a hardware encoder holds up fine while being far quicker.
    foreach ($candidate in @('h264_qsv', 'h264_nvenc', 'h264_amf')) {
        Write-Host "  probing $candidate ..." -NoNewline
        if (Test-Encoder -Name $candidate) {
            Write-Host " available"
            return $candidate
        }
        Write-Host " no"
    }
    Write-Host "  falling back to libx264 (CPU)"
    return 'libx264'
}

function Get-DefaultPreset {
    param([string]$Enc)

    switch -Wildcard ($Enc) {
        '*_qsv'   { 'slow' }
        '*_nvenc' { 'p6' }
        '*_amf'   { 'quality' }
        default   { 'medium' }
    }
}

function Invoke-Ffmpeg {
    param([string[]]$Arguments)

    & ffmpeg @Arguments
    if ($LASTEXITCODE -ne 0) { throw "ffmpeg exited with code $LASTEXITCODE." }
}

Initialize-FfmpegPath

$InputPath = (Resolve-Path -LiteralPath $InputPath).Path
$info = Get-MediaInfo -Path $InputPath

if (-not $OutputPath) {
    $dir  = Split-Path -Parent $InputPath
    $name = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
    $OutputPath = Join-Path $dir "$name (compressed).mp4"
}
if ((Test-Path -LiteralPath $OutputPath) -and -not $Overwrite) {
    throw "'$OutputPath' already exists. Pass -Overwrite to replace it."
}
if ([System.IO.Path]::GetFullPath($OutputPath) -eq $InputPath) {
    throw "Output path must differ from the input path."
}

if ($Encoder -eq 'auto') {
    Write-Host "Choosing an encoder..." -ForegroundColor Cyan
    $Encoder = Select-Encoder
}
if (-not $Preset) { $Preset = Get-DefaultPreset -Enc $Encoder }

$isTwoPass = $Encoder -in @('libx264', 'libx265')
$audioKbpsEffective = if ($info.HasAudio) { $AudioKbps } else { 0 }

Write-Host ""
Write-Host "Input    : $InputPath"
Write-Host ("Source   : {0}x{1}, {2:N1}s, {3:N1} MB" -f `
    $info.Width, $info.HeightPx, $info.Duration, ($info.Bytes / 1MB))
Write-Host "Output   : $OutputPath"
Write-Host ("Target   : under {0:N0} MB" -f $TargetMB)
Write-Host "Encoder  : $Encoder (preset $Preset)$(if ($isTwoPass) { ', two-pass' } else { ', constrained VBR' })"
Write-Host ""

# Hold back a little of the budget so container overhead and bitrate wobble
# don't push the result past the limit.
$safety = 0.95
$passLogBase = Join-Path ([System.IO.Path]::GetTempPath()) ("ffpass_" + [guid]::NewGuid().ToString('N'))
$success = $false

try {
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {

        $totalKbps = ($TargetMB * 1MB * 8 * $safety) / $info.Duration / 1000
        $videoKbps = [int][math]::Floor($totalKbps - $audioKbpsEffective)

        if ($videoKbps -lt 100) {
            throw ("A {0:N0} MB target over {1:N0}s leaves only {2} kbps for video, which is not workable. " -f `
                   $TargetMB, $info.Duration, $videoKbps) +
                  "Raise -TargetMB or lower -AudioKbps."
        }

        Write-Host ("Attempt {0}/{1}: video {2} kbps, audio {3} kbps" -f `
            $attempt, $MaxAttempts, $videoKbps, $audioKbpsEffective) -ForegroundColor Cyan

        $common = @('-hide_banner', '-y', '-i', $InputPath, '-map', '0:v:0')
        if ($info.HasAudio) { $common += @('-map', '0:a:0') }

        $filters = @()
        if ($Height -gt 0 -and $Height -lt $info.HeightPx) {
            $filters += "scale=-2:$Height`:flags=lanczos"
        }
        if ($Encoder -like '*_qsv') { $filters += 'format=nv12' }
        $vf = if ($filters.Count) { @('-vf', ($filters -join ',')) } else { @() }

        $videoOpts = @(
            '-c:v', $Encoder,
            '-b:v', "${videoKbps}k",
            '-maxrate', ("{0}k" -f [int]($videoKbps * 1.5)),
            '-bufsize', ("{0}k" -f [int]($videoKbps * 3)),
            '-pix_fmt', 'yuv420p',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709'
        )
        $videoOpts += if ($Encoder -like '*_nvenc') { @('-preset', $Preset, '-rc', 'vbr', '-multipass', 'fullres') }
                      elseif ($Encoder -like '*_qsv') { @('-preset', $Preset, '-look_ahead', '1', '-look_ahead_depth', '40') }
                      else { @('-preset', $Preset) }

        $audioOpts = if ($info.HasAudio) { @('-c:a', 'aac', '-b:a', "${AudioKbps}k", '-ac', '2') } else { @('-an') }

        if ($isTwoPass) {
            Write-Host "  pass 1 of 2..." -ForegroundColor DarkGray
            Invoke-Ffmpeg ($common + $vf + $videoOpts +
                @('-pass', '1', '-passlogfile', $passLogBase, '-an', '-f', 'null', '-'))

            Write-Host "  pass 2 of 2..." -ForegroundColor DarkGray
            Invoke-Ffmpeg ($common + $vf + $videoOpts + $audioOpts +
                @('-pass', '2', '-passlogfile', $passLogBase, '-movflags', '+faststart', $OutputPath))
        }
        else {
            Invoke-Ffmpeg ($common + $vf + $videoOpts + $audioOpts +
                @('-movflags', '+faststart', $OutputPath))
        }

        $actualMB = (Get-Item -LiteralPath $OutputPath).Length / 1MB
        Write-Host ("  produced {0:N1} MB" -f $actualMB)

        if ($actualMB -le $TargetMB) {
            $success = $true
            break
        }

        Write-Warning ("Overshot the {0:N0} MB target; retrying at a lower bitrate." -f $TargetMB)
        # Scale the budget back by however much we overshot, plus a margin.
        $safety = $safety * ($TargetMB / $actualMB) * 0.97
    }

    if (-not $success) {
        throw ("Could not get under {0:N0} MB after {1} attempts." -f $TargetMB, $MaxAttempts)
    }

    $finalMB = (Get-Item -LiteralPath $OutputPath).Length / 1MB
    Write-Host ""
    Write-Host "Done." -ForegroundColor Green
    Write-Host ("  {0:N1} MB  ->  {1:N1} MB  ({2:N1}% smaller)" -f `
        ($info.Bytes / 1MB), $finalMB, (100 - ($finalMB / ($info.Bytes / 1MB) * 100)))
    Write-Host "  $OutputPath"
}
finally {
    Get-ChildItem -Path ($passLogBase + '*') -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
}
