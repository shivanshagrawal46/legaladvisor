# =============================================================================
# Upload Legal Advisor project to DigitalOcean Droplet and run deploy.sh
# Run from Windows PowerShell:    .\upload_to_server.ps1
#
# Server:  139.59.39.65
# Path:    /root/mango_tree/legaladvisor   (isolated from your 8 other projects)
# Ports:   5015 (frontend) / 5115 (backend API)
# =============================================================================

$ErrorActionPreference = "Stop"

$SERVER     = "139.59.39.65"
$USER       = "root"
# If your SSH key is somewhere else, change this:
$SSH_KEY    = "$env:USERPROFILE\.ssh\id_rsa"
$LOCAL_ROOT = "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
$REMOTE_STAGING = "/tmp/legaladvisor_deploy"   # safe temp folder — NEVER under /root

Write-Host ""
Write-Host "======================================================"
Write-Host "  Legal Advisor — Upload + Deploy"
Write-Host "  Target: $USER@$SERVER"
Write-Host "  Path:   /root/mango_tree/legaladvisor"
Write-Host "======================================================"
Write-Host ""

# Optional: pass `-SshKey` flag at runtime to override default key path
if (-not (Test-Path $SSH_KEY)) {
    Write-Host "⚠️  SSH key not found at $SSH_KEY" -ForegroundColor Yellow
    Write-Host "    If you use password auth, just press Enter when prompted."
    Write-Host "    Otherwise edit `$SSH_KEY at the top of this script."
    Write-Host ""
    $useKey = $false
} else {
    $useKey = $true
}

function Invoke-Ssh($cmd) {
    if ($useKey) {
        ssh -i $SSH_KEY "${USER}@${SERVER}" $cmd
    } else {
        ssh "${USER}@${SERVER}" $cmd
    }
    if ($LASTEXITCODE -ne 0) { throw "ssh failed: $cmd" }
}

function Invoke-Scp($source, $dest) {
    if ($useKey) {
        scp -i $SSH_KEY -r $source "${USER}@${SERVER}:${dest}"
    } else {
        scp -r $source "${USER}@${SERVER}:${dest}"
    }
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $source → $dest" }
}

# ── Step 1: Wipe OUR temp staging folder so old files don't leak in ─────────
# This ONLY touches /tmp/legaladvisor_deploy — nothing else on the server.
Write-Host "[1/4] Preparing temp staging folder on server ($REMOTE_STAGING)..."
Invoke-Ssh "rm -rf $REMOTE_STAGING && mkdir -p $REMOTE_STAGING"

# ── Step 2: Upload project files ────────────────────────────────────────────
Write-Host "[2/4] Uploading project files (this may take 30-60 seconds)..."

# We exclude .git, node_modules, dist, __pycache__, logs, venv before upload
# by listing only what we need.
$itemsToUpload = @(
    "src",
    "api",
    "config",
    "frontend",
    "deploy",
    "server.py",
    "requirements.txt",
    "requirements_server.txt",
    "deploy.sh"
)

# Filter frontend to exclude node_modules + dist BEFORE uploading (huge speedup)
# Build a temp staging copy locally
$tempStage = Join-Path $env:TEMP "legaladvisor_upload_$(Get-Random)"
New-Item -ItemType Directory -Path $tempStage | Out-Null

try {
    foreach ($item in $itemsToUpload) {
        $src = Join-Path $LOCAL_ROOT $item
        if (-not (Test-Path $src)) {
            Write-Host "      ⚠️  Skipping missing: $item" -ForegroundColor Yellow
            continue
        }
        $dst = Join-Path $tempStage $item
        if ((Get-Item $src).PSIsContainer) {
            # robocopy is fastest + has /XD exclude-dirs
            $excludeDirs = @("node_modules", "dist", "__pycache__", ".git", "logs", "venv", ".vite")
            $robocopyArgs = @($src, $dst, "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP", "/XD") + $excludeDirs
            robocopy @robocopyArgs | Out-Null
        } else {
            Copy-Item $src $dst -Force
        }
    }

    # Upload the staged tree
    Write-Host "      Uploading staged tree..."
    Invoke-Scp "$tempStage\*" "$REMOTE_STAGING/"

    # ── Step 3: Upload .env (kept separate so it's never in temp dirs) ──────
    Write-Host "[3/4] Uploading .env (API keys)..."
    $envFile = Join-Path $LOCAL_ROOT ".env"
    if (-not (Test-Path $envFile)) {
        throw ".env file not found at $envFile"
    }
    Invoke-Scp $envFile "$REMOTE_STAGING/.env"

    # ── Step 4: Run deploy.sh on server ─────────────────────────────────────
    Write-Host "[4/4] Running deploy.sh on server (this takes 3-5 min on first run)..."
    Write-Host ""
    Invoke-Ssh "chmod +x $REMOTE_STAGING/deploy.sh && bash $REMOTE_STAGING/deploy.sh"

    Write-Host ""
    Write-Host "======================================================"
    Write-Host "  ✅ DEPLOYMENT COMPLETE"
    Write-Host ""
    Write-Host "  Frontend:  http://139.59.39.65:5015"
    Write-Host "  Backend:   http://139.59.39.65:5115/api/health"
    Write-Host "  Login:     rakeshsir@mtreh.com / MangoTree@12345"
    Write-Host "======================================================"
    Write-Host ""
}
finally {
    if (Test-Path $tempStage) {
        Remove-Item -Recurse -Force $tempStage -ErrorAction SilentlyContinue
    }
}
