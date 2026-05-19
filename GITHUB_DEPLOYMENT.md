# GitHub-based Deployment Guide

Complete step-by-step instructions for deploying via GitHub — manual first, then auto-deploy via GitHub Actions.

---

## Part A — One-time GitHub setup (do on your Windows machine)

### A.1 — Create a private GitHub repo

1. Go to https://github.com/new
2. Repository name: `legaladvisor` (or anything you like)
3. **Make it Private** (important — keeps your code safe)
4. Do NOT initialize with README/license/.gitignore (you already have a `.gitignore`)
5. Click "Create repository"

After creating, GitHub will show you a URL like:
```
git@github.com:YourUsername/legaladvisor.git
```
or
```
https://github.com/YourUsername/legaladvisor.git
```

Copy this URL — you'll need it.

### A.2 — Initialize git locally and push

Open **PowerShell** in `C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments`:

```powershell
# Init git (skip if already a git repo)
git init
git branch -M main

# Verify .env is NOT being tracked (your .gitignore already excludes it)
git status
# → .env should NOT appear in the list. If it does, STOP and tell me.

# Stage everything and commit
git add .
git commit -m "Initial commit"

# Connect to your GitHub repo (replace URL with yours)
git remote add origin https://github.com/YourUsername/legaladvisor.git

# Push
git push -u origin main
```

If you're asked for credentials → use a GitHub Personal Access Token as password (https://github.com/settings/tokens, create with `repo` scope).

---

## Part B — One-time server setup (do via SSH)

### B.1 — Connect to your server

From PowerShell:
```powershell
ssh root@139.59.39.65
```

### B.2 — Clone the repo into the deploy directory

```bash
# Make the parent directory
mkdir -p /root/mango_tree

# Clone (replace URL with yours)
cd /root/mango_tree
git clone https://github.com/YourUsername/legaladvisor.git legaladvisor
cd legaladvisor
```

If your repo is private, git will ask for credentials. Use your GitHub username + Personal Access Token.

**Tip: store credentials so you don't get asked again:**
```bash
git config --global credential.helper store
# Next git pull will prompt once and save credentials forever.
```

### B.3 — Upload your `.env` file (one-time, from your Windows machine)

Open a **new PowerShell** window (keep the SSH one open):
```powershell
scp "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments\.env" root@139.59.39.65:/root/mango_tree/legaladvisor/.env
```

`.env` is intentionally NOT in git (because of `.gitignore`) so you upload it manually once.

### B.4 — Run the deploy script (in the SSH window)

```bash
cd /root/mango_tree/legaladvisor
chmod +x deploy.sh
bash deploy.sh
```

First run takes 3–5 minutes (installing Python deps + building React). When you see:

```
🎉 DEPLOYMENT SUCCESSFUL
Open in browser:  http://139.59.39.65:5015
```

…you're live. Open http://139.59.39.65:5015 in your browser and log in.

---

## Part C — Manual re-deploy (after future code changes)

This is the simple manual workflow. You make changes locally → push to GitHub → SSH to server → pull + deploy.

### Step 1 — From your Windows machine (PowerShell, in project folder):
```powershell
git add .
git commit -m "describe what you changed"
git push
```

### Step 2 — SSH to the server:
```powershell
ssh root@139.59.39.65
```

### Step 3 — On the server:
```bash
cd /root/mango_tree/legaladvisor
git pull
bash deploy.sh
```

That's it. ~1–2 minutes for re-deploys (much faster than first time).

---

## Part D — Auto-deploy via GitHub Actions (optional, the "fancy" way)

After this is set up, you just run `git push` from your laptop and the server **automatically** pulls + redeploys. No more SSH-ing in.

### D.1 — Generate an SSH deploy key pair (one-time)

On your **Windows PowerShell**:
```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy" -f $env:USERPROFILE\.ssh\legaladvisor_deploy
# Press Enter twice — no passphrase
```

This creates two files:
- `~/.ssh/legaladvisor_deploy`     (private key)
- `~/.ssh/legaladvisor_deploy.pub` (public key)

### D.2 — Add the PUBLIC key to your server

Get the public key contents:
```powershell
type $env:USERPROFILE\.ssh\legaladvisor_deploy.pub
```

Copy the entire line. Then SSH to your server:
```powershell
ssh root@139.59.39.65
```

On the server:
```bash
mkdir -p ~/.ssh
echo "PASTE_THE_PUBLIC_KEY_LINE_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

### D.3 — Add the PRIVATE key as a GitHub secret

Get the private key contents:
```powershell
type $env:USERPROFILE\.ssh\legaladvisor_deploy
```

Copy the entire output including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----` lines.

Then in GitHub:
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** and add these **3 secrets**:

| Secret name | Value |
|---|---|
| `SSH_HOST` | `139.59.39.65` |
| `SSH_USER` | `root` |
| `SSH_PRIVATE_KEY` | (paste the private key contents) |

### D.4 — Confirm the workflow file exists

I've already created `.github/workflows/deploy.yml` for you. Verify with:
```powershell
type .github\workflows\deploy.yml
```

Commit and push it:
```powershell
git add .github/workflows/deploy.yml
git commit -m "Add auto-deploy workflow"
git push
```

### D.5 — That's it. Test it!

Every `git push` to `main` from now on triggers an auto-deploy. To watch it:

1. Go to your GitHub repo → **Actions** tab
2. Click the latest workflow run
3. Click the `deploy` job to see live logs

You can also trigger a manual deploy without pushing code:
- Go to Actions → "Deploy to DigitalOcean" → "Run workflow" button → "Run workflow"

---

## Summary — which option should you use?

| You need… | Use this |
|---|---|
| First-time deploy | **Part A + B** (one-time setup, then run deploy.sh) |
| Quick re-deploy after a small change | **Part C** (manual `git pull && bash deploy.sh`) |
| Fully hands-off — push and forget | **Part D** (GitHub Actions) |

---

## Common gotchas

| Problem | Fix |
|---|---|
| `git push` asks for password forever | Generate a Personal Access Token at https://github.com/settings/tokens and use it as the password |
| `.env` accidentally committed | Run `git rm --cached .env && git commit -m "Remove .env"`. Then **rotate all secrets** (assume they're leaked). |
| GitHub Action says "Permission denied (publickey)" | The `SSH_PRIVATE_KEY` secret content is wrong, or the public key wasn't added to `~/.ssh/authorized_keys` on the server |
| Deploy succeeds but website blank | Hard-refresh your browser (Ctrl+F5) — cached old React build |

---

## What to send me if something fails

If you hit any error, paste:
1. **Which step number** failed (e.g., "B.4 failed")
2. **The exact error message**
3. (For server-side issues) Output of:
   ```bash
   journalctl -u legaladvisor-backend  -n 50
   journalctl -u legaladvisor-frontend -n 50
   ```

I'll fix it immediately.
