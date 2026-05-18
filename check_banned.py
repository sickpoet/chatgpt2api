#!/usr/bin/env python3
"""检测封号 - 连续2次被封才删除"""
import json
import sqlite3
import requests
from datetime import datetime

DB_PATH = "/opt/chatgpt2api/data/accounts.db"
JSON_PATH = "/opt/chatgpt2api/data/accounts.json"
BACKUP_PATH = "/opt/chatgpt2api/data/banned_accounts.json"

def check_account(access_token, proxy=None):
    """测试账号是否有效"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        resp = requests.get(
            "https://chatgpt.com/backend-api/models",
            headers=headers,
            proxies=proxies,
            timeout=15
        )
        
        if resp.status_code == 200:
            return "正常", None
        elif resp.status_code == 401:
            return "Token过期", "401 Unauthorized"
        elif resp.status_code == 403:
            return "被封禁", "403 Forbidden"
        elif resp.status_code == 429:
            return "限流中", "429 Too Many Requests"
        else:
            return "异常", f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return "超时", "请求超时"
    except Exception as e:
        return "错误", str(e)

def add_ban_count_column(conn):
    """确保 ban_count 列存在"""
    c = conn.cursor()
    c.execute("PRAGMA table_info(accounts)")
    columns = [row[1] for row in c.fetchall()]
    if 'ban_count' not in columns:
        c.execute("ALTER TABLE accounts ADD COLUMN ban_count INTEGER DEFAULT 0")
        conn.commit()
        print("✅ 已添加 ban_count 列")

def backup_banned_account(account):
    """备份被封账号"""
    try:
        banned = []
        try:
            with open(BACKUP_PATH) as f:
                banned = json.load(f)
        except:
            pass
        
        banned.append({
            "user_id": account["user_id"],
            "email": account["email"],
            "access_token": account["access_token"],
            "banned_at": datetime.now().isoformat(),
            "ban_count": account.get("ban_count", 0)
        })
        
        with open(BACKUP_PATH, 'w') as f:
            json.dump(banned, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"   备份失败: {e}")

def remove_from_json(user_id):
    """从 accounts.json 中删除账号"""
    try:
        with open(JSON_PATH) as f:
            accounts = json.load(f)
        
        original_count = len(accounts)
        accounts = [a for a in accounts if a.get("user_id") != user_id]
        
        if len(accounts) < original_count:
            with open(JSON_PATH, 'w') as f:
                json.dump(accounts, f, indent=2, ensure_ascii=False)
            return True
    except Exception as e:
        print(f"   删除失败: {e}")
    return False

def main():
    # 读取代理
    proxy = None
    try:
        with open("/opt/chatgpt2api/config.json") as f:
            config = json.load(f)
            proxy = config.get("proxy") or None
    except:
        pass
    
    # 读取账号
    with open(JSON_PATH) as f:
        accounts = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    add_ban_count_column(conn)
    c = conn.cursor()
    
    total = len(accounts)
    normal = 0
    banned = 0
    expired = 0
    deleted = 0
    
    print(f"🔍 开始检测 {total} 个账号...")
    print(f"   代理: {proxy or '无'}")
    print()
    
    for i, acc in enumerate(accounts, 1):
        user_id = acc.get("user_id")
        email = acc.get("email", "N/A")
        access_token = acc.get("access_token")
        
        if not access_token:
            continue
        
        status, reason = check_account(access_token, proxy)
        
        # 获取当前 ban_count
        c.execute("SELECT ban_count FROM accounts WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        current_ban_count = row[0] if row else 0
        
        if status == "正常":
            normal += 1
            # 重置 ban_count
            c.execute("UPDATE accounts SET ban_count = 0, status = '正常', updated_at = ? WHERE user_id = ?", 
                      (datetime.now().isoformat(), user_id))
        elif status in ["被封禁", "Token过期"]:
            banned += 1
            new_ban_count = current_ban_count + 1
            
            print(f"  [{i}/{total}] {email}: {status} (连续第{new_ban_count}次)")
            
            if new_ban_count >= 2:
                # 连续2次被封，删除
                print(f"   ⚠️ 连续2次被封，删除账号")
                backup_banned_account(acc)
                if remove_from_json(user_id):
                    c.execute("DELETE FROM accounts WHERE user_id = ?", (user_id,))
                    c.execute("""
                    INSERT INTO status_logs (user_id, old_status, new_status, quota, changed_at)
                    VALUES (?, ?, ?, ?, ?)
                    """, (user_id, status, "已删除", acc.get("quota", 0), datetime.now().isoformat()))
                    deleted += 1
            else:
                # 第一次被封，记录
                c.execute("""
                UPDATE accounts SET ban_count = ?, status = ?, updated_at = ? WHERE user_id = ?
                """, (new_ban_count, status, datetime.now().isoformat(), user_id))
                c.execute("""
                INSERT INTO status_logs (user_id, old_status, new_status, quota, changed_at)
                VALUES (?, ?, ?, ?, ?)
                """, (user_id, acc.get("status", "未知"), status, acc.get("quota", 0), datetime.now().isoformat()))
        else:
            # 超时、限流等，不计为被封
            c.execute("UPDATE accounts SET status = ?, updated_at = ? WHERE user_id = ?",
                      (status, datetime.now().isoformat(), user_id))
        
        if i % 10 == 0:
            print(f"  进度: {i}/{total}")
    
    conn.commit()
    conn.close()
    
    print()
    print(f"📊 检测结果:")
    print(f"   总账号: {total}")
    print(f"   正常: {normal}")
    print(f"   被封禁: {banned}")
    print(f"   已删除: {deleted}")
    print(f"   剩余: {total - deleted}")

if __name__ == "__main__":
    main()
