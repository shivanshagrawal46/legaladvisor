# Real-time Gmail push ingestion — setup guide

Goal: the moment an email arrives in (or is labelled) **Boris Lawsuit**, the
DigitalOcean server ingests *that* message + attachments through the full
pipeline (force-vision OCR → chunk/contextual-summary/embed → enrich/link →
verify). Event-driven. No polling. No laptop.

```
Gmail  --watch()-->  Cloud Pub/Sub topic  --pull-->  worker on DO  -->  MongoDB
   (new Boris mail)      (tiny notify)     (streaming)  (scoped ingest)   (searchable)
```

The notification itself only carries a `historyId`; the worker calls
`history.list` to learn exactly which message(s) are new, then ingests only
those. Uses the existing `gmail.readonly` OAuth — **no new Google scopes**.

---

## Part A — Google Cloud (one-time, ~10 min in the console)

Use the **same GCP project** your Gmail OAuth client came from.

1. **Enable the Pub/Sub API**
   Console → APIs & Services → Enable APIs → search "Cloud Pub/Sub API" → Enable.

2. **Create the topic**
   Pub/Sub → Topics → Create topic → ID: `gmail-boris`
   (Full name becomes `projects/<PROJECT_ID>/topics/gmail-boris`.)

3. **Let Gmail publish to the topic** (critical, easy to miss)
   Open topic `gmail-boris` → Permissions → **Add principal**:
   - New principal: `gmail-api-push@system.gserviceaccount.com`
   - Role: **Pub/Sub Publisher** → Save.

4. **Create the pull subscription**
   In topic `gmail-boris` → Create subscription → ID: `gmail-boris-sub`
   - Delivery type: **Pull**
   - Ack deadline: **600 seconds** (max — our pipeline can take a few minutes)
   - Leave the rest default → Create.
   (Full name: `projects/<PROJECT_ID>/subscriptions/gmail-boris-sub`.)

5. **Service account for the worker to read the subscription**
   IAM & Admin → Service Accounts → Create:
   - Name: `gmail-push-worker`
   - Grant role: **Pub/Sub Subscriber** (`roles/pubsub.subscriber`)
   - Done → open it → Keys → Add key → JSON → download.
   Copy that JSON to the DO box (e.g. `/opt/outlook_attachments/pubsub-sa.json`).

Hand me back these three values (or drop them in the env file below):
- `PROJECT_ID`
- topic  = `projects/<PROJECT_ID>/topics/gmail-boris`
- subscription = `projects/<PROJECT_ID>/subscriptions/gmail-boris-sub`

---

## Part B — DigitalOcean server (one-time)

Assumes the repo is already on the box. Adjust paths in the two `.service`
files if your repo isn't at `/opt/outlook_attachments` or user isn't `mangotree`.

1. **Install the new dependency** (into the same venv the pipeline uses)
   ```bash
   cd /opt/outlook_attachments
   .venv/bin/python -m pip install "google-cloud-pubsub>=2.18"
   ```

2. **Copy 3 files from the laptop** into `/opt/outlook_attachments/` so the
   worker is authenticated headlessly:
   - `client_secret.json`  (Gmail OAuth client)
   - `gmail_token.json`    (already-consented token; auto-refreshes from here)
   - the Pub/Sub service-account key `mango-500409-*.json` → save it as
     `pubsub-sa.json`

3. **Append the real-time keys to the box's EXISTING `.env`**
   (`settings.py` loads repo-root `.env` with `override=True`, so it is the
   single source of truth — no separate file). The `.env` must already have
   `MONGO_URI`, `MONGO_DB_NAME`, `PST_FILE_PATH` (any string; file need not
   exist), `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `OPENAI_API_KEY`. Add:
   ```ini
   GMAIL_CLIENT_SECRET=/opt/outlook_attachments/client_secret.json
   GMAIL_TOKEN_PATH=/opt/outlook_attachments/gmail_token.json
   GOOGLE_APPLICATION_CREDENTIALS=/opt/outlook_attachments/pubsub-sa.json
   GMAIL_PUBSUB_TOPIC=projects/mango-500409/topics/gmail-boris
   PUBSUB_SUBSCRIPTION=projects/mango-500409/subscriptions/gmail-boris-sub
   ```

4. **Arm the watch once** (also seeds the history baseline):
   ```bash
   set -a && . ./.env && set +a
   .venv/bin/python -m scripts.gmail_watch --label "__....Boris Lawsuit"
   ```

5. **Install the services**
   ```bash
   sudo cp deploy/gmail-push-worker.service /etc/systemd/system/
   sudo cp deploy/gmail-watch.service       /etc/systemd/system/
   sudo cp deploy/gmail-watch.timer         /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now gmail-push-worker.service
   sudo systemctl enable --now gmail-watch.timer
   ```

6. **Verify**
   ```bash
   systemctl status gmail-push-worker.service
   journalctl -u gmail-push-worker.service -f
   ```
   Send yourself a test email into the Boris Lawsuit label — within seconds the
   log shows `[worker] notification ...` → `[rt] DONE {... status: OK}`.

---

## How it behaves

- **Only on change:** the worker sleeps until Gmail pushes a notification. Zero
  work (and zero cost) when nothing arrives.
- **Scoped & fast:** it ingests only the new message(s); it does NOT run the
  18-minute global occurrence-sync the batch tool does.
- **Idempotent:** re-delivered notifications / already-ingested ids are no-ops
  (3-way dedup).
- **Self-healing:** `watch()` is renewed daily by the timer; if a notification's
  history window has expired, the worker falls back to a 2-day label scan.
- **One-at-a-time:** `max_messages=1` + an in-process lock mean overlapping
  bursts are processed sequentially, never concurrently.

## Turn it off
```bash
sudo systemctl disable --now gmail-push-worker.service gmail-watch.timer
.venv/bin/python -m scripts.gmail_watch --label "__....Boris Lawsuit" --stop
```

## Retire the laptop poller (after this is verified live)
On the laptop (PowerShell):
```powershell
Unregister-ScheduledTask -TaskName "MangoTree Boris Auto-Ingest" -Confirm:$false
```
