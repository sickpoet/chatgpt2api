#!/usr/bin/env python3
"""查询账号状态"""
import sqlite3
import sys

DB_PATH = "/opt/chatgpt2api/data/accounts.db"

def query(status_filter=None, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 统计
    if status_filter:
        c.execute("SELECT COUNT(*) FROM accounts WHERE status = ?", (status_filter,))
    else:
        c.execute("SELECT COUNT(*) FROM accounts")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM accounts WHERE status = '正常'")
    normal = c.fetchone()[0]
    
    c.execute("SELECT SUM(quota) FROM accounts WHERE status = '正常'")
    total_quota = c.fetchone()[0] or 0
    
    print(f"📊 账号统计:")
    print(f"   总账号: {total}")
    print(f"   正常: {normal}")
    print(f"   异常: {total - normal}")
    print(f"   总配额: {total_quota}")
    print()
    
    # 查询账号列表
    if status_filter:
        c.execute("""
        SELECT user_id, email, status, quota, success, fail, ban_count, last_used_at 
        FROM accounts WHERE status = ? 
        ORDER BY last_used_at DESC LIMIT ?
        """, (status_filter, limit))
    else:
        c.execute("""
        SELECT user_id, email, status, quota, success, fail, ban_count, last_used_at 
        FROM accounts 
        ORDER BY last_used_at DESC LIMIT ?
        """, (limit,))
    
    rows = c.fetchall()
    if rows:
        print(f"{'邮箱':<35} {'状态':<6} {'配额':<6} {'成功/失败':<10} {'封号次数':<8} {'最后使用'}")
        print("-" * 100)
        for row in rows:
            user_id, email, status, quota, success, fail, ban_count, last_used = row
            success_fail = f"{success}/{fail}"
            print(f"{email or 'N/A':<35} {status:<6} {quota:<6} {success_fail:<10} {ban_count:<8} {last_used or 'N/A'}")
    
    # 查询最近状态变更
    c.execute("""
    SELECT user_id, old_status, new_status, quota, changed_at 
    FROM status_logs 
    ORDER BY changed_at DESC LIMIT 5
    """)
    changes = c.fetchall()
    if changes:
        print(f"\n📋 最近状态变更:")
        for change in changes:
            user_id, old_status, new_status, quota, changed_at = change
            c.execute("SELECT email FROM accounts WHERE user_id = ?", (user_id,))
            email = c.fetchone()
            email = email[0] if email else user_id
            print(f"   {email}: {old_status} → {new_status} (配额: {quota}) [{changed_at}]")
    
    conn.close()

if __name__ == "__main__":
    status_filter = sys.argv[1] if len(sys.argv) > 1 else None
    query(status_filter)
