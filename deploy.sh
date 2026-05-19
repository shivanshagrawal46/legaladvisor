#!/bin/bash
# =============================================================================
# Legal Advisor — DigitalOcean Deployment Script
# Server:   139.59.39.65
# Backend:  http://139.59.39.65:5115
# Frontend: http://139.59.39.65:5015
#
# NON-INVASIVE deployment:
#   - Does NOT run apt-get update / upgrade
#   - Does NOT install Node.js or npm (uses existing)
#   - Does NOT install global npm packages
#   - Only installs Python venv/dev tooling IF missing
#   - All project files isolated under /root/mango_tree/legaladvisor
#   - Two dedicated systemd services with unique names
# =============================================================================
set -e  # stop on any error

# ── Config ───────────────────────────────────────────────────────────────────
DEPLOY_DIR="/root/mango_tree/legaladvisor"
UPLOAD_DIR="/tmp/legaladvisor_deploy"
BACKEND_SERVICE="legaladvisor-backend"
FRONTEND_SERVICE="legaladvisor-frontend"
REQUIRED_PY_MAJOR=3
REQUIRED_PY_MINOR=10

echo ""
echo "======================================================"
echo "  Legal Advisor Deployment (non-invasive mode)"
echo "  Target: 139.59.39.65  Ports: 5015 (UI) / 5115 (API)"
echo "  Path:   $DEPLOY_DIR"
echo "======================================================"
echo ""

# ── 1. Verify existing tooling (Node.js, npm, rsync) — DO NOT INSTALL ────────
echo "[1/8] Verifying existing tooling..."

MISSING_REQUIRED=()
for cmd in node npm; do
    if ! command -v $cmd > /dev/null 2>&1; then
        MISSING_REQUIRED+=("$cmd")
    fi
done

