"""Import-alerts monitor: official pages -> queue.json -> human review -> alerts.json.
Usage:  python monitor.py fetch --baseline   (first run: mark current links as seen)
        python monitor.py fetch              (queue new import-related links)
        python monitor.py review             (approve/edit queued items into alerts.json)
Never publish an alert you have not read on the official page."""
import json, re, sys, hashlib, datetime as dt
from pathlib import Path
from urllib.parse import urljoin
import requests, yaml
from bs4 import BeautifulSoup

H = Path(__file__).parent
PUB = H.parent / "public"
STATE, QUEUE, SRC = H/"state.json", H/"queue.json", H/"sources.yaml"
FEED, STATUS = PUB/"alerts.json", PUB/"status.json"
UA = {"User-Agent": "ImportAlertsBot/0.1 (student project; contact: alalouci5@gmail.com)"}
IMPORT = re.compile(r"import|programme pr[ée]visionnel|\bPPI\b|domicili|douan|taxe|conformit|\bCOC\b|licence|interdiction|cabas|استيراد|توطين|جمارك|رسوم|مطابقة|حظر", re.I)
EXPORT = re.compile(r"export|تصدير", re.I)
CATS = {"ppi": r"\bPPI\b|programme pr[ée]visionnel|برنامج الاستيراد", "micro": r"micro-?import|cabas|مقاول ذاتي",
        "bank": r"domicili|banque d.alg|abef|توطين", "customs": r"douan|droits?|taxe|جمارك|رسوم",
        "conf": r"conformit|\bCOC\b|interdiction|licence|مطابقة|حظر"}

def load(p, d): return json.loads(p.read_text("utf8")) if p.exists() else d
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=1), "utf8")

def classify(title):
    """Import-only filter. Returns a category, '' (unknown) or None (skip)."""
    if not IMPORT.search(title): return None
    if EXPORT.search(title) and not re.search(r"import|استيراد", title, re.I): return None
    return next((k for k, rx in CATS.items() if re.search(rx, title, re.I)), "")

def links(src):
    r = requests.get(src["url"], headers=UA, timeout=30); r.raise_for_status()
    seen, out = set(), []
    for a in BeautifulSoup(r.content, "html.parser").find_all("a", href=True):
        t, u = " ".join(a.get_text().split()), urljoin(src["url"], a["href"])
        if len(t) >= 20 and u not in seen: seen.add(u); out.append((t, u))
    return out

def fetch(baseline=False):
    st, q = load(STATE, {"seen": []}), load(QUEUE, [])
    seen, res = set(st["seen"]), {}
    for s in yaml.safe_load(SRC.read_text("utf8"))["sources"]:
        if not s.get("enabled"): continue
        try: found = links(s)
        except Exception as e: print("WARN", s["name"], e); res[s["name"]] = f"error: {e}"; continue
        res[s["name"]] = "ok" if found else "no links found (layout changed?)"
        for t, u in found:
            i = hashlib.sha1(u.encode()).hexdigest()[:12]
            if i in seen: continue
            seen.add(i)
            c = classify(t)
            if baseline or c is None: continue
            q.append({"id": i, "found": dt.date.today().isoformat(), "official": s["url"], "title": t, "lead": u, "cat": c, "status": "pending"})
    st["seen"] = sorted(seen); save(STATE, st); save(QUEUE, q)
    save(STATUS, {"last_run": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"), "sources": res})
    print("pending:", sum(x["status"] == "pending" for x in q), "| sources:", res)
    if any(v != "ok" for v in res.values()) or not res: sys.exit(1)  # GitHub emails you on a failed run

def ask(label, default=""):
    v = input(f"{label} [{default}]: ").strip(); return v or default

def review():
    q, feed = load(QUEUE, []), load(FEED, [])
    for it in [x for x in q if x["status"] == "pending"]:
        print("\n", it["title"], "\n", it["lead"], "\n cat:", it["cat"] or "?")
        ch = input("[a]pprove / [s]kip / [q]uit: ").lower()
        if ch == "q": break
        if ch != "a": it["status"] = "skipped"; continue
        a = {"id": it["id"], "date": ask("date YYYY-MM-DD", it["found"]), "cat": ask("cat ppi|micro|bank|customs|conf", it["cat"] or "customs"),
             "type": ask("type rule|deadline|open|scope", "rule"), "title": ask("title (AR)", it["title"]),
             "what": ask("what changed (AR)"), "do": ask("what to do (AR)"), "impact": ask("cost impact (AR, optional)"),
             "official": it["official"], "lead": it["lead"], "verified": ask("read on official page? y/n", "n") == "y"}
        due = ask("deadline YYYY-MM-DD (optional)")
        if due: a["due"] = due
        feed.append(a); it["status"] = "approved"
    feed.sort(key=lambda x: x["date"], reverse=True); save(FEED, feed); save(QUEUE, q)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch": fetch("--baseline" in sys.argv)
    elif cmd == "review": review()
    else: print(__doc__)
