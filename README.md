# Import alerts: site + monitor in one repo

    public/    the website (index.html), the feed (alerts.json), monitor status (status.json)
    monitor/   monitor.py, sources.yaml, requirements.txt (+ queue.json, state.json after the first run)
    .github/workflows/monitor.yml   daily run on GitHub Actions
    vercel.json                     serves ./public as a static site

## One-time setup
1. Create an empty GitHub repo, then from this folder:
       git init && git add . && git commit -m "first version"
       git branch -M main && git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git && git push -u origin main
2. In Vercel, import that repo (or tell Claude the repo name and it links it). Every push redeploys.
3. In `monitor/monitor.py`, replace YOUR_EMAIL in the User-Agent line.
4. First monitor run: GitHub -> Actions -> monitor -> Run workflow -> tick "baseline". This avoids flooding the queue.
5. Optional Telegram ping for you (the reviewer): add repo secrets TG_TOKEN and TG_CHAT.

## Daily routine (about 10 minutes)
    git pull
    cd monitor && pip install -r requirements.txt && python monitor.py review
    cd .. && git add public/alerts.json && git commit -m "alerts" && git push

Read each item on the official page before approving. Only mark "read on official page" = y when you did.

## What the site shows
- The Alerts tab loads `alerts.json` from the same site; if missing it uses the 7 built-in alerts.
- "Last automatic check" comes from `status.json`. If it is old, the monitor is not running.

## Failure handling
- A failed or empty source makes the run exit with an error, so GitHub emails you, and `status.json` records which source failed.
- Check manually once a month that the official pages still look the same; the parser reads plain links.

## Limits
Not tested against the live Algerian sites (my sandbox could not reach them). Only mcepe.gov.dz is enabled in sources.yaml; the other addresses are unverified. JavaScript-rendered pages need Playwright. Alerts are information, not legal advice.
