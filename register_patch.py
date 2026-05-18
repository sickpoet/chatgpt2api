"""
chatgpt2api 注册机优化 — 直接在容器内执行
功能：域名信誉治理 + 错误分类 + 智能重试
"""
import json
import re
import threading
import time
from pathlib import Path

DATA_DIR = Path("/app/data")
REG_FILE = DATA_DIR / "domain_reputation.json"

# ============================================================
# Step 1: 创建域名信誉模块
# ============================================================
DOMAIN_REP_MODULE = '''\
"""域名信誉治理"""
import json, threading, time
from pathlib import Path

_persist = str(Path(__file__).resolve().parent.parent.parent / "data" / "domain_reputation.json")
_lock = threading.Lock()
_stats = {}

def _load():
    global _stats
    try: _stats = json.loads(Path(_persist).read_text("utf-8"))
    except: _stats = {}

def _save():
    try: Path(_persist).write_text(json.dumps(_stats, ensure_ascii=False, indent=2), encoding="utf-8")
    except: pass

_load()

def record_success(domain):
    with _lock:
        s = _stats.setdefault(domain, {"s":0,"f":0,"blk":0,"err":""})
        s["s"] = s.get("s",0) + 1; s["blk"] = 0; s["err"] = ""
        _save()

def record_failure(domain, error, blocked=False):
    with _lock:
        s = _stats.setdefault(domain, {"s":0,"f":0,"blk":0,"err":""})
        s["f"] = s.get("f",0) + 1; s["err"] = error[:200]
        if blocked: s["blk"] = time.time() + 7200
        _save()

def is_blocked(domain):
    with _lock:
        s = _stats.get(domain)
        if not s: return False
        if s.get("blk",0) > time.time(): return True
        if s.get("f",0) >= 3 and s.get("s",0) == 0: return True
        return False

def is_domain_blocked_error(err):
    e = err.lower()
    return "http_400" in e and ("account_creation_failed" in e or "failed to create account" in e)

def summary():
    with _lock:
        parts = []
        for d,s in sorted(_stats.items()):
            t = s.get("s",0)+s.get("f",0)
            r = s.get("s",0)/t*100 if t>0 else 0
            b = "BLK" if s.get("blk",0)>time.time() else ""
            parts.append(f"{d}:{s.get('s',0)}/{t}({r:.0f}%){b}")
        return " | ".join(parts) or "no data"
'''

print("[1/4] 注入域名信誉模块...")
Path("/app/services/register/domain_reputation.py").write_text(DOMAIN_REP_MODULE, encoding="utf-8")
print("  ✅ domain_reputation.py")

# ============================================================
# Step 2: 修改 mail_provider.py — 域名过滤
# ============================================================
print("[2/4] 修改 mail_provider.py...")
mp_code = Path("/app/services/register/mail_provider.py").read_text("utf-8")
mp_backup = Path("/app/services/register/mail_provider.py.bak")
if not mp_backup.exists():
    mp_backup.write_text(mp_code, encoding="utf-8")

# 加 import
if "domain_reputation" not in mp_code:
    mp_code = mp_code.replace(
        "from curl_cffi import requests as curl_requests",
        "from curl_cffi import requests as curl_requests\nfrom services.register.domain_reputation import is_blocked as _dr_is_blocked"
    )

# 修改 _next_domain 函数头
if "_dr_is_blocked" not in mp_code:
    mp_code = mp_code.replace(
        "def _next_domain(domains: list[str]) -> str:",
        "def _next_domain(domains: list[str]) -> str:\n    domains = [d for d in domains if not _dr_is_blocked(d)] or domains"
    )

Path("/app/services/register/mail_provider.py").write_text(mp_code, encoding="utf-8")
print("  ✅ mail_provider.py 已加域名过滤")

# ============================================================
# Step 3: 修改 openai_register.py — 记录域名信誉
# ============================================================
print("[3/4] 修改 openai_register.py...")
reg_code = Path("/app/services/register/openai_register.py").read_text("utf-8")
reg_backup = Path("/app/services/register/openai_register.py.bak3")
if not reg_backup.exists():
    reg_backup.write_text(reg_code, encoding="utf-8")

# 加 import
if "domain_reputation" not in reg_code:
    reg_code = reg_code.replace(
        "from services.register import mail_provider",
        "from services.register import mail_provider\nfrom services.register.domain_reputation import record_success as _dr_success, record_failure as _dr_fail, is_domain_blocked_error as _dr_is_blocked_err"
    )

# 成功时记录域名
if "_dr_success" not in reg_code:
    reg_code = reg_code.replace(
        'access_token = str(result["access_token"])\n        account_service.add_accounts([access_token])',
        'access_token = str(result["access_token"])\n        try:\n            _em = str(result.get("email",""))\n            _dm = _em.split("@")[-1] if "@" in _em else ""\n            if _dm: _dr_success(_dm)\n        except: pass\n        account_service.add_accounts([access_token])'
    )

# 失败时记录域名
if "_dr_fail" not in reg_code:
    old_fail = '        log(f"任务{index} 注册失败，本次耗时{cost:.1f}s，原因: {e}", "red")\n        return {"ok": False, "index": index, "error": str(e)}'
    new_fail = '''        try:
            _dr_fail("", str(e), blocked=_dr_is_blocked_err(str(e)))
        except: pass
        log(f"任务{index} 注册失败，本次耗时{cost:.1f}s，原因: {e}", "red")
        return {"ok": False, "index": index, "error": str(e)}'''
    reg_code = reg_code.replace(old_fail, new_fail)

Path("/app/services/register/openai_register.py").write_text(reg_code, encoding="utf-8")
print("  ✅ openai_register.py 已加域名记录")

# ============================================================
# Step 4: 验证
# ============================================================
print("[4/4] 验证...")
try:
    from services.register.domain_reputation import summary
    print(f"  ✅ 模块加载成功: {summary()}")
except Exception as e:
    print(f"  ⚠️ 模块加载失败: {e}")

print("\n=== 优化完成，重启容器生效 ===")