if [ ${#MISSING_REQUIRED[@]} -gt 0 ]; then
    echo "  ❌ Required tools missing: ${MISSING_REQUIRED[*]}"
    echo "     These should already exist (your other React projects use them)."
    echo "     Aborting — please install them manually first."
    exit 1
fi

echo "      ✅ Node: $(node --version)"
echo "      ✅ npm:  $(npm --version)"

# rsync — needed for sync step; install only if missing
if ! command -v rsync > /dev/null 2>&1; then
    echo "      ⚙️  rsync missing → installing (single package, no update)"
    apt-get install -y -qq rsync
fi
echo "      ✅ rsync: $(rsync --version | head -n1 | awk '{print $3}')"

# ── 2. Python check + install ONLY what's missing ────────────────────────────
echo "[2/8] Checking Python..."

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
PY_MINOR=$(echo $PY_VER | cut -d. -f2)

PYTHON_BIN=python3
NEED_NEWER_PYTHON=false

if [ "$PY_MAJOR" -lt "$REQUIRED_PY_MAJOR" ] || \
   ([ "$PY_MAJOR" -eq "$REQUIRED_PY_MAJOR" ] && [ "$PY_MINOR" -lt "$REQUIRED_PY_MINOR" ]); then
    NEED_NEWER_PYTHON=true
fi

# Only install python3-venv / python3-dev / build-essential if MISSING
PY_PKGS_TO_INSTALL=()

if ! python3 -c "import venv" 2>/dev/null && [ "$NEED_NEWER_PYTHON" = false ]; then
    PY_PKGS_TO_INSTALL+=("python3-venv")
fi

# python3-dev needed for some packages with C extensions (e.g. bcrypt) if they fall back to source
if ! dpkg -s python3-dev > /dev/null 2>&1; then
    PY_PKGS_TO_INSTALL+=("python3-dev")
fi

if ! dpkg -s build-essential > /dev/null 2>&1; then
    PY_PKGS_TO_INSTALL+=("build-essential")
fi

if [ ${#PY_PKGS_TO_INSTALL[@]} -gt 0 ]; then
    echo "      Installing missing Python tooling: ${PY_PKGS_TO_INSTALL[*]}"
    apt-get install -y -qq "${PY_PKGS_TO_INSTALL[@]}"
else
    echo "      Python tooling already present."
fi

if [ "$NEED_NEWER_PYTHON" = true ]; then
    echo "      ⚙️  System Python $PY_VER is below required $REQUIRED_PY_MAJOR.$REQUIRED_PY_MINOR"
    echo "      Installing python3.11 from deadsnakes PPA (does not touch system python3)..."
    apt-get install -y -qq software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
    PYTHON_BIN=python3.11
fi

echo "      ✅ Using: $($PYTHON_BIN --version)  ($PYTHON_BIN)"

# ── 3. Create deploy directory ───────────────────────────────────────────────
echo "[3/8] Setting up $DEPLOY_DIR..."
mkdir -p "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/logs"

# ── 4. Sync project files (skipped in git mode) ──────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" = "$DEPLOY_DIR" ]; then
    echo "[4/8] Running in-place (git mode) — skipping rsync."
elif [ -d "$UPLOAD_DIR" ] && [ -f "$UPLOAD_DIR/deploy.sh" ]; then
    echo "[4/8] Syncing project files from $UPLOAD_DIR → $DEPLOY_DIR..."
    rsync -a --delete \
            --exclude='frontend/node_modules' \
            --exclude='frontend/dist' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.git' \
            --exclude='logs/*.log' \
            --exclude='venv' \
            "$UPLOAD_DIR/" "$DEPLOY_DIR/"
    echo "      Files synced."
else
    echo "[4/8] ❌ Cannot find source files."
    echo "       Either:"
    echo "         (a) Run this script from inside $DEPLOY_DIR (git mode)"
    echo "         (b) Stage files in $UPLOAD_DIR first"
    exit 1
fi

# ── 5. Python venv + project dependencies (isolated) ─────────────────────────
echo "[5/8] Creating venv & installing Python dependencies (slim)..."
cd "$DEPLOY_DIR"

if [ -d venv ]; then
    rm -rf venv
fi

$PYTHON_BIN -m venv venv
source venv/bin/activate

pip install --quiet --upgrade pip setuptools wheel

if [ -f requirements_server.txt ]; then
    echo "      Using requirements_server.txt (slim runtime)"
    pip install --quiet -r requirements_server.txt
else
    echo "      requirements_server.txt missing → using requirements.txt"
    pip install --quiet -r requirements.txt
fi

echo "      ✅ Python deps installed inside $DEPLOY_DIR/venv (isolated)"

# ── 6. Build React frontend + install local 'serve' (NOT global) ─────────────
echo "[6/8] Building React frontend (production)..."
cd "$DEPLOY_DIR/frontend"
npm install --silent --no-audit --no-fund
npm run build
echo "      ✅ Build complete → $DEPLOY_DIR/frontend/dist"

# Install 'serve' LOCALLY (in this project's node_modules only — not -g)
if [ ! -x "$DEPLOY_DIR/frontend/node_modules/.bin/serve" ]; then
    echo "      Installing 'serve' locally for this project..."
    npm install --silent --no-audit --no-fund --no-save serve
fi
echo "      ✅ Using local serve at $DEPLOY_DIR/frontend/node_modules/.bin/serve"

# ── 7. Install systemd services (unique names, isolated) ─────────────────────
echo "[7/8] Installing systemd services..."
cd "$DEPLOY_DIR"

SERVE_BIN="$DEPLOY_DIR/frontend/node_modules/.bin/serve"

# Patch backend service: use venv's uvicorn + correct WorkingDirectory
sed -e "s|/usr/bin/python3 -m uvicorn|$DEPLOY_DIR/venv/bin/uvicorn|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$DEPLOY_DIR|g" \
    -e "s|EnvironmentFile=.*|EnvironmentFile=$DEPLOY_DIR/.env|g" \
    deploy/legaladvisor-backend.service > /tmp/legaladvisor-backend.service

# Patch frontend service: WorkingDirectory + use LOCAL serve binary (not /usr/bin/npx)
sed -e "s|WorkingDirectory=.*|WorkingDirectory=$DEPLOY_DIR/frontend|g" \
    -e "s|ExecStart=.*|ExecStart=$SERVE_BIN -s dist -l 5015|g" \
    deploy/legaladvisor-frontend.service > /tmp/legaladvisor-frontend.service

cp /tmp/legaladvisor-backend.service  /etc/systemd/system/legaladvisor-backend.service
cp /tmp/legaladvisor-frontend.service /etc/systemd/system/legaladvisor-frontend.service

systemctl daemon-reload
echo "      ✅ Services installed (legaladvisor-backend, legaladvisor-frontend)"

# ── 8. Enable + (re)start ONLY our services ──────────────────────────────────
echo "[8/8] Starting our services (does not touch any other service)..."
systemctl enable $BACKEND_SERVICE  > /dev/null 2>&1
systemctl enable $FRONTEND_SERVICE > /dev/null 2>&1

systemctl restart $BACKEND_SERVICE  || systemctl start $BACKEND_SERVICE
sleep 4
systemctl restart $FRONTEND_SERVICE || systemctl start $FRONTEND_SERVICE
sleep 3

# ── Health check ─────────────────────────────────────────────────────────────
echo ""
echo "Health check:"

BACKEND_OK=false
FRONTEND_OK=false

if systemctl is-active --quiet $BACKEND_SERVICE; then
    BACKEND_OK=true
    echo "      ✅ Backend  service RUNNING on :5115"
else
    echo "      ❌ Backend  service FAILED  — journalctl -u $BACKEND_SERVICE -n 50"
fi

if systemctl is-active --quiet $FRONTEND_SERVICE; then
    FRONTEND_OK=true
    echo "      ✅ Frontend service RUNNING on :5015"
else
    echo "      ❌ Frontend service FAILED  — journalctl -u $FRONTEND_SERVICE -n 50"
fi

sleep 2
if curl -sf -m 5 http://127.0.0.1:5115/api/health > /dev/null 2>&1; then
    echo "      ✅ Backend HTTP responding (/api/health)"
else
    echo "      ⚠️  Backend HTTP not responding yet (may still be warming up)"
fi

# Firewall reminder (read-only — does not change rules)
if command -v ufw > /dev/null 2>&1; then
    if ufw status 2>/dev/null | grep -q "Status: active"; then
        echo ""
        echo "      ⚠️  ufw is active — if ports aren't reachable, run manually:"
        echo "          ufw allow 5015/tcp"
        echo "          ufw allow 5115/tcp"
    fi
fi

echo ""
echo "======================================================"
if $BACKEND_OK && $FRONTEND_OK; then
    echo "  🎉 DEPLOYMENT SUCCESSFUL"
    echo ""
    echo "  Open in browser:  http://139.59.39.65:5015"
    echo "  API health check: http://139.59.39.65:5115/api/health"
    echo ""
    echo "  Logs:"
    echo "    journalctl -u $BACKEND_SERVICE  -f"
    echo "    journalctl -u $FRONTEND_SERVICE -f"
else
    echo "  ⚠️  DEPLOYMENT PARTIALLY FAILED — check journalctl above"
fi
echo "======================================================"
echo ""
