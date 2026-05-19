# Legal Advisor — Deployment Guide

Target server: **DigitalOcean Droplet `139.59.39.65`**
Deployment path: **`/root/mango_tree/legaladvisor`** (isolated, will not touch your 8 existing projects)

| Service  | Port | URL                              |
| -------- | ---- | -------------------------------- |
| Frontend | 5015 | http://139.59.39.65:5015         |
| Backend  | 5115 | http://139.59.39.65:5115/api/... |

---

## 1. nginx vs uvicorn — what's actually happening

**uvicorn** and **nginx** do completely different things:

- **uvicorn** is the *ASGI server* that **runs your Python code**. It is NOT optional — FastAPI / Django-async / Flask-async all need something like uvicorn (or gunicorn/hypercorn) to even start.
- **nginx** is a *reverse proxy*. It does not run Python. It receives HTTP requests on port 80/443 and forwards them to upstream apps (like uvicorn or your Node.js apps).

Your existing 8 projects use this chain:
```
Browser → nginx (port 80/443, SSL, domain routing) → Node.js (port 3001/3002/...)
```

For Legal Advisor, since you said "raw IP is fine, no domain, internal use", we use:
```
Browser → uvicorn directly (port 5115)
Browser → serve directly (port 5015)
```

Why we skipped nginx for this project:

| Concern | Verdict |
| --- | --- |
| SSL/HTTPS | Not needed yet — raw IP + HTTP is fine for internal team |
| Domain routing | Not needed — using raw IP + ports |
| Static file serving | Handled by `npx serve` on its own port |
| Rate limiting / gzip | Optional for internal tool |
| **Risk of breaking 8 existing projects** | ✅ **ZERO — we don't touch `/etc/nginx/` at all** |

When you later want a domain + HTTPS:
- Add one nginx server block: `server_name legaladvisor.mtreh.com → proxy_pass http://127.0.0.1:5015`
- Add a Let's Encrypt cert with `certbot`
- Done. Your existing projects are untouched.

---

## 2. Python version

- **Local (your machine):** Python 3.9.1
- **Server (target):** Python 3.10+ (Ubuntu 22.04 default = 3.10, Ubuntu 24.04 default = 3.12)
- `deploy.sh` **checks Python version** and falls back to installing `python3.11` from the deadsnakes PPA if the system Python is older than 3.10.
- Server runtime does NOT need `libratom` (PST parsing) or `paddleocr` (OCR) — those were used during the data-prep phase. The server reads pre-processed data from MongoDB. So we use a slim `requirements_server.txt` (~150 MB vs ~1.5 GB for full `requirements.txt`).

---

## 3. Auto-deployment — how to run it

### One command from your Windows PowerShell

From `C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments\`:

```powershell
.\upload_to_server.ps1
```

That's it. The script:

1. Connects to `root@139.59.39.65` via SSH
2. Wipes `/tmp/legaladvisor_deploy/` (our private temp staging folder — safe, never touches `/root`)
3. Locally stages your project files (excluding `node_modules`, `dist`, `__pycache__`, `.git`, `logs`, `venv`) into a temp folder
4. SCPs the staged files + `.env` to the server
5. Runs `deploy.sh` on the server which:

| Step | What `deploy.sh` does |
| ---- | ---- |
| 1 | Installs `python3`, `python3-venv`, `nodejs`, `npm`, `serve`, `rsync` |
| 2 | Checks Python version, installs `python3.11` if too old |
| 3 | Creates `/root/mango_tree/legaladvisor/` |
| 4 | Rsyncs project files from `/root/upload/` |
| 5 | Creates a Python venv and installs `requirements_server.txt` |
| 6 | `npm install` + `npm run build` in `frontend/` |
| 7 | Installs systemd services `legaladvisor-backend` + `legaladvisor-frontend` |
| 8 | Enables + starts both services (so they auto-start on reboot) |
| 9 | Health checks both services |

First run: ~3–5 minutes. Re-deploys: ~1–2 minutes (npm/pip caches kick in).

### Prerequisites (one-time, on your Windows machine)

You need SSH access to the droplet. Two options:

**Option A — SSH key (recommended):**
```powershell
# Generate a key if you don't have one
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\id_rsa

# Copy your public key to the droplet (one-time)
# Easiest: open .ssh\id_rsa.pub, copy contents, then on the droplet:
#   nano ~/.ssh/authorized_keys
# and paste the line at the end.
```

**Option B — password auth:**
Just run `.\upload_to_server.ps1` — it will prompt for the root password (you'll have to type it ~3 times).

---

## 4. After-deployment commands (on the server)

```bash
# View logs (live tail)
journalctl -u legaladvisor-backend  -f
journalctl -u legaladvisor-frontend -f

# Restart manually
systemctl restart legaladvisor-backend
systemctl restart legaladvisor-frontend

# Check status
systemctl status legaladvisor-backend
systemctl status legaladvisor-frontend

# Stop everything (won't affect other projects)
systemctl stop legaladvisor-backend legaladvisor-frontend

# Open ports if ufw is active
ufw allow 5015/tcp
ufw allow 5115/tcp
```

---

## 5. To re-deploy after code changes

Just run `.\upload_to_server.ps1` again. The script syncs only changed files and restarts the services. No need to touch the server manually.

---

## 6. Safety guarantees

Everything below confirms we won't break your existing 8 projects:

- ✅ No changes to `/etc/nginx/`
- ✅ No changes to existing systemd services
- ✅ Uses dedicated ports `5015` and `5115` (not 80, 443, 3000, 3001, etc.)
- ✅ Lives in `/root/mango_tree/legaladvisor/` (its own folder)
- ✅ Has its own Python `venv` (no global `pip install`)
- ✅ Service names are prefixed `legaladvisor-*` (no naming collisions)
- ✅ The `serve` package is installed globally via npm but only adds the `serve` binary — doesn't affect any running Node app
