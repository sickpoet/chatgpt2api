#!/usr/bin/env python3
"""同步 accounts.json 到 SQLite 数据库"""
import json
import sqlite3
from datetime import datetime

DB_PATH = "/opt/chatgpt2api/data/accounts.db"
JSON_PATH = "/opt/chatgpt2api/data/accounts.json"

def sync():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    with open(JSON_PATH, 'r') as f:
        accounts = json.load(f)
    
    new_count = 0
    update_count = 0
    status_change_count = 0
    
    for acc in accounts:
        user_id = acc.get('user_id')
        if not user_id:
            continue
        
        c.execute("SELECT status, quota FROM accounts WHERE user_id = ?", (user_id,))
        existing = c.fetchone()
        
        if existing:
            old_status, old_quota = existing
            new_status = acc.get('status', '未知')
            
            c.execute("""
            UPDATE accounts SET 
                email = ?, access_token = ?, type = ?, status = ?, 
                quota = ?, success = ?, fail = ?,
                last_used_at = ?, restore_at = ?, updated_at = ?
            WHERE user_id = ?
            """, (
                acc.get('email'), acc.get('access_token'), acc.get('type'),
                new_status, acc.get('quota', 0), 
                acc.get('success', 0), acc.get('fail', 0),
                acc.get('last_used_at'), acc.get('restore_at'),
                datetime.now().isoformat(), user_id
            ))
            
            if old_status != new_status:
                c.execute("""
                INSERT INTO status_logs (user_id, old_status, new_status, quota)
                VALUES (?, ?, ?, ?)
                """, (user_id, old_status, new_status, acc.get('quota', 0)))
                status_change_count += 1
            
            update_count += 1
        else:
            c.execute("""
            INSERT INTO accounts (
                user_id, email, access_token, type, status, quota,
                image_quota_unknown, success, fail, last_used_at, restore_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, acc.get('email'), acc.get('access_token'), acc.get('type'),
                acc.get('status'), acc.get('quota', 0), acc.get('image_quota_unknown', False),
                acc.get('success', 0), acc.get('fail', 0),
                acc.get('last_used_at'), acc.get('restore_at')
            ))
            new_count += 1
        
        # 更新限额进度
        for limit in acc.get('limits_progress', []):
            c.execute("""
            INSERT OR REPLACE INTO limits_progress (user_id, feature_name, remaining, reset_after)
            VALUES (?, ?, ?, ?)
            """, (user_id, limit['feature_name'], limit['remaining'], limit['reset_after']))
    
    conn.commit()
    conn.close()
    
    if new_count or update_count or status_change_count:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 同步: 新增 {new_count}, 更新 {update_count}, 状态变更 {status_change_count}")

if __name__ == "__main__":
    sync()
