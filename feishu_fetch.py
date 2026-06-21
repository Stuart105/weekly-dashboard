"""飞书多维表格 → Dashboard DATA"""
import os, re, requests, sys

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
            elif line.startswith("FEISHU_BASE_ID="):
                BASE_ID = line.split("=", 1)[1].strip().strip('"').strip("'")

def _auth():
    """获取 tenant_access_token，认证失败时抛出明确的异常"""
    if not APP_SECRET:
        raise RuntimeError(
            "飞书 APP_SECRET 未配置。请在 .env 文件中设置 FEISHU_APP_SECRET=你的密钥，"
            "或设置环境变量 FEISHU_APP_SECRET"
        )
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": APP_ID, "app_secret": APP_SECRET},
            timeout=10
        )
        resp = r.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"飞书认证请求失败(网络/超时): {e}")
    except ValueError:
        raise RuntimeError(f"飞书认证响应无效(非JSON): {r.text[:200]}")

    if r.status_code != 200:
        raise RuntimeError(
            f"飞书认证失败 HTTP {r.status_code}: {resp.get('msg', resp)}"
        )
    if "tenant_access_token" not in resp:
        raise RuntimeError(
            f"飞书认证失败，未获取到 token。响应: {resp.get('msg', resp)}。"
            f"请检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 是否正确。"
        )
    return "Bearer " + resp["tenant_access_token"]

def _get(path, params=None):
    r = requests.get(f"https://open.feishu.cn/open-apis{path}",
        headers={"Authorization": _auth()}, params=params, timeout=15)
    resp = r.json()
    if r.status_code != 200:
        raise RuntimeError(
            f"飞书 API 请求失败 HTTP {r.status_code}: {resp.get('msg', resp)} (path={path})"
        )
    return resp

def _read_all(tid):
    items, pt = [], None
    while True:
        p = {"page_size": 200}
        if pt: p["page_token"] = pt
        d = _get(f"/bitable/v1/apps/{BASE_ID}/tables/{tid}/records", p)
        if "data" not in d:
            raise RuntimeError(
                f"飞书多维表格读取失败，响应中缺少 data 字段。"
                f"表ID={tid}, 响应: {d.get('msg', d)}"
            )
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
    try:
        kpi = _read_all("tblmGijNaVv80ogT")
    except Exception as e:
        print(f"[feishu_fetch] 读取表格失败: {e}", file=sys.stderr)
        raise

    if not kpi:
        raise RuntimeError(
            "飞书多维表格中没有数据。请确认表格 tblmGijNaVv80ogT 中已填入周报数据。"
        )

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

    if best_count == 0:
        raise RuntimeError(
            "飞书多维表格中所有行数据均为空或无效。请确认表格中已填入数值数据。"
        )

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
