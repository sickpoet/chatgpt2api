import json
import sqlite3
from datetime import datetime

DB_PATH = "/opt/chatgpt2api/data/accounts.db"
JSON_PATH = "/opt/chatgpt2api/data/accounts.json"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 创建账号表
    c.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        user_id TEXT PRIMARY KEY,
        email TEXT,
        access_token TEXT,
        type TEXT DEFAULT 'Free',
        status TEXT DEFAULT '正常',
        quota INTEGER DEFAULT 0,
        image_quota_unknown BOOLEAN DEFAULT 0,
        success INTEGER DEFAULT 0,
        fail INTEGER DEFAULT 0,
        last_used_at TEXT,
        restore_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 创建状态变更日志表
    c.execute("""
    CREATE TABLE IF NOT EXISTS status_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        old_status TEXT,
        new_status TEXT,
        quota INTEGER,
        changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES accounts(user_id)
    )
    """)
    
    # 创建限额进度表
    c.execute("""
    CREATE TABLE IF NOT EXISTS limits_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        feature_name TEXT,
        remaining INTEGER,
        reset_after TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES accounts(user_id),
        UNIQUE(user_id, feature_name)
    )
    """)
    
    conn.commit()
    return conn

def import_from_json(conn):
    with open(JSON_PATH, 'r') as f:
        accounts = json.load(f)
    
    c = conn.cursor()
    imported = 0
    updated = 0
    
    for acc in accounts:
        user_id = acc.get('user_id')
        if not user_id:
            continue
        
        # 检查是否已存在
        c.execute("SELECT status FROM accounts WHERE user_id = ?", (user_id,))
        existing = c.fetchone()
        
        if existing:
            # 更新
            c.execute("""
            UPDATE accounts SET 
                email = ?, access_token = ?, type = ?, status = ?, 
                quota = ?, image_quota_unknown = ?, success = ?, fail = ?,
                last_used_at = ?, restore_at = ?, updated_at = ?
            WHERE user_id = ?
            """, (
                acc.get('email'), acc.get('access_token'), acc.get('type'),
                acc.get('status'), acc.get('quota', 0), acc.get('image_quota_unknown', False),
                acc.get('success', 0), acc.get('fail', 0),
                acc.get('last_used_at'), acc.get('restore_at'),
                datetime.now().isoformat(), user_id
            ))
            
            # 记录状态变更
            if existing[0] != acc.get('status'):
                c.execute("""
                INSERT INTO status_logs (user_id, old_status, new_status, quota)
                VALUES (?, ?, ?, ?)
                """, (user_id, existing[0], acc.get('status'), acc.get('quota', 0)))
            
            updated += 1
        else:
            # 新增
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
            imported += 1
        
        # 更新限额进度
        for limit in acc.get('limits_progress', []):
            c.execute("""
            INSERT OR REPLACE INTO limits_progress (user_id, feature_name, remaining, reset_after)
            VALUES (?, ?, ?, ?)
            """, (user_id, limit['feature_name'], limit['remaining'], limit['reset_after']))
    
    conn.commit()
    print(f"✅ 导入完成: 新增 {imported}, 更新 {updated}")

if __name__ == "__main__":
    conn = init_db()
    import_from_json(conn)
    
    # 统计
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM accounts")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM accounts WHERE status = '正常'")
    normal = c.fetchone()[0]
    c.execute("SELECT SUM(quota) FROM accounts WHERE status = '正常'")
    total_quota = c.fetchone()[0] or 0
    
    print(f"📊 数据库统计:")
    print(f"   总账号: {total}")
    print(f"   正常: {normal}")
    print(f"   总配额: {total_quota}")
    
    conn.close()
