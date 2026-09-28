"""Builds data.json for the daily-summary page from two Notion data sources.
Env: NOTION_TOKEN (integration token; share both databases with the integration).
"""
import json, os, datetime as dt, urllib.request, urllib.error

TOKEN = os.environ["NOTION_TOKEN"]
LOG_DS = "c84963b3-643a-4564-92b8-08f38a5af163"      # Athlete Log (daily)
INTAKE_DS = "a806b326-5146-40bd-98d1-0ca6bf8159dd"   # Daily intake
RULES = {"baseline": 1850, "proteinTrain": 120, "proteinRest": 100, "fatPct": 0.20, "eaTarget": 28}
H = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2025-09-03", "Content-Type": "application/json"}

def _post(url, body, version):
    h = dict(H); h["Notion-Version"] = version
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["results"]
    except urllib.error.HTTPError as e:
        print("NOTION", e.code, url, e.read().decode()[:600]); raise

def query(ds, body):
    """Try the data_sources endpoint (2025-09-03); fall back to databases (2022-06-28)."""
    try:
        return _post(f"https://api.notion.com/v1/data_sources/{ds}/query", body, "2025-09-03")
    except urllib.error.HTTPError:
        return _post(f"https://api.notion.com/v1/databases/{ds}/query", body, "2022-06-28")

def val(p):
    t = p["type"]
    if t == "number": return p["number"]
    if t == "date": return p["date"]["start"] if p["date"] else None
    if t in ("rich_text", "title"): return "".join(x["plain_text"] for x in p[t]) or None
    if t == "checkbox": return p["checkbox"]
    if t == "last_edited_time": return p["last_edited_time"]
    return None

def props(page): return {k: val(v) for k, v in page["properties"].items()}

def parse_workouts(txt):
    """'[Run (Morning Run): 50m | 10.5km | HR Avg:145 Max:157 | ... | 61TSS | HR Zones: Z1:50m]' -> list of {n,t}"""
    out = []
    if not txt or txt.startswith("No workouts"): return out
    for chunk in txt.split(" AND "):
        chunk = chunk.strip().strip("[]")
        name, _, rest = chunk.partition(": ")
        out.append({"n": name.split(" (")[-1].rstrip(")") if " (" in name else name, "t": rest.replace(" | ", " · ")})
    return out

today = dt.date.today()
since = (today - dt.timedelta(days=13)).isoformat()
rows = query(LOG_DS, {"filter": {"property": "date", "date": {"on_or_after": since}}, "sorts": [{"property": "date", "direction": "ascending"}], "page_size": 20})
days = []
for r in rows:
    p = props(r)
    days.append({
        "d": p["date"][5:10], "hrv": p.get("hrv"), "rhr": p.get("resting_hr"), "shr": p.get("avg_sleep_hr"),
        "sl": p.get("sleep_h"), "dp": p.get("deep_h"), "rem": p.get("rem_h"), "aw": p.get("awake_h"),
        "ctl": p.get("ctl"), "atl": p.get("atl"), "tsb": p.get("tsb"), "tss": p.get("tss") or 0,
        "act": p.get("active_kcal") or 0, "in": p.get("kcal_intake"), "bal": p.get("balance_kcal"),
        "w": p.get("weight_kg"), "lm": p.get("lean_mass_kg"), "wk": parse_workouts(p.get("workouts")),
        "open": p["date"] == today.isoformat(),
    })
if days and days[-1]["open"]:
    days[-1]["in"] = None; days[-1]["bal"] = None   # open day carries yesterday's values until day close

intake = {}
ir = query(INTAKE_DS, {"filter": {"property": "Day", "title": {"equals": today.isoformat()}}, "page_size": 1})
if ir:
    p = props(ir[0])
    intake = {"kcal": p.get("kcal"), "carbs": p.get("carbs_g"), "protein": p.get("protein_g"), "fat": p.get("fat_g"),
              "updated": (p.get("last_updated") or "")[11:16]}

json.dump({"generated": dt.datetime.now().strftime("%d %b %H:%M"), "rules": RULES, "days": days, "intake": intake},
          open("data.json", "w"), indent=0)
print(f"wrote {len(days)} days, intake={bool(intake)}")
