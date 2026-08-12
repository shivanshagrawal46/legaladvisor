# CEO Report — Website Archival of bonaventuraauctions.com

**Date:** 15 Jul 2026
**Prepared by:** Engineering
**Target:** `https://www.bonaventuraauctions.com/`
*rawl completion.** Because we interrupted the crawl, the offline links weren't rewritten and styling appeared "broken." We resolved it with a custom post-processing converter — but the takeaway is to either let crawls finish or run a conversion pass afterward.

7. **Some lot pages are broken server-side (HTTP 500).** Several hundred lots returned server errors and are genuinely un-archivable — a data-quality signal about the source site itself, not a flaw in our process.

8. **Integrity layer adds evidentiary weight cheaply.** Hashing every file + recording timestamps/IPs turns a casual copy into a defensible record at near-zero cost.

---

## 5. Tools & Libraries Used

| Tool / Library | Version | Purpose |
|---|---|---|
| **GNU Wget** | 1.21.4 | Core recursive site mirroring, page-requisites, cookie-based authenticated crawl, link conversion |*Objective:** Produce a self-contained, evidence-grade offline archive of the auction website — including the logged-in area — that remains accessible even if the site is taken offline by its host.

---

## 1. Executive Summary

We successfully captured two archives of the target site:

1. A **public archive** — the full public-facing website (complete and clean).
2. An **authenticated archive** — the logged-in member area, including auction lot detail pages, captured via a valid session login.

The public capture is complete and verified. The authenticated capture succeeded in obtaining the core value — **~16,000 auction lot pages** — but the crawl behaved as a *runaway* due to an unbounded calendar, and required manual intervention. Both archives carry an integrity layer (per-file SHA-256 hashes + metadata) so they can serve as a defensible evidence record.

**Bottom line:** We can archive this site and preserve it offline. The core auction data is captured. A short, targeted re-run is recommended to make the archive fully self-contained (offline images) and to trim ~130 years of empty calendar bloat.

---

## 2. What We Delivered

| Archive | Files | Size | Key content | Status |
|---|---|---|---|---|
| **Public** | 60 | 6.2 MB | 16 pages (home, services, blog, calendar shell) + all CSS/JS/images | Complete, 0 errors, links converted |
| **Authenticated** | ~52,900 | ~826 MB | **16,065 auction lot pages**, member pages (my_bids, profile), calendar | Core captured; needs cleanup (see §4) |

Each archive folder contains:
- `site/` — the browsable offline copy
- `SHA256SUMS.txt` — cryptographic hash of every file (tamper-evidence)
- `ARCHIVE_METADATA.txt` — source URL, UTC timestamp, tool version, server IPs, coverage notes
- `wget_*_crawl.log` — full request/response network log (audit trail)

---

## 3. How It Works (plain English)

- **Archiving** = downloading a frozen snapshot of every page and asset (HTML, CSS, JavaScript, images) and rewriting internal links so the site browses offline from disk.
- **If the host takes the site down**, the archived static pages, styling, and text remain fully usable offline — permanently.
- **Login areas** were captured by logging in programmatically, saving the server's **session cookie**, and re-using it for the crawl.
- **Limitation:** live/dynamic features (real-time bidding, database search) are not preserved — only the page content as it existed at capture time.

---

## 4. Key Learnings

1. **The site is server-rendered, not JavaScript-rendered.** This was the single biggest de-risking fact: it meant a simple, reliable mirror tool could capture everything, and we did **not** need a heavyweight headless browser. Always verify render mode first.

2. **Login required only a session cookie — no CSRF/captcha.** A single form POST established an authenticated session that the crawler reused cleanly.

3. **Unbounded pagination causes runaway crawls (biggest operational lesson).** The site's calendar had no lower/upper date limit. The crawler dutifully walked month-by-month and generated **~35,000 empty daily pages spanning 1959 → 2093** — ~130+ years of near-empty pages inflating the archive to 826 MB. *Future crawls must constrain date/pagination ranges up front.*

4. **On Windows, killing the shell does not kill the child process.** Our first "stop" terminated the wrapper but the underlying `wget.exe` (a detached child) kept running for **~19 hours**. Lesson: always target the actual worker PID, and verify termination.

5. **Asset host names must match exactly.** Property photos are hosted on Amazon S3 at `prod-bvr-static.s3.amazonaws.com`, but we had whitelisted the regional variant `...s3.us-east-1.amazonaws.com`. The one-word mismatch caused **every lot photo to be skipped** — which is why images only appear when online (the pages still point to the live S3 URL). Easily fixed by adding the correct host.

6. **Link conversion happens only at c
| **curl** | Windows built-in | Login POST verification, HTTP status probing, session validity checks |
| **Python** | 3.9.1 | Custom link-conversion post-processor (`_convert_links.py`) |
| Python stdlib: `os`, `re`, `urllib.parse` | — | HTML/CSS link rewriting to offline-relative paths with live-URL fallback |
| **Playwright** (+ Chromium) | 1.60.0 | Provisioned as fallback for JS-rendered content — **not needed** once we confirmed server-side rendering |
| **PowerShell** | 5.x | Orchestration, file hashing (`Get-FileHash` SHA-256), process control, reporting |
| **winget** | — | Installed GNU Wget on the Windows host |

No paid services or third-party SaaS were used. Everything runs locally.

---

## 6. Current State & Recommended Next Steps

**State:** Runaway crawl stopped. Public archive complete. Authenticated archive holds all core lot pages but includes calendar bloat and points to live-hosted images.

**Recommended (short, targeted follow-up):**
1. **Fetch lot photos from S3** (`prod-bvr-static.s3.amazonaws.com`) so images display offline → makes the archive truly self-contained.
2. **Constrain the crawl** to the real auction date window (e.g. the ~5 active months) and re-run only the lot pages → removes ~35k empty pages and shrinks size dramatically.
3. **Run final link conversion** across the trimmed set for clean offline browsing.
4. **(Optional) Neutral timestamp:** submit the site to the Internet Archive Wayback Machine for an independent, third-party dated snapshot to strengthen evidentiary value.

**Estimated effort:** ~30–60 minutes of mostly-automated runtime.

---

## 7. Risk / Compliance Notes

- Authenticated capture used credentials supplied by the account owner; only content the account is authorized to view was accessed.
- The archive reflects a point-in-time snapshot; dynamic/live features are not reproduced.
- Integrity manifests are included so any later modification to the archive is detectable.
