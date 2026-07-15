@echo off
REM Nightly Insight job launcher (used by the Windows scheduled task).
REM Re-run all detectors over the current database + regenerate the Daily
REM Brief. Does NOT ingest email (ingestion is handled separately).
cd /d "C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
if not exist logs mkdir logs
python scripts\nightly_insight.py >> logs\nightly.log 2>&1
