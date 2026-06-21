"""飞书多维表格 → Dashboard DATA"""
import os, re, requests

APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a931cdfb8bf89bb5")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
BASE_ID = os.environ.get("FEISHU_BASE_ID", "XJAZbw1rqaWHMnsVAJIci7ttnJd")

# Fallback: read from .env
if not APP_SECRET:
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        for line in open(env_file):
            line = line.strip()
            if line.startswith("FEISHU_APP_SECRET="):
                APP_SECRET = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("FEISHU_APP_ID="):
                APP_ID = line.split("=", 1)[1].strip().strip('"').strip("'")

def _auth():
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
    return "Bearer " + r.json()["tenant_access_token"]

def _get(path, params=None):
    r = requests.get(f"https://open.feishu.cn/open-apis{path}",
        headers={"Authorization": _auth()}, params=params, timeout=15)
    return r.json()

def _read_all(tid):
    items, pt = [], None
    while True:
        p = {"page_size": 200}
        if pt: p["page_token"] = pt
        d = _get(f"/bitable/v1/apps/{BASE_ID}/tables/{tid}/records", p)
        if "data" not in d: break
        for it in d["data"].get("items", []):
            f = {}
            for k, v in it.get("fields", {}).items():
                if v is not None:
                    f[k] = v if isinstance(v, (int, float)) else str(v).strip()
            items.append(f)
        if not d["data"].get("has_more"): break
        pt = d["data"].get("page_token")
    return items

def _num(s):
    if s is None: return 0
    if isinstance(s, (int, float)): return float(s)
    try: return float(str(s).replace(",","").replace("%","").replace("¥","").strip())
    except: return 0

def fetch():
    kpi = _read_all("tblmGijNaVv80ogT")

    period, week_range = "W??", ""
    for row in kpi:
        for v in row.values():
            if isinstance(v, str) and "W" in v and "周累计" in v:
                m = re.search(r'(W\d+)', v)
                period = m.group(1) if m else period
                week_range = v.replace(f"{period}周累计：","").replace("至","-")
                break

    best_row, best_count = {}, 0
    for row in kpi:
        count = sum(1 for v in row.values() if _num(v) != 0)
        if count > best_count:
            best_row, best_count = row, count

    metrics = {}
    for fid, val in best_row.items():
        n = _num(val)
        if n != 0:
            metrics[fid] = n

    return {
        "period": period,
        "week_range": week_range,
        "store": "奥莱店华南区城市",
        "total_nums": metrics,
        "total_row": {k: str(v)[:80] for k, v in best_row.items() if v},
    }
